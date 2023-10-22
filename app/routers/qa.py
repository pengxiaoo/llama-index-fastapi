from fastapi import APIRouter
from app.data.messages.qa import QuestionAnsweringRequest, QuestionAnsweringResponse
from app.common.log_util import logger

qa_router = APIRouter(
    prefix="/qa",
    tags=["question answering"],
)
