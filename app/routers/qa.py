from fastapi import APIRouter, Path
from app.data.models.qa import Answer
from app.data.messages.qa import (
    DeleteDocumentResponse,
    QuestionAnsweringRequest,
    QuestionAnsweringResponse,
    DocumentRequest,
    DocumentResponse,
)
from app.llama_index_server import index_server
from app.utils.log_util import logger

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
    data = index_server.query_index(query_text)
    answer = Answer(**data)
    return QuestionAnsweringResponse(data=answer)


@qa_router.post(
    "/document",
    response_model=DocumentResponse,
    description="only for testing, check what's inside the document",
)
async def get_document(req: DocumentRequest):
    logger.info(f"get document for doc_id {req.doc_id}")
    document = index_server.get_document(req.doc_id)
    return DocumentResponse(data=document)


@qa_router.delete(
    "/documents/{doc_id}",
    response_model=DeleteDocumentResponse,
    description="delete a document by doc_id. only for testing",
)
async def delete_doc(doc_id: str = Path(..., title="The ID of the document to delete")):
    logger.info(f"Delete doc for {doc_id}")
    index_server.delete_doc(doc_id)
    return DeleteDocumentResponse(msg=f"Successfully deleted {doc_id}")


@qa_router.post(
    "/cleanup",
    response_model=DeleteDocumentResponse,
    description="cleanup all the user query meta data in mongodb. only for testing",
)
async def cleanup_for_test():
    logger.info(f"Cleanup for test")
    index_server.cleanup_for_test()
    return DeleteDocumentResponse(msg=f"Successfully cleanup")
