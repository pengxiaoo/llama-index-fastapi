from typing import Optional
from pydantic import Field, BaseModel
from llama_index.llms.base import MessageRole

from app.data.models.chat import ChatReply



class ChatRequest(BaseModel):
    conversation_id: str = Field(..., description="Unique id of the conversation")
    orignator: MessageRole = Field(..., description="Source of the dialog")
    dialog: str = Field(..., description="Content of the current request")
    sequence_num: int = Field(..., description="The sequence number of current dialog")


class ChatResponse(BaseModel):
    data: Optional[ChatReply] = Field(None, description="Chat reply")
