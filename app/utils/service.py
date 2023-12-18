from app.llama_index_server.index_server import query_index as _query_index
from app.llama_index_server.index_server import insert_file_into_index as insert_file
from app.llama_index_server.index_server import insert_text_into_index as insert_text
from app.llama_index_server.index_server import delete_doc as _delete_doc
from app.llama_index_server.index_server import get_document as _get_document


class LLamaIndexService:
    def query_index(self, question):
        return _query_index(question)

    def insert_text_into_index(self, text, doc_id):
        return insert_text(text, doc_id)

    def insert_file_into_index(self, path, doc_id):
        return insert_file(path, doc_id)

    def delete_doc(self, doc_id):
        return _delete_doc(doc_id)

    def get_document(self, doc_id):
        return _get_document(doc_id)


__GLOBAL_SERIVCE__ = {"LLAMA_INDEX_SERVICE": LLamaIndexService()}


def get_service(service_name: str):
    if service_name not in __GLOBAL_SERIVCE__:
        raise ValueError(f"Unknown service: {service_name}")
    return __GLOBAL_SERIVCE__[service_name]
