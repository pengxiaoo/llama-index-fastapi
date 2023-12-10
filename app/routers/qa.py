from fastapi import APIRouter, Path
from app.data.models.qa import Answer
from app.data.messages.qa import (
    DeleteDocumentResponse,
    QuestionAnsweringRequest,
    QuestionAnsweringResponse,
    DocumentRequest,
    DocumentResponse,
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


@qa_router.post(
    "/document/",
    response_model=DocumentResponse,
    description="only for testing, check what's inside the document",
)
async def get_document(req: DocumentRequest):
    logger.info(f"get document for doc_id {req.doc_id}")
    manager = manager_util.get_manager()
    document = manager.get_document(req.doc_id)._getvalue()
    return DocumentResponse(data=document)


@qa_router.delete(
    "/documents/{doc_id}",
    response_model=DeleteDocumentResponse,
    description="only for testing",
)
async def delete_doc(doc_id: str = Path(..., title="The ID of the document to delete")):
    logger.info(f"Delete doc for {doc_id}")
    manager = manager_util.get_manager()
    manager.delete_doc(doc_id)
    return DeleteDocumentResponse(msg=f"Successfully deleted {doc_id}")
