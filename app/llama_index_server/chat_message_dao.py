from typing import List
import pymongo
from llama_index.core.llms.base import ChatMessage
from app.utils.mongo_dao import MongoDao
from app.utils import data_consts
from app.data.models.mongodb import Message
from app.utils.log_util import logger

CHAT_HISTORY_LIMIT = 20


class ChatMessageDao(MongoDao):
    def __init__(self,
                 mongo_uri=data_consts.MONGO_URI,
                 db_name=Message.db_name(),
                 collection_name=Message.collection_name(),
                 ):
        super().__init__(mongo_uri, db_name, collection_name)

    def get_chat_history(self, conversation_id: str) -> List[Message]:
        messages = self.find(
            query={"conversation_id": conversation_id, },
            limit=CHAT_HISTORY_LIMIT,
            sort=[("timestamp", pymongo.DESCENDING)],
        )
        if messages is None:
            return []
        else:
            messages = list(messages)
            messages = [Message(**m) for m in messages]
            messages.sort(key=lambda m: m.timestamp)
            logger.info(f"Found message history size: {len(messages)}")
            return messages

    def save_chat_history(self, conversation_id: str, chat_message: ChatMessage):
        message = Message.from_chat_message(conversation_id, chat_message)
        self.insert_one(message)
