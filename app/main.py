from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError
from app.utils.openapi import patch_openapi
from app.data.messages.status_code import StatusCode
from app.data.messages.response import CustomHTTPException
from app.routers.qa import qa_router
from app.utils.log_util import logger
import uvicorn
import time

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


@app.middleware("timing")
async def init_timing_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    end_time = time.time()
    response.headers["X-Response-Time"] = str((end_time - start_time) * 1000)
    return response


# Remove 422 error in the docs
patch_openapi(app)

prefix = "/api/v1"
app.include_router(qa_router, prefix=prefix)


def handle_error_msg(request, error_msg, error_code=None):
    request_url = str(request.url)
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


def main():
    # show if there is any python process running bounded to the port
    # ps -fA | grep python
    logger.info("Start api server")
    uvicorn.run("main:app", host="127.0.0.1", port=8081, reload=True)


if __name__ == "__main__":
    main()
