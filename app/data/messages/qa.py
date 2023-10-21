from pydantic import Field
from app.data.models.qa import Answer
from app.data.messages.response import BaseResponseModel


class QuestionAnsweringResponse(BaseResponseModel):
    data: Answer = Field(..., description="answer to the question")
