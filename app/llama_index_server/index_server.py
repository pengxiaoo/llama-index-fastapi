from typing import Union
from llama_index import Prompt
from llama_index.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.indices.postprocessor import SimilarityPostprocessor
from llama_index.llms.base import ChatMessage
from llama_index.agent import OpenAIAgent
from llama_index.llms import OpenAI
from llama_index.core.llms.types import MessageRole
from app.data.messages.qa import DocumentRequest
from app.data.models.qa import Source, Answer, get_default_answer_id, get_default_answer
from app.data.models.mongodb import (
    LlamaIndexDocumentMeta,
    LlamaIndexDocumentMetaReadable,
    Message,
)
from app.utils.log_util import logger
from app.utils import data_util
from app.llama_index_server.chat_message_dao import ChatMessageDao
from app.llama_index_server.index_storage import index_storage
from app.llama_index_server.my_query_engine_tool import MyQueryEngineTool, MATCHED_MARK

SIMILARITY_CUTOFF = 0.85
PROMPT_TEMPLATE_FOR_QUERY_ENGINE = (
    "We have provided context information below. \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "Given this information, assume you are an experienced golf coach, if the question has anything to do with golf, "
    "please give short, simple, accurate, precise answer to the question, "
    "limited to 80 words maximum. If the question has nothing to do with golf at all, please answer "
    f"'{get_default_answer_id()}'.\n"
    "The question is: {query_str}\n"
)
SYSTEM_PROMPT_TEMPLATE_FOR_CHAT_ENGINE = (
    "Your are an expert Q&A system that can find relevant information using the tools at your disposal.\n"
    "The tools can access a set of typical questions a golf beginner might ask.\n"
    "If the user's query matches one of those typical questions, stop and return the matched question immediately.\n"
    "If the user's query doesn't match any of those typical questions, "
    "then you should act as an experienced golf coach, and firstly evaluate whether the question is relevant to golf.\n"
    f"if it is not golf relevant at all, please answer '{get_default_answer_id()},"
    "otherwise, please give short, simple, accurate, precise answer to the question, limited to 80 words maximum.\n"
    "You may need to combine the chat history to fully understand the query of the user.\n"
)
chat_message_dao = ChatMessageDao()


def get_local_query_engine():
    """
    strictly limited to local knowledge base. our local knowledge base is a list of standard questions which are indexed in vector store,
    while the standard answers are stored in mongodb through DocumentMetaDao.
    there is a one-to-one mapping between each standard question and a standard answer.
    we may update or optimize the standard answers in mongodb frequently, but usually we don't update the standard questions.
    if a query matches one of the standard questions, we can find the respective standard answer from mongodb.
    """
    index = index_storage.index()
    return index.as_query_engine(
        response_synthesizer=get_response_synthesizer(
            response_mode=ResponseMode.NO_TEXT
        ),
        node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)],
    )


def get_matched_question_from_local_query_engine(query_text):
    local_query_engine = get_local_query_engine()
    local_query_response = local_query_engine.query(query_text)
    if len(local_query_response.source_nodes) > 0:
        matched_node = local_query_response.source_nodes[0]
        matched_question = matched_node.text
        logger.debug(f"Found matched question from index: {matched_question}")
        return matched_question
    else:
        return None


def get_doc_meta(text):
    matched_doc_id = data_util.get_doc_id(text)
    mongo = index_storage.mongo()
    doc_meta = mongo.find_one({"doc_id": matched_doc_id})
    doc_meta = LlamaIndexDocumentMeta(**doc_meta) if doc_meta else None
    return matched_doc_id, doc_meta


def get_llm_query_engine():
    index = index_storage.index()
    qa_template = Prompt(PROMPT_TEMPLATE_FOR_QUERY_ENGINE)
    return index.as_query_engine(text_qa_template=qa_template)


def query_index(query_text, only_for_meta=False) -> Union[Answer, LlamaIndexDocumentMeta, None]:
    data_util.assert_not_none(query_text, "query cannot be none")
    logger.info(f"Query test: {query_text}")
    # first search locally
    matched_question = get_matched_question_from_local_query_engine(query_text)
    if matched_question:
        matched_doc_id, doc_meta = get_doc_meta(matched_question)
        if doc_meta:
            logger.debug(f"An matched doc meta found from mongodb: {doc_meta}")
            doc_meta.query_timestamps.append(data_util.get_current_milliseconds())
            index_storage.mongo().upsert_one({"doc_id": matched_doc_id}, doc_meta)
            if only_for_meta:
                return doc_meta
            else:
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
            if only_for_meta:
                return None
    # if not found, turn to LLM
    llm_query_engine = get_llm_query_engine()
    response = llm_query_engine.query(query_text)
    # save the question-answer pair to index
    answer = Answer(
        category=None,
        question=query_text,
        source=index_storage.current_model,
        answer=str(response),
    )
    index_storage.add_doc(answer)
    return answer


def delete_doc(doc_id):
    data_util.assert_not_none(doc_id, "doc_id cannot be none")
    logger.info(f"Delete document with doc id: {doc_id}")
    return index_storage.delete_doc(doc_id)


def get_document(req: DocumentRequest):
    doc_meta = index_storage.mongo().find_one({"doc_id": req.doc_id})
    if doc_meta:
        return LlamaIndexDocumentMetaReadable(**doc_meta)
    elif req.fuzzy:
        doc_meta = query_index(req.doc_id, only_for_meta=True)
        if doc_meta:
            doc_meta.matched_question = doc_meta.question
            doc_meta.question = doc_meta.doc_id = req.doc_id
            return LlamaIndexDocumentMetaReadable(**doc_meta.model_dump())
        return None


def cleanup_for_test():
    return index_storage.mongo().cleanup_for_test()


# todo: use cache?
def get_chat_engine(conversation_id: str, streaming: bool = False):
    local_query_engine = get_local_query_engine()
    query_engine_tools = [
        MyQueryEngineTool.from_defaults(
            query_engine=local_query_engine,
            name="local_query_engine",
            description="Queries from a knowledge base consists of typical questions that a golf beginner might ask",
        )
    ]
    chat_llm = OpenAI(
        temperature=0,
        model=index_storage.current_model,
        streaming=streaming,
        max_tokens=100,
    )
    chat_history = chat_message_dao.get_chat_history(conversation_id)
    chat_history = [ChatMessage(role=c.role, content=c.content) for c in chat_history]
    # todo: when the tool find a matched question, should return directly, without further querying from openai
    return OpenAIAgent.from_tools(
        tools=query_engine_tools,
        llm=chat_llm,
        chat_history=chat_history,
        verbose=True,
        system_prompt=SYSTEM_PROMPT_TEMPLATE_FOR_CHAT_ENGINE,
    )


def get_response_text_from_chat(agent_chat_response):
    sources = agent_chat_response.sources
    if len(sources) > 0:
        source_content = sources[0].content
        if MATCHED_MARK in source_content:
            return source_content.replace(MATCHED_MARK, "").strip()
    return agent_chat_response.response


def chat(query_text: str, conversation_id: str) -> Message:
    # we will not index chat messages in vector store, but will save them in mongodb
    data_util.assert_not_none(query_text, "query content cannot be none")
    user_message = ChatMessage(role=MessageRole.USER, content=query_text)
    # save immediately, since the following steps may take a while and throw exceptions
    chat_message_dao.save_chat_history(conversation_id, user_message)
    chat_engine = get_chat_engine(conversation_id)
    agent_chat_response = chat_engine.chat(query_text)
    response_text = get_response_text_from_chat(agent_chat_response)
    # todo: change the if condition to: response_text == get_default_answer_id()
    response_text = get_default_answer() if get_default_answer_id() in response_text else response_text
    matched_doc_id, doc_meta = get_doc_meta(response_text)
    if doc_meta:
        logger.debug(f"An matched doc meta found from mongodb: {doc_meta}")
        doc_meta.query_timestamps.append(data_util.get_current_milliseconds())
        index_storage.mongo().upsert_one({"doc_id": matched_doc_id}, doc_meta)
        bot_message = ChatMessage(role=MessageRole.ASSISTANT, content=doc_meta.answer)
    else:
        # means the chat engine cannot find a matched doc meta from mongodb
        logger.warning(f"'{matched_doc_id}' is not found in mongodb")
        bot_message = ChatMessage(role=MessageRole.ASSISTANT, content=response_text)
    chat_message_dao.save_chat_history(conversation_id, bot_message)
    return Message.from_chat_message(conversation_id, bot_message)


async def stream_chat(content: str, conversation_id: str):
    # todo: need to use chat engine based on index. otherwise, the local database is not utilized
    # We only support using OpenAI's API
    client = OpenAI()
    user_message = ChatMessage(role=MessageRole.USER, content=content)
    chat_message_dao.save_chat_history(conversation_id, user_message)
    history = chat_message_dao.get_chat_history(conversation_id)
    messages = [dict(content=c.content, role=c.role) for c in history]
    messages = [
                   dict(
                       role=MessageRole.SYSTEM,
                       content=(
                           "assume you are an experienced golf coach, if the question has anything to do with golf, "
                           "please give short, simple, accurate, precise answer to the question, "
                           "limited to 80 words maximum. If the question has nothing to do with golf at all, please answer "
                           f"'{get_default_answer()}'."
                       )
                   ),
               ] + messages
    completion = client.chat.completions.create(
        model=index_storage.current_model,
        messages=messages,
        temperature=0,
        stream=True  # again, we set stream=True
    )
    chunks = []
    for chunk in completion:
        finish_reason = chunk.choices[0].finish_reason
        content = chunk.choices[0].delta.content
        if finish_reason == "stop" or finish_reason == "length":
            # reached the end
            if content is not None:
                bot_message = ChatMessage(role=MessageRole.ASSISTANT, content=content)
                chat_message_dao.save_chat_history(conversation_id, bot_message)
            break
        if content is None:
            break
        chunks.append(content)
        logger.debug("Chunk message: %s", content)
        yield content
