from app.llama_index_server.index_server import query_index as _query_index
from app.llama_index_server.index_server import delete_doc as _delete_doc
from app.llama_index_server.index_server import get_document as _get_document
from app.llama_index_server.index_server import cleanup_for_test as _cleanup_for_test

LLAMA_INDEX_SERVICE = "LLAMA_INDEX_SERVICE"


class LLamaIndexService:

    def query_index(self, question):
        return _query_index(question)

    def delete_doc(self, doc_id):
        return _delete_doc(doc_id)

    def get_document(self, doc_id):
        return _get_document(doc_id)

    def cleanup_for_test(self):
        return _cleanup_for_test()


__GLOBAL_SERVICE__ = {
    LLAMA_INDEX_SERVICE: LLamaIndexService(),
}


def get_service(service_name: str):
    if service_name not in __GLOBAL_SERVICE__:
        raise ValueError(f"Unknown service: {service_name}")
    return __GLOBAL_SERVICE__[service_name]
