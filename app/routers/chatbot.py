import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

import pymongo

from app.data.messages.chat import ChatRequest, ChatResponse, Originator
from app.data.models.mongodb import ChatData
from app.data.models.qa import Answer
from app.llama_index_server import index_server
from app.utils.log_util import logger
from app.utils.mongo_dao import MongoDao
from app.utils import data_consts


chatbot_router = APIRouter(
    prefix="/chat",
    tags=["chatbot"],
)


"""
How to ensure a unique id?: Using context var or header?
How to streaming data back?:
    https://cookbook.openai.com/examples/how_to_stream_completions
    https://stackoverflow.com/questions/75740652/fastapi-streamingresponse-not-streaming-with-generator-function

How to control the context length?: The size of the history messages

"""


"""
Workflow

- New conversation:
  - conversation_id
  - Other metadata: user_id, sequence number(Can the client get this)?
  - timestamp
  - author: (User or AI, message is sent by User or Bot)


Request design:
- Text
- conversation_id


Response design

- For non-streaming mode
  - Search for the history and sort by timestamp
- For streaming mode

"""

HISTORY_SIZE = 10

collection_name = "conversation"
db_name = "ai_bot"
mongodb = MongoDao(
    data_consts.MONGO_URI,
    db_name,
    collection_name=collection_name,
)


@chatbot_router.post(
    "/dialog",
    response_model=ChatResponse,
)
async def chat(request: ChatRequest):
    logger.info("Non streaming chat")
    conversation_id = request.conversation_id
    find_all_user_query = {
        "conversation_id": conversation_id,
        "originator": {"$ne": 2},
    }
    conversations = mongodb.find(
        find_all_user_query,
        limit=HISTORY_SIZE,
        sort=[("timestamp", pymongo.DESCENDING)],
    )
    conversations = list(conversations)

    logger.info(f"Found conversation size: {len(conversations)}")

    # Insert the dialog into mongodb
    ts = round(time.time() * 1000)
    data = ChatData(
        conversation_id=conversation_id,
        timestamp=str(ts),
        text=request.dialog,
        originator=Originator.User,
        source=None,
    )
    mongodb.insert_one(data)

    # Find in index
    response = index_server.chat(request.dialog, conversation_id, conversations)

    # Insert result into mongodb
    ts = round(time.time() * 1000)
    if response:
        chat_data = ChatData(
            conversation_id=conversation_id,
            timestamp=str(ts),
            text=response.answer,
            originator=Originator.Bot,
            source=response.source,
        )
        mongodb.insert_one(chat_data)
    return ChatResponse(data=response)


@chatbot_router.post("/streaming_dialog")
async def streaming_chat():
    ...
