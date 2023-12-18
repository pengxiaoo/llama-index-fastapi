from fastapi import APIRouter, Request

from app.llama_index_server.index_server import delete_doc as _delete_doc
from app.llama_index_server.index_server import (
    insert_text_into_index,
    insert_file_into_index,
)
from app.llama_index_server.index_server import get_document as _get_document
from app.llama_index_server.index_server import query_index

index_router = APIRouter(
    prefix="/index",
    tags=["index server API"],
)


@index_router.post("/query", description="")
async def query(request: Request):
    json = await request.json()
    question = json["question"]
    return query_index(question)


@index_router.post("/insertion")
async def insert_doc_to_index(request: Request):
    """Insert document into index

    Args:
        doc_type: one of [TEXT, File]
    """
    json = await request.json()
    doc_type = json.get("doc_type", "Unknown").upper()
    doc_id = json.get("doc_id")
    if doc_type == "TEXT":
        text = json["text"]
        insert_text_into_index(text, doc_id)
    elif doc_type == "FILE":
        path = json["path"]
        insert_file_into_index(path, doc_id=doc_id)
    else:
        raise ValueError(f"Unknown doc_type: {doc_type}")


@index_router.delete("/{doc_id}")
async def delete_doc(doc_id: str):
    return _delete_doc(doc_id)


@index_router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    return _get_document(doc_id)
