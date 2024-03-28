from fastapi import APIRouter
import asyncio
from app.data.messages.chat import ChatRequest, ChatResponse
from app.llama_index_server import index_server
from app.utils.log_util import logger
from app.utils.data_consts import API_TIMEOUT

chatbot_router = APIRouter(
    prefix="/chat",
    tags=["chatbot"],
)


@chatbot_router.post(
    "/non-streaming",
    response_model=ChatResponse,
    description="Chat with the ai bot in a non streaming way.")
async def chat(request: ChatRequest):
    logger.info("Non streaming chat")
    conversation_id = request.conversation_id
    message = await asyncio.wait_for(index_server.chat(request.content, conversation_id), timeout=API_TIMEOUT)
    return ChatResponse(data=message)
