from pydantic import Field, BaseModel
from typing import Optional
from app.data.models.qa import Answer
from app.data.messages.response import BaseResponseModel
from app.data.models.mongodb import LlamaIndexDocumentMetaReadable


class QuestionAnsweringRequest(BaseModel):
    question: str = Field(..., description="question to be answered")

    class ConfigDict:
        json_schema_extra = {
            "example_relevant_and_in_knowledge_base": {
                "question": "How do I achieve consistent ball contact?"
            },
            "example_relevant_but_not_in_knowledge_base": {
                "question": "How much money it will cost if I buy a full set of golf clubs?"
            },
            "example_not_relevant": {"question": "What is the capital of United States of America?"},
        }


class QuestionAnsweringResponse(BaseResponseModel):
    data: Optional[Answer] = Field(None, description="answer to the question")


class DocumentRequest(BaseModel):
    doc_id: str = Field(..., description="document id")

    class ConfigDict:
        json_schema_extra = {
            "doc_id": "doc_id_1",
        }


class DocumentResponse(BaseResponseModel):
    data: Optional[LlamaIndexDocumentMetaReadable] = Field(None, description="document data")


class DeleteDocumentResponse(BaseResponseModel):
    """DeleteDocumentResponse"""
