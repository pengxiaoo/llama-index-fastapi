from pydantic import Field, BaseModel
from typing import List
from app.utils.data_util import milliseconds_to_human_readable


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
    In llama index, a Document is a container around any data source.
    reference: https://docs.llamaindex.ai/en/stable/getting_started/concepts.html
    """
    """
    Indexes:
        doc_id(primary)
    """
    doc_id: str = Field(..., description="Global unique id of the document")
    doc_text: str = Field(..., description="The text of the document")
    from_knowledge_base: bool = Field(..., description="If the document is from knowledge base")
    insert_timestamp: int = Field(..., description="The timestamp when the document is inserted")
    query_timestamps: List[int] = Field([], description="The timestamps when the document is queried")

    @staticmethod
    def collection_name():
        return "llama_index_document_meta"

    def __init__(self, **data):
        if "doc_id" not in data:
            # todo is there a better way to generate doc_id?
            data["doc_id"] = data["doc_text"]
        super().__init__(**data)


class LlamaIndexDocumentMetaReadable(LlamaIndexDocumentMeta):
    insert_time: str = Field(..., description="The time when the document is inserted, in human readable format")
    last_query_time: str = Field("", description="The time when the document is last queried")
    query_count: int = Field(0, description="How many times the document is queried")

    def __init__(self, **data):
        data["insert_time"] = milliseconds_to_human_readable(data["insert_timestamp"])
        super().__init__(**data)
        if len(self.query_timestamps) > 0:
            self.query_timestamps.sort()
            self.last_query_time = milliseconds_to_human_readable(self.query_timestamps[-1])
        self.query_count = len(self.query_timestamps)
