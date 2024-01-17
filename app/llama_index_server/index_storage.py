from collections import deque
import os
from functools import lru_cache
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

CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
LLAMA_INDEX_HOME = os.path.join(PARENT_DIR, "llama_index_server")
os.environ["LLAMA_INDEX_CACHE_DIR"] = f"{LLAMA_INDEX_HOME}/llama_index_cache"
INDEX_PATH = f"{LLAMA_INDEX_HOME}/saved_index"
CSV_PATH = os.path.join(PARENT_DIR, f"{LLAMA_INDEX_HOME}/documents/golf-knowledge-base.csv")
PERSIST_INTERVAL = 3600


class IndexStorage:
    def __init__(self):
        self._current_model = Source.CHATGPT35
        logger.info("initializing index and mongo ...")
        self._index, self._mongo = self.initialize_index()
        logger.info("initializing index and mongo done")
        self._lock = Lock()
        self._last_persist_time = 0
        self._chat_engine_record = {}

    @property
    def chat_engine_record(self):
        return self._chat_engine_record

    @property
    def current_model(self):
        return self._current_model

    def mongo(self):
        return self._mongo

    def index(self):
        return self._index

    @contextmanager
    def lock(self):
        # for the write operations on self._index
        with self._lock:
            yield

    def delete_doc(self, doc_id):
        """remove from both index and mongo"""
        with self.lock():
            self._index.delete_ref_doc(doc_id, delete_from_docstore=True)
            self._index.storage_context.persist(persist_dir=INDEX_PATH)
            return self._mongo.delete_one({"doc_id": doc_id})

    def add_doc(self, answer: Answer):
        """add to both index and mongo"""
        with self.lock():
            doc = answer.to_llama_index_document()
            self._index.insert(doc)
            current_time = data_util.get_current_seconds()
            if current_time - self._last_persist_time >= PERSIST_INTERVAL:
                self._index.storage_context.persist(persist_dir=INDEX_PATH)
                self._last_persist_time = current_time
            doc_meta = LlamaIndexDocumentMeta.from_answer(answer)
            pruned_doc_ids = self._mongo.upsert_one({"doc_id": doc.doc_id}, doc_meta, need_prune=True)
            if len(pruned_doc_ids) > 0:
                for pruned_doc_id in pruned_doc_ids:
                    self._index.delete_ref_doc(pruned_doc_id, delete_from_docstore=True)
                self._index.storage_context.persist(persist_dir=INDEX_PATH)

    def initialize_index(self) -> Tuple[BaseIndex, DocumentMetaDao]:
        llm = OpenAI(temperature=0.1, model=self._current_model)
        service_context = ServiceContext.from_defaults(llm=llm)
        mongo = DocumentMetaDao()
        if os.path.exists(INDEX_PATH) and os.path.exists(INDEX_PATH + "/docstore.json"):
            logger.info(f"Loading index from dir: {INDEX_PATH}")
            index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=INDEX_PATH),
                service_context=service_context,
            )
        else:
            data_util.assert_true(os.path.exists(CSV_PATH), f"csv file not found: {CSV_PATH}")
            standard_answers = csv_util.load_standard_answers_from_csv(CSV_PATH)
            documents = [answer.to_llama_index_document() for answer in standard_answers]
            index = VectorStoreIndex.from_documents(documents, service_context=service_context)
            index.storage_context.persist(persist_dir=INDEX_PATH)
            doc_metas = [LlamaIndexDocumentMeta.from_answer(answer).model_dump() for answer in standard_answers]
            mongo.bulk_upsert(doc_metas, primary_keys=["doc_id"])
        logger.info(f"Stored docs size: {mongo.doc_size()}")
        return index, mongo


index_storage = IndexStorage()


class ChatEngine:
    """Class to keep track of all the chat engine"""
    def __init__(self, limit=10):
        self._data = {}
        self._limit = limit
        self._deque = deque(maxlen=limit)

    def get(self, conversation_id):
        """Get a chat engine according to conversation_id

        Args:
            conversation_id: the unique id of the conversation

        Returns:
            engine
            bool: whether it is newly created
        """
        engine = self._data.get(conversation_id)
        if engine:
            return engine, False
        if len(self._data) > self._limit:
            front = self._deque.popleft()
            logger.info(f"Delete engine for {front}")
            del self._data[front]
        self._deque.append(conversation_id)
        logger.info(f"Create a new chat engine for {conversation_id}")
        engine = index_storage.index().as_chat_engine()
        self._data[conversation_id] = engine
        return engine, True


chat_engine = ChatEngine()
