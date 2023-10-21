from fastapi import APIRouter
from app.data.messages.response import BaseResponseModel
from app.common.log_util import logger

qa_router = APIRouter(
    prefix="/qa",
    tags=["question answering"],
)


@qa_router.post("", response_model=BaseResponseModel)
async def answer_question():
    logger.info("answer question from user")
    return BaseResponseModel(data=[])
