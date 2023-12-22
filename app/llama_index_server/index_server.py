import json
from llama_index import (
    Document,
    Prompt,
    SimpleDirectoryReader,
)
from llama_index.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.indices.postprocessor import SimilarityPostprocessor
from app.data.models import qa
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
        doc_text = local_query_response.source_nodes[0].text
        if qa.has_answer(doc_text):
            logger.debug(f"Found matched answer from index: {doc_text}")
            matched_meta = json.loads(doc_text)
            matched_question = matched_meta["question"]
            matched_doc_id = data_util.get_doc_id(matched_question)
            with index_storage.rw_mongo() as mongo:
                doc_meta = mongo.find_one("doc_id", matched_doc_id)
                doc_meta = LlamaIndexDocumentMeta(**doc_meta) if doc_meta else None
                current_timestamp = data_util.get_current_milliseconds()
                if doc_meta:
                    logger.debug(f"Found doc meta from mongodb: {doc_meta}")
                    doc_meta.query_timestamps.append(current_timestamp)
                    mongo.upsert_one("doc_id", matched_doc_id, doc_meta)
                    from_knowledge_base = doc_meta.from_knowledge_base
                else:
                    # means the document meta has been removed from mongodb. for example by pruning
                    logger.warning(f"'{matched_doc_id}' is not found in mongodb")
                    doc_meta = LlamaIndexDocumentMeta(
                        doc_id=matched_doc_id,
                        doc_text=doc_text,
                        from_knowledge_base=False,
                        insert_timestamp=current_timestamp,
                        query_timestamps=[current_timestamp],
                    )
                    mongo.upsert_one("doc_id", matched_doc_id, doc_meta)
                    from_knowledge_base = False
            answer_text = qa.extract_answer(doc_text)
            category = qa.extract_category(doc_text)
            return Answer(
                category=category,
                question=query_text,
                matched_question=matched_question,
                source=Source.KNOWLEDGE_BASE if from_knowledge_base else Source.USER_ASKED,
                answer=answer_text,
            )
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
    doc_text = answer.model_dump_json()
    doc_id = data_util.get_doc_id(query_text)
    insert_text_into_index(doc_text, doc_id)
    return answer


def insert_text_into_index(text, doc_id):
    document = Document(text=text)
    insert_into_index(document, doc_id=doc_id)


def insert_file_into_index(doc_file_path, doc_id=None):
    document = SimpleDirectoryReader(input_files=[doc_file_path]).load_data()[0]
    insert_into_index(document, doc_id=doc_id)


def insert_into_index(document, doc_id=None):
    index_storage.add_doc(document, doc_id)


def delete_doc(doc_id):
    data_util.assert_not_none(doc_id, "doc_id cannot be none")
    logger.info(f"Delete document with doc id: {doc_id}")
    index_storage.delete_doc("doc_id", doc_id)


def get_document(doc_id):
    with index_storage.r_mongo() as mongo:
        doc_meta = mongo.find_one("doc_id", doc_id)
        if doc_meta:
            readable = LlamaIndexDocumentMetaReadable(
                doc_id=doc_meta["doc_id"],
                doc_text=doc_meta["doc_text"],
                from_knowledge_base=doc_meta["from_knowledge_base"],
                insert_timestamp=doc_meta["insert_timestamp"],
                query_timestamps=doc_meta["query_timestamps"],
            )
            return readable
    return None


def cleanup_for_test():
    with index_storage.rw_mongo() as mongo:
        return mongo.cleanup_for_test()
