from pydantic import Field, BaseModel
from typing import Optional
from app.data.models.qa import Answer
from app.data.messages.response import BaseResponseModel


class QuestionAnsweringRequest(BaseModel):
    question: str = Field(..., description="question to be answered")

    class ConfigDict:
        json_schema_extra = {
            "example_golf_relevant_1": {"question": "How to play golf in bad whether?"},
            "example_golf_relevant_2": {
                "question": "How much money it will cost if I buy a full set of golf clubs?"
            },
            "example_not_relevant": {"question": "What is the capital of China?"},
        }


class QuestionAnsweringResponse(BaseResponseModel):
    data: Optional[Answer] = Field(None, description="answer to the question")
