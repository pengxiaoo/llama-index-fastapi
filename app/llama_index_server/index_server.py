import os
import pickle
from pathlib import Path
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
from llama_index import Document, download_loader, GPTVectorStoreIndex, ServiceContext, StorageContext, \
    load_index_from_storage, SimpleDirectoryReader
from llama_index.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.indices.postprocessor import SimilarityPostprocessor
from app.common.log_util import logger

llama_index_home = "./llama_index_server"
os.environ["LLAMA_INDEX_CACHE_DIR"] = f"{llama_index_home}/llama_index_cache"
index_name = f"{llama_index_home}/saved_index"
pkl_home = f"{llama_index_home}/pkl"
pkl_name = f"{pkl_home}/stored_documents.pkl"
index = None
stored_docs = {}
lock = Lock()


def initialize_index():
    """Create a new global index, or load one from the pre-set path."""
    global index, stored_docs
    service_context = ServiceContext.from_defaults(chunk_size_limit=512)
    with lock:
        if os.path.exists(index_name):
            logger.info(f"Loading index from dir: {index_name}")
            index = load_index_from_storage(StorageContext.from_defaults(persist_dir=index_name),
                                            service_context=service_context)
        else:
            json_reader = download_loader("JSONReader")
            loader = json_reader()
            documents = loader.load_data(file=Path('./documents/golf-knowledge-base.jsonl'), is_jsonl=True)
            index = GPTVectorStoreIndex.from_documents(documents, service_context=service_context)
            logger.info("Using GPTVectorStoreIndex")
            index.storage_context.persist(persist_dir=index_name)
        if os.path.exists(pkl_name):
            logger.info(f"Loading from pickle: {pkl_name}")
            with open(pkl_name, "rb") as f:
                stored_docs = pickle.load(f)


def query_index(query_text):
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
        response = local_query_response.source_nodes[0].text
        if 'answer": ' in response:
            response = response.split('answer": ')[1].strip("\"\n}")
    else:
        # if not found, turn to LLM
        llm_query_engine = index.as_query_engine()
        response = llm_query_engine.query(query_text)
        response = str(response)
        # save the question-answer pair to index
        question_answer_pair = f'"source": "conversation", "category":"", "question": {query_text}, "answer": {response}'
        insert_text_into_index(question_answer_pair)

    return response


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
        stored_docs[document.doc_id] = document.text[0:200]  # only take the first 200 chars
        index.insert(document)
        index.storage_context.persist(persist_dir=index_name)
        with open(pkl_name, "wb") as f:
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
