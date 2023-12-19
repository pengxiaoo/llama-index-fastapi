from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.openapi import patch_openapi
from app.llama_index_server.router import index_router
from app.utils.log_util import logger
import uvicorn

app = FastAPI(
    title="Front end from llama-index",
    servers=[
        {
            "url": "http://127.0.0.1:8082",
            "description": "Local environment for llama index server",
        },
    ],
    version="0.0.1",
)

# Enable CORS for *
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Remove 422 error in the docs
patch_openapi(app)

prefix = "/api/v1"
app.include_router(index_router, prefix=prefix)


def main():
    # show if there is any python process running bounded to the port
    # ps -fA | grep python
    logger.info("Start llama index server")
    uvicorn.run("app.llama_index_server.main:app", host="127.0.0.1", port=8082)


if __name__ == "__main__":
    main()
