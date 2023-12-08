from fastapi import APIRouter
from app.data.models.qa import Answer
from app.data.messages.qa import (
    DeleteDocumentResponse,
    QuestionAnsweringRequest,
    QuestionAnsweringResponse,
)
from app.utils.log_util import logger
from app.utils import manager_util

qa_router = APIRouter(
    prefix="/qa",
    tags=["question answering"],
)


@qa_router.post(
    "/query",
    response_model=QuestionAnsweringResponse,
    description="ask questions related to the knowledge base, return the answer if there is a good match, "
    "otherwise turn to chatgpt for answer",
)
async def answer_question(req: QuestionAnsweringRequest):
    logger.info("answer question from user")
    query_text = req.question
    manager = manager_util.get_manager()
    data = manager.query_index(query_text)._getvalue()
    answer = Answer(**data)
    return QuestionAnsweringResponse(data=answer)


@qa_router.get(
    "/documents",
    response_model=QuestionAnsweringResponse,
    description="only for testing",
)
async def get_document_list():
    logger.info("get document list")
    manager = manager_util.get_manager()
    documents = manager.get_document_list()._getvalue()
    return QuestionAnsweringResponse(data=documents)


@qa_router.delete(
    "/documents/{doc_id}",
    response_model=DeleteDocumentResponse,
    description="only for testing",
)
async def delete_doc(doc_id: str):
    logger.info(f"Delete doc for {doc_id}")
    manager = manager_util.get_manager()
    manager.delete_doc(doc_id)
    return DeleteDocumentResponse(msg=f"Successfully deleted {doc_id}")
