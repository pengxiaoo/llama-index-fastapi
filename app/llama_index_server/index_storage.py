import os
from contextlib import contextmanager
from pathlib import Path
from multiprocessing import RLock, Lock
from typing import Tuple
from llama_index.llms import OpenAI
from llama_index.indices.base import BaseIndex
from llama_index import (
    ServiceContext,
    load_index_from_storage,
    StorageContext,
    download_loader,
    VectorStoreIndex,
)
from app.data.models.qa import Source, extract_question
from app.data.models.mongodb import LlamaIndexDocumentMeta
from app.utils.log_util import logger
from app.utils import data_util, jsonl_util
from app.llama_index_server.document_meta_dao import DocumentMetaDao

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
llama_index_home = os.path.join(parent_dir, "llama_index_server")
os.environ["LLAMA_INDEX_CACHE_DIR"] = f"{llama_index_home}/llama_index_cache"
index_path = f"{llama_index_home}/saved_index"
csv_path = os.path.join(parent_dir, f"{llama_index_home}/documents/golf-knowledge-base.csv")
jsonl_path = csv_path.replace(".csv", ".jsonl")


class IndexStorage:
    def __init__(self):
        self._current_model = Source.CHATGPT35
        logger.info("initializing index and mongo ...")
        self._index, self._mongo = self.initialize_index()
        logger.info("initializing index and mongo done")
        self._rlock = RLock()
        self._rwlock = Lock()

    @property
    def current_model(self):
        return self._current_model

    @contextmanager
    def r_index(self):
        with self._rlock:
            yield self._index

    @contextmanager
    def r_mongo(self):
        with self._rlock:
            yield self._mongo

    @contextmanager
    def rw_mongo(self):
        with self._rwlock:
            yield self._mongo

    def delete_doc(self, doc_id):
        """remove from both index and mongo"""
        with self._rwlock:
            self._index.delete_ref_doc(doc_id, delete_from_docstore=True)
            self._index.storage_context.persist(persist_dir=index_path)
            self._mongo.delete_one("doc_id", doc_id)

    def add_doc(self, doc, doc_id=None):
        """add to both index and mongo"""
        with self._rwlock:
            if doc_id is not None:
                doc.doc_id = doc_id
            self._index.insert(doc)
            self._index.storage_context.persist(persist_dir=index_path)
            doc_meta = LlamaIndexDocumentMeta(
                doc_id=doc_id,
                doc_text=doc.text,
                from_knowledge_base=False,
                insert_timestamp=data_util.get_current_milliseconds(),
                query_timestamps=[],
            )
            pruned_doc_ids = self._mongo.upsert_one("doc_id", doc.doc_id, doc_meta)
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
            logger.info("Using VectorStoreIndex")
            index.storage_context.persist(persist_dir=index_path)
            for doc in documents:
                question = extract_question(doc.text)
                doc_id = data_util.get_doc_id(question)
                doc_meta = LlamaIndexDocumentMeta(
                    doc_id=doc_id,
                    doc_text=doc.text,
                    from_knowledge_base=True,
                    insert_timestamp=data_util.get_current_milliseconds(),
                    query_timestamps=[],
                )
                # todo use batch upsert
                mongo.upsert_one("doc_id", doc_id, doc_meta)
        logger.info(f"Stored docs size: {mongo.doc_size()}")
        return index, mongo


index_storage = IndexStorage()
