from pydantic import Field, BaseModel
from typing import Optional
from app.data.models.qa import Answer
from app.data.messages.response import BaseResponseModel


class QuestionAnsweringRequest(BaseModel):
    question: str = Field(..., description="question to be answered")


class QuestionAnsweringResponse(BaseResponseModel):
    data: Optional[Answer] = Field(None, description="answer to the question")
