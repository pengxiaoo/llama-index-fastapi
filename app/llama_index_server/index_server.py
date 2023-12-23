from llama_index import Prompt
from llama_index.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.indices.postprocessor import SimilarityPostprocessor
from app.data.models.qa import Source, Answer, get_default_answer_id
from app.data.models.mongodb import (
    LlamaIndexDocumentMeta,
    LlamaIndexDocumentMetaReadable,
)
from app.utils.log_util import logger
from app.utils import data_util
from app.llama_index_server.index_storage import index_storage

SIMILARITY_CUTOFF = 0.85
PROMPT_TEMPLATE_STR = (
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


def query_index(query_text) -> Answer:
    data_util.assert_not_none(query_text, "query cannot be none")
    logger.info(f"Query test: {query_text}")
    # first search locally
    with index_storage.r_index() as index:
        local_query_engine = index.as_query_engine(
            response_synthesizer=get_response_synthesizer(
                response_mode=ResponseMode.NO_TEXT
            ),
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)],
        )
        local_query_response = local_query_engine.query(query_text)
    if len(local_query_response.source_nodes) > 0:
        matched_node = local_query_response.source_nodes[0]
        matched_question = matched_node.text
        logger.debug(f"Found matched question from index: {matched_question}")
        matched_doc_id = data_util.get_doc_id(matched_question)
        with index_storage.rw_mongo() as mongo:
            doc_meta = mongo.find_one({"doc_id": matched_doc_id})
            doc_meta = LlamaIndexDocumentMeta(**doc_meta) if doc_meta else None
            current_timestamp = data_util.get_current_milliseconds()
            if doc_meta:
                logger.debug(f"Found doc meta from mongodb: {doc_meta}")
                doc_meta.query_timestamps.append(current_timestamp)
                mongo.upsert_one({"doc_id": matched_doc_id}, doc_meta)
                return Answer(
                    category=doc_meta.category,
                    question=query_text,
                    matched_question=matched_question,
                    source=Source.KNOWLEDGE_BASE if doc_meta.source == Source.KNOWLEDGE_BASE else Source.USER_ASKED,
                    answer=doc_meta.answer,
                )
            else:
                # means the document meta has been removed from mongodb. for example by pruning
                logger.warning(f"'{matched_doc_id}' is not found in mongodb")
    # if not found, turn to LLM
    qa_template = Prompt(PROMPT_TEMPLATE_STR)
    with index_storage.r_index() as index:
        llm_query_engine = index.as_query_engine(text_qa_template=qa_template)
        response = llm_query_engine.query(query_text)
    answer_text = str(response)
    # save the question-answer pair to index
    answer = Answer(
        category=None,
        question=query_text,
        source=index_storage.current_model,
        answer=answer_text,
    )
    index_storage.add_doc(answer)
    return answer


def delete_doc(doc_id):
    data_util.assert_not_none(doc_id, "doc_id cannot be none")
    logger.info(f"Delete document with doc id: {doc_id}")
    index_storage.delete_doc("doc_id", doc_id)


def get_document(doc_id):
    with index_storage.r_mongo() as mongo:
        doc_meta = mongo.find_one({"doc_id": doc_id})
        if doc_meta:
            return LlamaIndexDocumentMetaReadable(**doc_meta)
    return None


def cleanup_for_test():
    with index_storage.rw_mongo() as mongo:
        return mongo.cleanup_for_test()
