from enum import Enum
from pydantic import Field, BaseModel


class Model(str, Enum):
    CHATGPT35 = "gpt-3.5-turbo"
    CHATGPT4 = "gpt-4"


class Answer(BaseModel):
    """
    """
    model: Model = Field(..., description="model used to generate the answer")
    content: str = Field(..., description="content of the answer")
