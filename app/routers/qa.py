from fastapi import APIRouter
from app.data.messages.qa import (
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
    description="ask questions related to golf, return a standard answer if there is a good match in the knowledge "
                "base, otherwise turn to chatgpt for an answer. if the question is not related to golf at all, "
                "return a default answer telling the user to ask another question",
)
async def answer_question(req: QuestionAnsweringRequest):
    logger.info("answer question from user")
    query_text = req.question
    answer = index_server.query_index(query_text)
    return QuestionAnsweringResponse(data=answer)


@qa_router.post(
    "/document",
    response_model=DocumentResponse,
    description="check what's inside the document. mainly for testing",
)
async def get_document(req: DocumentRequest):
    logger.info(f"get document for doc_id {req.doc_id}, fuzzy search: {req.fuzzy}")
    document = index_server.get_document(req)
    return DocumentResponse(data=document)
