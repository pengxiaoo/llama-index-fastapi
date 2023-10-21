from pydantic import Field, BaseModel
from typing import List, Any, Union
from app.data.models.qa import Answer
from app.data.messages.response import BaseResponseModel


class QuestionAnsweringRequest(BaseModel):
    question: str = Field(..., description="question to be answered")


class QuestionAnsweringResponse(BaseResponseModel):
    data: Union[str, Answer, List[Any]] = Field(..., description="answer to the question")
