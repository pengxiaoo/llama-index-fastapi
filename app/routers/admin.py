from fastapi import APIRouter, Path, Depends
from fastapi.security import HTTPBasicCredentials
from app.data.messages.qa import DeleteDocumentResponse
from app.llama_index_server import index_server
from app.utils.log_util import logger
from app.utils import auth_util

admin_router = APIRouter(
    prefix="/admin",
    tags=["(admin) high priority admin operations, usually for testing and debugging"],
)


@admin_router.delete(
    "/documents/{doc_id}",
    response_model=DeleteDocumentResponse,
    description="delete a document by doc_id. only for testing",
)
async def delete_doc(doc_id: str = Path(..., title="The ID of the document to delete"),
                     credentials: HTTPBasicCredentials = Depends(auth_util.verify_credentials)):
    logger.info(f"Delete doc for {doc_id}")
    deleted_count = index_server.delete_doc(doc_id)
    return DeleteDocumentResponse(msg=f"Deleting {doc_id}. Deleted count = {deleted_count}")


@admin_router.post(
    "/cleanup",
    response_model=DeleteDocumentResponse,
    description="cleanup all the user query meta data in mongodb. only for testing",
)
async def cleanup_for_test(credentials: HTTPBasicCredentials = Depends(auth_util.verify_credentials)):
    logger.info(f"Cleanup for test")
    index_server.cleanup_for_test()
    return DeleteDocumentResponse(msg=f"Successfully cleanup")
