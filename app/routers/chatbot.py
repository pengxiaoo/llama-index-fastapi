from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.data.messages.chat import ChatRequest, ChatResponse
from app.llama_index_server import index_server
from app.utils.log_util import logger


chatbot_router = APIRouter(
    prefix="/chat",
    tags=["chatbot"],
)


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
