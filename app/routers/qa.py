from fastapi import APIRouter
from app.data.messages.qa import QuestionAnsweringRequest, QuestionAnsweringResponse
from app.common.log_util import logger
from app.common import manager_util

qa_router = APIRouter(
    prefix="/qa",
    tags=["question answering"],
)


@qa_router.post("/query", response_model=QuestionAnsweringResponse)
async def answer_question(req: QuestionAnsweringRequest):
    logger.info("answer question from user")
    query_text = req.question
    manager = manager_util.get_manager()
    response = manager.query_index(query_text)._getvalue()
    sources = [{"text": str(x.source_text),
                "similarity": round(x.similarity, 2),
                "doc_id": str(x.doc_id),
                "start": x.node_info['start'],
                "end": x.node_info['end']
                } for x in response.source_nodes]
    # manager.insert_into_index(filepath, doc_id=filename)
    return QuestionAnsweringResponse(data=str(response))


@qa_router.get("/documents", response_model=QuestionAnsweringResponse)
async def get_documents_list(req: QuestionAnsweringRequest):
    manager = manager_util.get_manager()
    documents = manager.get_documents_list()._getvalue()
    return QuestionAnsweringResponse(data=documents)
