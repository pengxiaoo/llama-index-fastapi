import time
from typing import Any, Dict
from multiprocessing.managers import BaseManager
from llama_index import (
    Document,
    Prompt,
    SimpleDirectoryReader,
)
from llama_index.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.indices.postprocessor import SimilarityPostprocessor
from app.data.models.qa import Source, get_default_answer_id
from app.utils.log_util import logger
from app.utils import data_util
from app.utils.storage import index_storage

similarity_cutoff = 0.85
prompt_template_string = (
    "We have provided context information below. \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "Given this information, assume you are an experienced golf coach, "
    "please give short, simple, accurate, precise answer to the golfer beginner's question, "
    "limited to 80 words maximum. If the question is not relevant to golf, please answer "
    f"'{get_default_answer_id()}'.\n"
    "The question is: {query_str}\n"
)
# TODO: use mongodb to replace pickle for stored_docs
"""
stored_docs stores documents from both user's questions and the knowledge base.
it has a one to one mapping with the documents in the index.
the key is doc_id, in current version it is the question text itself;
the value is a tuple of 4 elements:
    doc_text: str,  which is the whole text of the document, typically contains question, answer, and category;
    from_knowledge_base: bool, which indicates whether the document is from knowledge base;
    insert_timestamp: float, which is the timestamp when the document is inserted;
    query_timestamps: List[float], which is a list of timestamps when the document is queried;
query_timestamps indicates the popularity of the document.
"""


def query_index(query_text) -> Dict[str, Any]:
    data_util.assert_not_none(query_text, "query cannot be none")
    logger.info(f"Query test: {query_text}")
    # first search locally
    with index_storage.r_index() as index:
        local_query_engine = index.as_query_engine(
            response_synthesizer=get_response_synthesizer(
                response_mode=ResponseMode.NO_TEXT
            ),
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=similarity_cutoff)],
        )
        local_query_response = local_query_engine.query(query_text)
    if len(local_query_response.source_nodes) > 0:
        text = local_query_response.source_nodes[0].text
        # TODO encapsulate the following text extractions to functions
        if 'answer": ' in text:
            matched_question = text.split('question": ')[1].split(",\n")[0].strip('"')
            matched_doc_id = data_util.get_doc_id(matched_question)
            with index_storage.rw_stored_docs() as stored_docs:
                finded_doc = stored_docs.find_doc(matched_doc_id)
                if finded_doc:
                    finded_doc["query_tss"].append(time.time())
                    from_knowledge_base =  finded_doc["from_knowledge_base"]
                else:
                    # means the document has been removed from stored_docs
                    logger.warning(f"'{matched_doc_id}' is not found in stored_docs")
                    data = {
                        "doc_text": text,
                        "from_knowledge_base": False,
                        "insert_ts": time.time(),
                        "query_tss": []
                    }
                    stored_docs.insert_doc(matched_doc_id, data)
                    from_knowledge_base = False
            answer_text = text.split('answer": ')[1].strip('"\n}')
            if 'category": ' in text:
                category = text.split('category": ')[1].split(",")[0].strip('"\n}')
                category = None if data_util.is_empty(category) else category
            else:
                category = None
            return {
                "category": category,
                "question": query_text,
                "matched_question": matched_question,
                "source": Source.KNOWLEDGE_BASE if from_knowledge_base else Source.USER_ASKED,
                "answer": answer_text,
            }
    # if not found, turn to LLM
    qa_template = Prompt(prompt_template_string)
    with index_storage.rw_index() as index:
        llm_query_engine = index.as_query_engine(text_qa_template=qa_template)
        response = llm_query_engine.query(query_text)
    answer_text = str(response)
    # save the question-answer pair to index
    question_answer_pair = f'"source": {Source.USER_ASKED}, "category": "", "question": {query_text}, "answer": {answer_text}'
    doc_id = data_util.get_doc_id(query_text)
    insert_text_into_index(question_answer_pair, doc_id)
    return {
        "category": None,
        "question": query_text,
        "source": index_storage.current_model,
        "answer": answer_text,
    }


def insert_text_into_index(text, doc_id):
    document = Document(text=text)
    insert_into_index(document, doc_id=doc_id)


def insert_file_into_index(doc_file_path, doc_id=None):
    document = SimpleDirectoryReader(input_files=[doc_file_path]).load_data()[0]
    insert_into_index(document, doc_id=doc_id)


def insert_into_index(document, doc_id=None):
    """Insert new document into global index."""
    index_storage.add_doc(document, doc_id)


def delete_doc(doc_id):
    data_util.assert_not_none(doc_id, "doc_id cannot be none")
    logger.info(f"Delete document with doc id: {doc_id}")
    index_storage.delete_doc(doc_id)


def get_document(doc_id):
    with index_storage.r_stored_docs() as stored_docs:
        result = stored_docs.find_doc(doc_id)
        if result:
            return {
                "doc_id": doc_id,
                "doc_text": result["doc_text"],
                "from_knowledge_base": result["from_knowledge_base"],
                "insert_time_display": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(result["insert_timestamp"])
                ),
                "query_times": len(result["query_tss"]),
            }
    return None


def main():
    # setup server
    manager = BaseManager(address=("localhost", 5602), authkey=b"password")
    manager.register("query_index", query_index)
    manager.register("insert_text_into_index", insert_text_into_index)
    manager.register("insert_file_into_index", insert_file_into_index)
    manager.register("get_document", get_document)
    manager.register("delete_doc", delete_doc)
    server = manager.get_server()

    logger.info("server started...")
    server.serve_forever()


if __name__ == "__main__":
    main()
