from llama_index.llms.base import ChatMessage
from pydantic import Field, BaseModel
from llama_index.core.llms.types import MessageRole
from app.data.models.mongodb import Message


class ChatRequest(BaseModel):
    conversation_id: str = Field(..., description="Unique id of the conversation")
    content: str = Field(..., description="Content of the chat message")

    def to_chat_message(self) -> ChatMessage:
        return ChatMessage(
            role=MessageRole.USER,
            content=self.content,
        )


class ChatResponse(BaseModel):
    data: Message = Field(..., description="response from the chatbot")
