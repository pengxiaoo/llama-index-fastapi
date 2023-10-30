import os
from fastapi import APIRouter, UploadFile, File
from app.data.messages.qa import QuestionAnsweringRequest, QuestionAnsweringResponse, \
    BaseResponseModel
from app.common.log_util import logger
from app.common import manager_util

qa_router = APIRouter(
    prefix="/qa",
    tags=["question answering"],
)

PATH_DOCUMENTS = './documents'


@qa_router.post("/query", response_model=QuestionAnsweringResponse,
                description="ask questions related to the knowledge base, return the answer if there is a good match, "
                            "otherwise turn to chatgpt for answer")
async def answer_question(req: QuestionAnsweringRequest):
    logger.info("answer question from user")
    query_text = req.question
    manager = manager_util.get_manager()
    response = manager.query_index(query_text)._getvalue()
    return QuestionAnsweringResponse(data=response)


@qa_router.get("/documents", response_model=QuestionAnsweringResponse, description="only for testing")
async def get_documents_list():
    manager = manager_util.get_manager()
    documents = manager.get_documents_list()._getvalue()
    return QuestionAnsweringResponse(data=documents)


@qa_router.post("/uploadFile", response_model=BaseResponseModel, description="only for testing")
def upload_file(uploaded_file: UploadFile = File(..., description="files for indexing"), ):
    manager = manager_util.get_manager()
    try:
        filename = uploaded_file.filename
        filepath = os.path.join(PATH_DOCUMENTS, os.path.basename(filename))
        with open(filepath, 'wb') as buffer:
            buffer.write(uploaded_file.file.read())
        manager.insert_file_into_index(filepath, doc_id=filename)
    except Exception as e:
        return BaseResponseModel(msg="File uploaded failed: {}".format(str(e)))
    return BaseResponseModel(msg="File uploaded successfully")
