from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError
from multiprocessing.managers import BaseManager
from app.data.messages.status_code import StatusCode
from app.data.messages.response import CustomHTTPException
from app.data.messages.qa import QuestionAnsweringRequest, QuestionAnsweringResponse
from app.data.messages.response import BaseResponseModel
from app.routers.qa import qa_router
from app.common.log_util import logger, ERROR_MSG_USER_NOT_FOUND
import uvicorn

# os.environ["OPENAI_API_KEY"] = "your key here"

app = FastAPI(
    title="Api Definitions for Question Answering",
    servers=[
        {"url": "http://127.0.0.1:8081",
         "description": "Local test environment", },
    ],
    version="0.0.1")

# Enable CORS for *
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = "/api/v1"
app.include_router(qa_router, prefix=prefix)

# initialize manager connection
# NOTE: you might want to handle the password in a less hardcoded way
manager = BaseManager(('', 5602), b'password')
manager.register('query_index')
manager.register('insert_into_index')
manager.register('get_documents_list')
manager.connect()


def handle_error_msg(request, error_msg, error_code=None):
    request_url = str(request.url)
    if error_code == "UserNotFoundException":
        error_msg = f"client error in {request_url}: {ERROR_MSG_USER_NOT_FOUND}"
    else:
        error_msg = f"client error in {request_url}: {error_msg}"
    logger.error(error_msg)
    result = error_msg.split(":")[-1].strip()
    return result


@app.exception_handler(CustomHTTPException)
async def custom_exception_handler(request, exc):
    msg = exc.detail
    error_msg = handle_error_msg(request, msg)
    return JSONResponse(status_code=400, content={
        "status_code": exc.custom_status_code,
        "msg": error_msg,
    })


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    msg = exc.errors()[0]["msg"]
    error_msg = handle_error_msg(request, msg)
    return JSONResponse(status_code=400, content={
        "status_code": StatusCode.ERROR_INPUT_FORMAT,
        "msg": error_msg,
    })


@app.exception_handler(ClientError)
async def client_error_handler(request, exc):
    error_code = exc.response["Error"]["Code"]
    error_msg = exc.response["Error"]["Message"]
    error_msg = handle_error_msg(request, error_msg, error_code)
    return JSONResponse(status_code=400, content={
        "status_code": StatusCode.ERROR_INPUT_FORMAT,
        "msg": error_msg,
    })


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    error_msg = handle_error_msg(request, str(exc))
    return JSONResponse(status_code=400, content={
        "status_code": StatusCode.ERROR_INPUT_FORMAT,
        "msg": error_msg,
    })


@app.exception_handler(KeyError)
async def key_error_handler(request, exc):
    error_msg = handle_error_msg(request, "KeyError - " + str(exc))
    return JSONResponse(status_code=400, content={
        "status_code": StatusCode.ERROR_INPUT_FORMAT,
        "msg": error_msg,
    })


@app.post("/query", response_model=QuestionAnsweringResponse)
async def answer_question(req: QuestionAnsweringRequest):
    # logger.info("answer question from user")
    global manager
    query_text = req.question
    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    # TODO manager.insert_into_index(filepath, doc_id=filename)
    response = manager.query_index(query_text)._getvalue()
    sources = [{"text": str(x.source_text),
                "similarity": round(x.similarity, 2),
                "doc_id": str(x.doc_id),
                "start": x.node_info['start'],
                "end": x.node_info['end']
                } for x in response.source_nodes]
    return QuestionAnsweringResponse(data=str(response))


@app.get("/documents", response_model=QuestionAnsweringResponse)
async def get_documents_list(req: QuestionAnsweringRequest):
    global manager
    documents = manager.get_documents_list()._getvalue()
    return BaseResponseModel(data=documents)


if __name__ == "__main__":
    # show if there is any python process running bounded to the port
    # ps -fA | grep python
    uvicorn.run("main:app", host="127.0.0.1", port=8081, reload=True)
