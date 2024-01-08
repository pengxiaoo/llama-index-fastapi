from enum import Enum
from typing import Optional
from pydantic import Field, BaseModel

from app.data.models.qa import Answer


class Originator(Enum):
    User = 1
    Bot = 2


class ChatRequest(BaseModel):
    conversation_id: str = Field(..., description="Unique id of the conversation")
    dialog: str = Field(..., description="Content of the current request")
    sequence_num: int = Field(..., description="The sequence number of current dialog")


class ChatResponse(BaseModel):
    data: Optional[Answer] = Field(None, description="Chat response")
