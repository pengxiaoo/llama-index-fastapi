import os
import time
from typing import Dict, Any, Optional
import pickle
from pathlib import Path
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
from llama_index import (
    Document,
    Prompt,
    download_loader,
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    load_index_from_storage,
    SimpleDirectoryReader,
)
from llama_index.indices.base import BaseIndex
from llama_index.llms import OpenAI
from llama_index.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.indices.postprocessor import SimilarityPostprocessor
from app.data.models.qa import Source, get_default_answer_id
from app.utils.log_util import logger
from app.utils import jsonl_util, data_util

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
llama_index_home = os.path.join(parent_dir, "llama_index_server")
os.environ["LLAMA_INDEX_CACHE_DIR"] = f"{llama_index_home}/llama_index_cache"
index_path = f"{llama_index_home}/saved_index"
csv_path = os.path.join(parent_dir, "documents/golf-knowledge-base.csv")
jsonl_path = csv_path.replace(".csv", ".jsonl")
pkl_path = f"{llama_index_home}/pkl/stored_documents.pkl"
similarity_cutoff = 0.85
prompt_template_string = (
    "We have provided context information below. \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "Given this information, assume you are an experienced golf coach, "
    "please give short, simple, accurate, precise answer to the golfer beginner's question, "
    "limited to 80 words maximum. If the question is not relevant to golf, please answer "
    f"'{get_default_answer_id()}'.\n"
    "The question is: {query_str}\n"
)
index: Optional[BaseIndex] = None
STORED_DOCS_LIMIT = 1000
stored_docs = {}
# TODO: use mongodb to replace pickle for stored_docs
"""
stored_docs stores documents from both user's questions and the knowledge base.
it has a one to one mapping with the documents in the index.
the key is doc_id, in current version it is the question text itself;
the value is a tuple of 4 elements:
    doc_text: str,  which is the whole text of the document, typically contains question, answer, and category;
    from_knowledge_base: bool, which indicates whether the document is from knowledge base;
    insert_timestamp: float, which is the timestamp when the document is inserted;
    query_timestamps: List[float], which is a list of timestamps when the document is queried;
query_timestamps indicates the popularity of the document.
"""
lock = Lock()
current_model = Source.CHATGPT35


def initialize_index():
    """Create a new global index, or load one from the pre-set path."""
    global index, stored_docs
    llm = OpenAI(temperature=0.1, model=current_model)
    service_context = ServiceContext.from_defaults(llm=llm)
    with lock:
        if os.path.exists(index_path) and os.path.exists(index_path + "/docstore.json"):
            logger.info(f"Loading index from dir: {index_path}")
            index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=index_path),
                service_context=service_context,
            )
            if os.path.exists(pkl_path):
                logger.info(f"Loading from pickle: {pkl_path}")
                with open(pkl_path, "rb") as f:
                    stored_docs = pickle.load(f)
        else:
            data_util.assert_true(
                os.path.exists(csv_path) or os.path.exists(jsonl_path),
                f"both csv and jsonl file are not found: {csv_path}, {jsonl_path}",
            )
            if not os.path.exists(jsonl_path):
                logger.info(f"Converting csv to jsonl: {csv_path} -> {jsonl_path}")
                jsonl_util.csv_to_jsonl(csv_path, jsonl_path)
            json_reader = download_loader("JSONReader")
            loader = json_reader()
            documents = loader.load_data(file=Path(jsonl_path), is_jsonl=True)
            index = VectorStoreIndex.from_documents(
                documents, service_context=service_context
            )
            for doc in documents:
                question = doc.text.split('question": ')[1].split(",\n")[0].strip('"')
                doc_id = data_util.get_doc_id(question)
                stored_docs[doc_id] = doc.text, True, time.time(), []
            logger.info("Using VectorStoreIndex")
            index.storage_context.persist(persist_dir=index_path)
            with open(pkl_path, "wb") as f:
                pickle.dump(stored_docs, f)


def query_index(query_text) -> Dict[str, Any]:
    data_util.assert_not_none(query_text, "query cannot be none")
    global index, stored_docs
    logger.info(f"Query test: {query_text}")
    # first search locally
    local_query_engine = index.as_query_engine(
        response_synthesizer=get_response_synthesizer(
            response_mode=ResponseMode.NO_TEXT
        ),
        node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=similarity_cutoff)],
    )
    local_query_response = local_query_engine.query(query_text)
    if len(local_query_response.source_nodes) > 0:
        text = local_query_response.source_nodes[0].text
        # TODO encapsulate the following text extractions to functions
        if 'answer": ' in text:
            matched_question = text.split('question": ')[1].split(",\n")[0].strip('"')
            matched_doc_id = data_util.get_doc_id(matched_question)
            if matched_doc_id in stored_docs:
                stored_docs[matched_doc_id][3].append(time.time())
                from_knowledge_base = stored_docs[matched_doc_id][1]
            else:
                # means the document has been removed from stored_docs
                logger.warning(f"'{matched_doc_id}' is not found in stored_docs")
                stored_docs[matched_doc_id] = text, False, time.time(), []
                from_knowledge_base = False
            answer_text = text.split('answer": ')[1].strip('"\n}')
            if 'category": ' in text:
                category = text.split('category": ')[1].split(",")[0].strip('"\n}')
                category = None if data_util.is_empty(category) else category
            else:
                category = None
            return {
                "category": category,
                "question": query_text,
                "matched_question": matched_question,
                "source": Source.KNOWLEDGE_BASE if from_knowledge_base else Source.USER_ASKED,
                "answer": answer_text,
            }
    # if not found, turn to LLM
    qa_template = Prompt(prompt_template_string)
    llm_query_engine = index.as_query_engine(text_qa_template=qa_template)
    response = llm_query_engine.query(query_text)
    answer_text = str(response)
    # save the question-answer pair to index
    question_answer_pair = f'"source": {Source.USER_ASKED}, "category": "", "question": {query_text}, "answer": {answer_text}'
    doc_id = data_util.get_doc_id(query_text)
    insert_text_into_index(question_answer_pair, doc_id)
    return {
        "category": None,
        "question": query_text,
        "source": current_model,
        "answer": answer_text,
    }


def insert_text_into_index(text, doc_id):
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
    logger.info(f"Insert document with doc id = {document.doc_id}")
    with lock:
        index.insert(document)
        # TODO: a little heavy for each doc
        index.storage_context.persist(persist_dir=index_path)
        # Keep track of stored docs -- llama_index doesn't make this easy
        stored_docs[document.doc_id] = document.text, False, time.time(), []
        if len(stored_docs) > STORED_DOCS_LIMIT:
            # prune docs from user questions and are not re-queried in 7 days
            for doc_id, (doc_text, from_knowledge_base, insert_timestamp, query_timestamps) in stored_docs.items():
                if not from_knowledge_base \
                        and time.time() - insert_timestamp > 7 * 24 * 60 * 60 \
                        and len(query_timestamps) == 0:
                    index.delete_ref_doc(doc_id)
                    value = stored_docs.pop(doc_id, None)
                    if value:
                        index.docstore.delete_ref_doc(doc_id)
        with open(pkl_path, "wb") as f:
            pickle.dump(stored_docs, f)


def delete_doc(doc_id):
    data_util.assert_not_none(doc_id, "doc_id cannot be none")
    global index, stored_docs
    logger.info(f"Delete document with doc id: {doc_id}")
    with lock:
        if index:
            index.delete_ref_doc(doc_id)
            value = stored_docs.pop(doc_id, None)
            if value:
                index.docstore.delete_ref_doc(doc_id)


def get_document(doc_id):
    global stored_docs
    for stored_doc_id, (doc_text, from_knowledge_base, insert_timestamp, query_timestamps) in stored_docs.items():
        if doc_id == stored_doc_id:
            return {
                "doc_id": doc_id,
                "doc_text": doc_text,
                "from_knowledge_base": from_knowledge_base,
                "insert_time_display": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(insert_timestamp)),
                "query_times": len(query_timestamps),
            }
    return None


def main():
    # init the global index
    logger.info("initializing index...")
    initialize_index()
    logger.info("initializing index... done")
    # setup server
    manager = BaseManager(address=("localhost", 5602), authkey=b"password")
    manager.register("query_index", query_index)
    manager.register("insert_text_into_index", insert_text_into_index)
    manager.register("insert_file_into_index", insert_file_into_index)
    manager.register("get_document", get_document)
    manager.register("delete_doc", delete_doc)
    server = manager.get_server()

    logger.info("server started...")
    server.serve_forever()


if __name__ == "__main__":
    main()
