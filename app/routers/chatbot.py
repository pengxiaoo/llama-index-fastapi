from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.data.messages.chat import ChatRequest, ChatResponse
from app.llama_index_server import index_server
from app.utils.log_util import logger


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


@chatbot_router.post(
    "/dialog",
    response_model=ChatResponse,
)
async def chat(request: ChatRequest):
    logger.info("Non streaming chat")
    conversation_id = request.conversation_id
    response = index_server.chat(request.dialog, conversation_id)
    return ChatResponse(data=response)


@chatbot_router.post("/streaming_dialog")
async def streaming_chat(request: ChatRequest):
    logger.info("Non streaming chat")
    conversation_id = request.conversation_id
    return StreamingResponse(
        index_server.stream_chat(request.dialog, conversation_id),
        media_type='text/event-stream'
    )
