from functools import lru_cache
from multiprocessing.managers import BaseManager


@lru_cache(maxsize=10)
def get_manager():
    manager = BaseManager(address=("localhost", 5602), authkey=b"password")
    manager.register("query_index")
    manager.register("insert_text_into_index")
    manager.register("insert_file_into_index")
    manager.register("get_document")
    manager.register("delete_doc")
    manager.connect()
    return manager
