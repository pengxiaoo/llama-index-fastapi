from app.utils.mongo_dao import MongoDao
from app.utils.log_util import logger
from app.utils.data_util import get_current_milliseconds, MILLISECONDS_PER_DAY
from app.data.models.mongodb import LlamaIndexDocumentMeta
from app.data.models.qa import Source

MONGO_URI = "mongodb://localhost:27017/"
DOCUMENT_META_LIMIT = 1000


class DocumentMetaDao(MongoDao):
    def __init__(self,
                 mongo_uri=MONGO_URI,
                 db_name=LlamaIndexDocumentMeta.db_name(),
                 collection_name=LlamaIndexDocumentMeta.collection_name(),
                 size_limit=DOCUMENT_META_LIMIT,
                 ):
        super().__init__(mongo_uri, db_name, collection_name, size_limit)

    def prune(self):
        """
        remove all documents that satisfy the following conditions:
            1. not from knowledge base, and
            2. inserted more than 7 days ago, and
            3. not queried in the last 7 days
        """
        logger.info(f"current doc size: {self.doc_size()}, pruning...")
        seven_days_ago = get_current_milliseconds() - 7 * MILLISECONDS_PER_DAY
        query = {
            "source": {"$ne": Source.KNOWLEDGE_BASE.value},
            "insert_timestamp": {"$lt": seven_days_ago},
            "query_timestamps": {
                "$not": {
                    "$elemMatch": {"$gte": seven_days_ago}
                }
            }
        }
        projection = {
            "_id": 0,
            "doc_id": 1,
        }
        pruned_doc_ids = []
        for doc in self.find(query, projection):
            pruned_doc_ids.append(doc["doc_id"])
        if len(pruned_doc_ids) > 0:
            self.delete_many(query)
        return pruned_doc_ids

    def cleanup_for_test(self):
        query = {
            "source": {"$ne": Source.KNOWLEDGE_BASE.value},
        }
        super().delete_many(query)
