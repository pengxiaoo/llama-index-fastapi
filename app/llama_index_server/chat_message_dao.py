from app.utils.mongo_dao import MongoDao
from app.utils import data_consts
from app.data.models.mongodb import Message


class ChatMessageDao(MongoDao):
    def __init__(self,
                 mongo_uri=data_consts.MONGO_URI,
                 db_name=Message.db_name(),
                 collection_name=Message.collection_name(),
                 ):
        super().__init__(mongo_uri, db_name, collection_name)
