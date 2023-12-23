import os
from contextlib import contextmanager
from multiprocessing import Lock
from typing import Tuple
from llama_index.llms import OpenAI
from llama_index.indices.base import BaseIndex
from llama_index import (
    ServiceContext,
    load_index_from_storage,
    StorageContext,
    VectorStoreIndex,
)
from app.data.models.qa import Source, Answer
from app.data.models.mongodb import LlamaIndexDocumentMeta
from app.utils.log_util import logger
from app.utils import data_util, csv_util
from app.llama_index_server.document_meta_dao import DocumentMetaDao

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
llama_index_home = os.path.join(parent_dir, "llama_index_server")
os.environ["LLAMA_INDEX_CACHE_DIR"] = f"{llama_index_home}/llama_index_cache"
index_path = f"{llama_index_home}/saved_index"
csv_path = os.path.join(parent_dir, f"{llama_index_home}/documents/golf-knowledge-base.csv")


class IndexStorage:
    def __init__(self):
        self._current_model = Source.CHATGPT35
        logger.info("initializing index and mongo ...")
        self._index, self._mongo = self.initialize_index()
        logger.info("initializing index and mongo done")
        self._rwlock = Lock()

    @property
    def current_model(self):
        return self._current_model

    def mongo(self):
        return self._mongo

    def index(self):
        return self._index

    @contextmanager
    def rw_lock(self):
        with self._rwlock:
            yield

    def delete_doc(self, doc_id):
        """remove from both index and mongo"""
        with self.rw_lock():
            self._index.delete_ref_doc(doc_id, delete_from_docstore=True)
            self._index.storage_context.persist(persist_dir=index_path)
            return self._mongo.delete_one({"doc_id": doc_id})

    def add_doc(self, answer: Answer):
        """add to both index and mongo"""
        with self.rw_lock():
            doc = answer.to_llama_index_document()
            self._index.insert(doc)
            # todo: no need to persist every time. could be batched or periodically
            self._index.storage_context.persist(persist_dir=index_path)
            doc_meta = LlamaIndexDocumentMeta.from_answer(answer)
            pruned_doc_ids = self._mongo.upsert_one({"doc_id": doc.doc_id}, doc_meta)
            if len(pruned_doc_ids) > 0:
                for pruned_doc_id in pruned_doc_ids:
                    self._index.delete_ref_doc(pruned_doc_id, delete_from_docstore=True)
                self._index.storage_context.persist(persist_dir=index_path)

    def initialize_index(self) -> Tuple[BaseIndex, DocumentMetaDao]:
        llm = OpenAI(temperature=0.1, model=self._current_model)
        service_context = ServiceContext.from_defaults(llm=llm)
        mongo = DocumentMetaDao()
        if os.path.exists(index_path) and os.path.exists(index_path + "/docstore.json"):
            logger.info(f"Loading index from dir: {index_path}")
            index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=index_path),
                service_context=service_context,
            )
        else:
            data_util.assert_true(os.path.exists(csv_path), f"csv file not found: {csv_path}")
            standard_answers = csv_util.load_standard_answers_from_csv(csv_path)
            documents = [answer.to_llama_index_document() for answer in standard_answers]
            index = VectorStoreIndex.from_documents(documents, service_context=service_context)
            index.storage_context.persist(persist_dir=index_path)
            doc_metas = [LlamaIndexDocumentMeta.from_answer(answer).model_dump() for answer in standard_answers]
            mongo.bulk_upsert(doc_metas, primary_keys=["doc_id"])
        logger.info(f"Stored docs size: {mongo.doc_size()}")
        return index, mongo


index_storage = IndexStorage()
