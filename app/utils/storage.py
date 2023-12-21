"""
Storage for index server
"""
import os
import pickle
import time
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

from app.data.models.qa import Source
from app.utils.log_util import logger
from app.utils import data_util, jsonl_util

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
llama_index_home = os.path.join(parent_dir, "llama_index_server")
os.environ["LLAMA_INDEX_CACHE_DIR"] = f"{llama_index_home}/llama_index_cache"
index_path = f"{llama_index_home}/saved_index"
csv_path = os.path.join(parent_dir, "documents/golf-knowledge-base.csv")
jsonl_path = csv_path.replace(".csv", ".jsonl")
pkl_path = f"{llama_index_home}/pkl/stored_documents.pkl"
similarity_cutoff = 0.85
STORED_DOCS_LIMIT = 1000


"""
What is in a row of a stored doc?

- Key: doc_id
- Value: A dict
  - doc_text
  - from_knowledge_base
  - insert_ts
  - query_tss

ts = timestamp
"""


class StoredDocs:

    def __init__(self, size_limit, index):
        self._stored_docs = {}
        self._size_limit = size_limit
        self._index = index

    def insert_doc(self, doc_id, value):
        logger.debug(f"Insert doc_id: {doc_id}")
        self._stored_docs[doc_id] = value
        self.prune()

    def update_doc(self, doc_id, updated_value):
        value = self._stored_docs[doc_id]
        value.update(**updated_value)
        self.insert_doc(doc_id, value)

    def find_doc(self, doc_id):
        logger.debug(f"Finding doc_id = {doc_id}")
        return self._stored_docs.get(doc_id)

    def delete_doc(self, doc_id):
        return self._stored_docs.pop(doc_id, None)

    def doc_size(self):
        return len(self._stored_docs)

    def prune(self):
        if self.doc_size() > self._size_limit:
            # prune docs from user questions and are not re-queried in 7 days
            for doc_id, data in self._stored_docs.items():
                from_knowledge_base = data["from_knowledge_base"]
                query_timestamps = data["query_tss"]
                insert_timestamp = data["insert_ts"]
                if (
                    not from_knowledge_base
                    and time.time() - insert_timestamp > 7 * 24 * 60 * 60
                    and len(query_timestamps) == 0
                ):
                    self._index.delete_ref_doc(doc_id)
                    value = self.delete_doc(doc_id)
                    if value:
                        self._index.docstore.delete_ref_doc(doc_id)

    def dump(self, path):
        with open(path, "wb") as writer:
            pickle.dump(self._stored_docs, writer)

    def load(self, path):
        with open(path, "rb") as reader:
            self._stored_docs.update(pickle.loads(reader.read()))
        for key, value in self._stored_docs.items():
            logger.debug("%s = %s", key, value)
        return self._stored_docs


class IndexStorage:
    def __init__(self):
        self._current_model = Source.CHATGPT35
        logger.info("initializing index...")
        self._index, self._stored_docs = self.initialize_index()
        logger.info("initializing index... done")
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
    def rw_index(self):
        with self._rwlock:
            yield self._index

    @contextmanager
    def r_stored_docs(self):
        with self._rlock:
            yield self._stored_docs

    @contextmanager
    def rw_stored_docs(self):
        with self._rwlock:
            yield self._stored_docs

    def delete_doc(self, doc_id):
        with self._rwlock:
            self._index.delete_ref_doc(doc_id)
            value = self._stored_docs.delete_doc(doc_id)
            if value:
                self._index.docstore.delete_ref_doc(value)

    def add_doc(self, doc, doc_id=None):
        if doc_id is not None:
            doc.doc_id = doc_id
        with self._rwlock:
            self._index.insert(doc)
            # TODO: a little heavy for each doc
            self._index.storage_context.persist(persist_dir=index_path)
            # Keep track of stored docs -- llama_index doesn't make this easy
            data = {
                "doc_text": doc.text,
                "from_knowledge_base": False,
                "insert_ts": time.time(),
                "query_tss": [],
            }
            self._stored_docs.insert_doc(doc.doc_id, data)
            self._stored_docs.dump(pkl_path)

    def initialize_index(self) -> Tuple[BaseIndex, StoredDocs]:
        """Create a new global index, or load one from the pre-set path."""
        llm = OpenAI(temperature=0.1, model=self._current_model)
        service_context = ServiceContext.from_defaults(llm=llm)
        if os.path.exists(index_path) and os.path.exists(index_path + "/docstore.json"):
            logger.info(f"Loading index from dir: {index_path}")
            index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=index_path),
                service_context=service_context,
            )
            stored_docs = StoredDocs(STORED_DOCS_LIMIT, index)
            if os.path.exists(pkl_path):
                logger.info(f"Loading from pickle: {pkl_path}")
                stored_docs.load(pkl_path)
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
            stored_docs = StoredDocs(STORED_DOCS_LIMIT, index)
            for doc in documents:
                question = doc.text.split('question": ')[1].split(",\n")[0].strip('"')
                doc_id = data_util.get_doc_id(question)
                data = {
                    "doc_text": doc.text,
                    "from_knowledge_base": True,
                    "insert_ts": time.time(),
                    "query_tss": [],
                }
                stored_docs.insert_doc(doc_id, data)
            logger.info("Using VectorStoreIndex")
            index.storage_context.persist(persist_dir=index_path)
            stored_docs.dump(pkl_path)
        logger.info(f"Stored docs size: {stored_docs.doc_size()}")
        return index, stored_docs


index_storage = IndexStorage()
