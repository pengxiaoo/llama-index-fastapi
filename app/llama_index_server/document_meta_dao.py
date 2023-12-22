from app.utils.mongo_dao import MongoDao
from app.utils.log_util import logger
from app.utils.data_util import get_current_milliseconds, MILLISECONDS_PER_DAY

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "ai_bot"
COLLECTION_NAME = "user_queries"
DOCUMENT_META_LIMIT = 1000


class DocumentMetaDao(MongoDao):
    def __init__(self,
                 mongo_uri=MONGO_URI,
                 db_name=DB_NAME,
                 collection_name=COLLECTION_NAME,
                 size_limit=DOCUMENT_META_LIMIT,
                 ):
        super().__init__(mongo_uri, db_name, collection_name, size_limit)

    def prune(self):
        logger.info(f"current doc size: {self.doc_size()}, pruning...")
        current_time = get_current_milliseconds()
        # todo optimize the pruning algorithm.
        # todo add unit test for pruning
        query = {
            "from_knowledge_base": False,
            "insert_timestamp": {"$lt": current_time - 7 * MILLISECONDS_PER_DAY},
            "query_timestamps": {"$size": 0}
        },
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
            "from_knowledge_base": False
        }
        super().delete_many(query)
