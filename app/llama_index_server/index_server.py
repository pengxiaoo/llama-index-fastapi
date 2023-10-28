import os
import pickle
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
from llama_index import SimpleDirectoryReader, GPTVectorStoreIndex, ServiceContext, StorageContext, \
    load_index_from_storage
from app.common.log_util import logger

# NOTE: for local testing only, do NOT deploy with your key hardcoded
index = None
stored_docs = {}
lock = Lock()
index_name = "llama_index_server/saved_index"
pkl_name = "llama_index_server/pkl/stored_documents.pkl"


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
            index = GPTVectorStoreIndex([], service_context=service_context)
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
    response = index.as_query_engine().query(query_text)
    return response


def insert_into_index(doc_file_path, doc_id=None):
    """Insert new document into global index."""
    global index, stored_docs
    document = SimpleDirectoryReader(input_files=[doc_file_path]).load_data()[0]
    if doc_id is not None:
        document.doc_id = doc_id

    with lock:
        # Keep track of stored docs -- llama_index_server doesn't make this easy
        stored_docs[document.doc_id] = document.text[0:200]  # only take the first 200 chars

        index.insert(document)
        index.storage_context.persist(persist_dir=index_name)

        with open(pkl_name, "wb") as f:
            pickle.dump(stored_docs, f)

    return


def get_documents_list():
    """Get the list of currently stored documents."""
    global stored_doc
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
    # NOTE: you might want to handle the password in a less hardcoded way
    manager = BaseManager(address=('', 5602), authkey=b'password')
    manager.register('query_index', query_index)
    manager.register('insert_into_index', insert_into_index)
    manager.register('get_documents_list', get_documents_list)
    server = manager.get_server()

    logger.info("server started...")
    server.serve_forever()


if __name__ == "__main__":
    main()
