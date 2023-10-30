import os
from typing import Dict, Any
import pickle
from pathlib import Path
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
from llama_index import Document, Prompt, download_loader, GPTVectorStoreIndex, ServiceContext, StorageContext, \
    load_index_from_storage, SimpleDirectoryReader
from llama_index.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.indices.postprocessor import SimilarityPostprocessor
from app.data.models.qa import Source
from app.utils.log_util import logger
from app.utils import jsonl_util, data_util

llama_index_home = "./llama_index_server"
os.environ["LLAMA_INDEX_CACHE_DIR"] = f"{llama_index_home}/llama_index_cache"
index_path = f"{llama_index_home}/saved_index"
csv_path = f"./documents/golf-knowledge-base.csv"
jsonl_path = csv_path.replace(".csv", ".jsonl")
pkl_path = f"{llama_index_home}/pkl/stored_documents.pkl"
answer_to_irrelevant_question = "This question is not relevant to golf."
prompt_template_string = (
    "We have provided context information below. \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "Given this information, assume you are an experienced golf coach, "
    "please give short, accurate, precise, simple answer to the golfer beginner's question, "
    "limited to 80 words maximum. If the question is not relevant to golf, please answer "
    f"'{answer_to_irrelevant_question}'.\n"
    "The question is: {query_str}\n"
)
index = None
stored_docs = {}
lock = Lock()


def initialize_index():
    """Create a new global index, or load one from the pre-set path."""
    global index, stored_docs
    service_context = ServiceContext.from_defaults()
    with lock:
        if os.path.exists(index_path):
            logger.info(f"Loading index from dir: {index_path}")
            index = load_index_from_storage(StorageContext.from_defaults(persist_dir=index_path),
                                            service_context=service_context)
        else:
            data_util.assert_true(os.path.exists(csv_path) or os.path.exists(jsonl_path),
                                  f"both csv and jsonl file are not found: {csv_path}, {jsonl_path}")
            if not os.path.exists(jsonl_path):
                logger.info(f"Converting csv to jsonl: {csv_path} -> {jsonl_path}")
                jsonl_util.csv_to_jsonl(csv_path, jsonl_path)
            json_reader = download_loader("JSONReader")
            loader = json_reader()
            documents = loader.load_data(file=Path(jsonl_path), is_jsonl=True)
            index = GPTVectorStoreIndex.from_documents(documents, service_context=service_context)
            logger.info("Using GPTVectorStoreIndex")
            index.storage_context.persist(persist_dir=index_path)
        if os.path.exists(pkl_path):
            logger.info(f"Loading from pickle: {pkl_path}")
            with open(pkl_path, "rb") as f:
                stored_docs = pickle.load(f)


def query_index(query_text) -> Dict[str, Any]:
    """Query the global index."""
    global index
    logger.info(f"Query test: {query_text}")
    # first search locally
    local_query_engine = index.as_query_engine(
        response_synthesizer=get_response_synthesizer(response_mode=ResponseMode.NO_TEXT),
        node_postprocessors=[
            SimilarityPostprocessor(similarity_cutoff=0.85)
        ]
    )
    local_query_response = local_query_engine.query(query_text)
    if len(local_query_response.source_nodes) > 0:
        text = local_query_response.source_nodes[0].text
        if 'answer\": ' in text:
            answer_text = text.split('answer\": ')[1].strip("\"\n}")
            if 'category\": ' in text:
                category = text.split('category\": ')[1].split(',')[0].strip("\"\n}")
                category = None if data_util.is_empty(category) else category
            else:
                category = None
            return {
                "category": category,
                "question": query_text,
                "source": Source.KNOWLEDGE_BASE,
                "answer": answer_text,
            }
    # if not found, turn to LLM
    qa_template = Prompt(prompt_template_string)
    llm_query_engine = index.as_query_engine(text_qa_template=qa_template)
    response = llm_query_engine.query(query_text)
    answer_text = str(response)
    # save the question-answer pair to index
    question_answer_pair = f'"source": "conversation", "category": "", "question": {query_text}, "answer": {answer_text}'
    insert_text_into_index(question_answer_pair)
    return {
        "category": None,
        "question": query_text,
        "source": Source.CHATGPT35,
        "answer": answer_text,
    }


def insert_text_into_index(text, doc_id=None):
    document = Document(text=text)
    insert_into_index(document, doc_id=doc_id)


def insert_file_into_index(doc_file_path, doc_id=None):
    document = SimpleDirectoryReader(input_files=[doc_file_path]).load_data()[0]
    insert_into_index(document, doc_id=doc_id)


def insert_into_index(document, doc_id=None):
    """Insert new document into global index."""
    global index, stored_docs
    if doc_id is not None:
        document.doc_id = doc_id
    with lock:
        # Keep track of stored docs -- llama_index doesn't make this easy
        stored_docs[document.doc_id] = document.text
        index.insert(document)
        index.storage_context.persist(persist_dir=index_path)
        with open(pkl_path, "wb") as f:
            pickle.dump(stored_docs, f)


def get_documents_list():
    """Get the list of currently stored documents."""
    global stored_docs
    documents_list = []
    for doc_id, doc_text in stored_docs.items():
        documents_list.append({"id": doc_id, "text": doc_text})
    return documents_list


def main():
    # init the global index
    logger.info("initializing index...")
    initialize_index()
    logger.info("initializing index... done")
    # setup server
    manager = BaseManager(address=('', 5602), authkey=b'password')
    manager.register('query_index', query_index)
    manager.register('insert_text_into_index', insert_text_into_index)
    manager.register('insert_file_into_index', insert_file_into_index)
    manager.register('get_documents_list', get_documents_list)
    server = manager.get_server()
    logger.info("server started...")
    server.serve_forever()


if __name__ == "__main__":
    main()
