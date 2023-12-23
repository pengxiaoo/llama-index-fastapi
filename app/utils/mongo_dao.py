from pymongo import MongoClient
from pymongo.collection import Collection
from app.data.models.mongodb import CollectionModel
from app.utils.log_util import logger


class MongoDao:
    """
    Base Data Access Object for MongoDB.
    """

    def __init__(
            self,
            mongo_uri,
            db_name,
            collection_name,
            size_limit=0,
    ):
        self._client = MongoClient(mongo_uri)
        self._db = self._client[db_name]
        self._collection: Collection = self._db[collection_name]
        if size_limit > 0:
            self._size_limit = size_limit
        else:
            self._size_limit = 0

    def upsert_one(self, key_name, key_value, value: CollectionModel):
        logger.info(f"Upsert {key_name} = {key_value}")
        self._collection.update_one(
            {key_name: key_value},
            {"$set": value.model_dump()},
            upsert=True,
        )
        pruned_ids = []
        if 0 < self._size_limit < self.doc_size():
            pruned_ids = self.prune()
        return pruned_ids

    def find(self, query, projection):
        logger.info(f"Find with query = {query}, projection = {projection}")
        return self._collection.find(query, projection)

    def find_one(self, key_name, key_value):
        logger.info(f"Find {key_name} = {key_value}")
        doc = self._collection.find_one(
            {key_name: key_value},
        )
        return doc

    def delete_one(self, key_name, key_value):
        delete_result = self._collection.delete_one(
            {key_name: key_value},
        )
        logger.info(f"Delete {key_name} = {key_value}, delete_result = {delete_result}")
        return delete_result.deleted_count

    def delete_many(self, query):
        delete_result = self._collection.delete_many(
            query,
        )
        deleted_count = delete_result.deleted_count
        logger.info(f"Delete many with query = {query}, deleted_count = {deleted_count}")
        return deleted_count

    def doc_size(self):
        return self._collection.count_documents({})

    def prune(self):
        return []

    def cleanup_for_test(self):
        pass
