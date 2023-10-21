from fastapi import APIRouter
from app.data.messages.qa import QuestionAnsweringRequest, QuestionAnsweringResponse
from app.data.messages.response import BaseResponseModel

qa_router = APIRouter(
    prefix="/qa",
    tags=["question answering"],
)
