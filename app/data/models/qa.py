from enum import Enum
from pydantic import Field, BaseModel
from typing import Optional


class Source(str, Enum):
    KNOWLEDGE_BASE = "knowledge-base"
    CHATGPT35 = "gpt-3.5-turbo"
    CHATGPT4 = "gpt-4"
    CLAUDE_2 = "claude-2"


class Answer(BaseModel):
    """ """

    category: Optional[str] = Field(
        None, description="Category of the question, if it can be recognized"
    )
    question: str = Field(..., description="the original question")
    source: Source = Field(..., description="Source of the answer")
    answer: str = Field(..., description="answer to the question")
