from pydantic import Field, BaseModel


class ChatReply(BaseModel):
    message: str = Field(..., description="Last chat message")
    reply: str = Field(..., description="Chat reply from assistant")
