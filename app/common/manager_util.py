from functools import lru_cache
from multiprocessing.managers import BaseManager


@lru_cache(maxsize=10)
def get_manager():
    manager = BaseManager(address=('', 5602), authkey=b'password')
    manager.register('query_index')
    manager.register('insert_into_index')
    manager.register('get_documents_list')
    manager.connect()
    return manager