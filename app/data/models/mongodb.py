from pydantic import Field, BaseModel
from typing import List, Optional
from llama_index.llms.base import MessageRole
from app.utils import data_util
from app.data.models.qa import Source


class CollectionModel(BaseModel):
    """
        Base class for all the collections stored in MongoDB.
    """

    @staticmethod
    def db_name():
        return "ai_bot"

    @staticmethod
    def collection_name():
        return None


class LlamaIndexDocumentMeta(CollectionModel):
    """
    meta data of llama index document.

    In llama index, a `Document` is a container around any data source.
    reference: https://docs.llamaindex.ai/en/stable/getting_started/concepts.html
    """
    """
    Indexes:
        doc_id(primary)
    """
    doc_id: str = Field(..., description="Global unique id of the document")
    question: str = Field(..., description="the original question")
    matched_question: Optional[str] = Field(None, description="matched question, if any")
    category: Optional[str] = Field(None, description="Category of the question, if it can be recognized")
    source: Source = Field(..., description="Source of the answer")
    answer: str = Field(..., description="answer to the question")
    insert_timestamp: int = Field(..., description="The timestamp when the document is inserted, in milliseconds")
    query_timestamps: List[int] = Field([], description="The timestamps when the document is queried")

    @staticmethod
    def collection_name():
        return "llama_index_document_meta"

    @staticmethod
    def from_answer(answer):
        doc_meta = LlamaIndexDocumentMeta(
            doc_id=data_util.get_doc_id(answer.question),
            question=answer.question,
            matched_question=answer.matched_question,
            source=answer.source.value,
            category=answer.category,
            answer=answer.answer,
            insert_timestamp=data_util.get_current_milliseconds(),
            query_timestamps=[],
        )
        return doc_meta

    def __init__(self, **data):
        if "doc_id" not in data:
            data["doc_id"] = data_util.get_doc_id(data["question"])
        super().__init__(**data)


class LlamaIndexDocumentMetaReadable(LlamaIndexDocumentMeta):
    insert_time: str = Field(..., description="The time when the document is inserted, in human readable format")
    last_query_time: str = Field("", description="The time when the document is last queried")
    query_count_7_days: int = Field(0, description="How many times the document is queried in last 7 days")

    def __init__(self, **data):
        data["insert_time"] = data_util.milliseconds_to_human_readable(data["insert_timestamp"])
        super().__init__(**data)
        if len(self.query_timestamps) > 0:
            self.query_timestamps.sort()
            self.last_query_time = data_util.milliseconds_to_human_readable(self.query_timestamps[-1])
        self.query_count_7_days = len([t for t in self.query_timestamps if
                                       t > data_util.get_current_milliseconds() - 7 * data_util.MILLISECONDS_PER_DAY])


class ChatData(CollectionModel):
    conversation_id: str = Field(..., description="Unique id of the conversation")
    timestamp: str = Field(..., description="Time in milliseconds")
    text: str = Field(..., description="Content of the conversation")
    originator: MessageRole = Field(..., description="Originator of the dialog")

    @staticmethod
    def collection_name():
        return "converstations"
