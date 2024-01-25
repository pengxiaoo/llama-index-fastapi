from typing import Union
from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from llama_index import Prompt
from llama_index.prompts import ChatPromptTemplate
from llama_index.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.indices.postprocessor import SimilarityPostprocessor
from llama_index.llms.base import ChatMessage
from llama_index.chat_engine.types import ChatMode
from llama_index.core.llms.types import MessageRole
from app.data.models.qa import Source, Answer, get_default_answer_id, get_default_answer
from app.data.models.mongodb import (
    LlamaIndexDocumentMeta,
    LlamaIndexDocumentMetaReadable,
    Message,
)
from app.llama_index_server.chat_message_dao import ChatMessageDao
from app.data.messages.qa import DocumentRequest
from app.utils.log_util import logger
from app.utils import data_util
from app.llama_index_server.index_storage import index_storage, chat_engine

SIMILARITY_CUTOFF = 0.85
QUERY_PROMPT_TEMPLATE = (
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
chat_message_dao = ChatMessageDao()


def get_local_query_engine():
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


def get_llm_query_engine():
    index = index_storage.index()
    qa_template = Prompt(QUERY_PROMPT_TEMPLATE)
    return index.as_query_engine(text_qa_template=qa_template)


def query_index(query_text, only_for_meta=False) -> Union[Answer, LlamaIndexDocumentMeta, None]:
    data_util.assert_not_none(query_text, "query cannot be none")
    logger.info(f"Query test: {query_text}")
    # first search locally
    matched_question = get_matched_question_from_local_query_engine(query_text)
    if matched_question:
        matched_doc_id = data_util.get_doc_id(matched_question)
        mongo = index_storage.mongo()
        doc_meta = mongo.find_one({"doc_id": matched_doc_id})
        doc_meta = LlamaIndexDocumentMeta(**doc_meta) if doc_meta else None
        if doc_meta:
            logger.debug(f"Found doc meta from mongodb: {doc_meta}")
            doc_meta.query_timestamps.append(data_util.get_current_milliseconds())
            mongo.upsert_one({"doc_id": matched_doc_id}, doc_meta)
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


def chat(content: str, conversation_id: str) -> Message:
    data_util.assert_not_none(content, "message content cannot be none")
    user_message = ChatMessage(role=MessageRole.USER, content=content)
    # save immediately, since the following steps may take a while and throw exceptions
    chat_message_dao.save_chat_history(conversation_id, user_message)
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                "If the question has nothing to do with golf at all, please answer "
                f"'{get_default_answer_id()}'.\n"
            ),
        ),
        ChatMessage(
            role=MessageRole.USER,
            content=(
                "Context information is below.\n"
                "---------------------\n"
                "{context_str}\n"
                "---------------------\n"
                "Given the context information and not prior knowledge, "
                "answer the question: {query_str}\n"
            ),
        ),
    ]
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)
    # text_qa_template = Prompt(PROMPT_TEMPLATE_STR)
    engine_kwargs = {
        "text_qa_template": text_qa_template,
        "chat_mode": ChatMode.CONDENSE_QUESTION,
    }
    engine, newly_created = chat_engine.get(conversation_id, engine_kwargs)
    logger.info(f"conversation_id: {conversation_id}, engine is new: {newly_created}, message content: {content}")
    if newly_created:
        chat_response = engine.chat(content)
        history = []
    else:
        history = chat_message_dao.get_chat_history(conversation_id)
        chat_messages = [ChatMessage(role=c.role, content=c.content) for c in history]
        logger.info(f"Creating Chat history, size: {len(chat_messages)}")
        chat_response = engine.chat(content, chat_history=chat_messages)
    # todo: the chat_response failed to utilize the local database, need further investigation
    logger.debug(f"Chat response: {chat_response.response}")
    if chat_response.response == get_default_answer_id():
        logger.debug("Irrelevant question, use OpenAI")
        client = OpenAI()
        chat_messages = [dict(role=c.role, content=c.content) for c in history]
        chat_messages += [
            dict(
                role=MessageRole.SYSTEM,
                content=(
                    "assume you are an experienced golf coach, if the question has anything to do with golf, "
                    "please give short, simple, accurate, precise answer to the question, "
                    "limited to 80 words maximum. If the question has nothing to do with golf at all, please answer "
                    f"'{get_default_answer()}'."
                )
            )
        ]
        completion = client.chat.completions.create(
            model=index_storage.current_model,
            messages=chat_messages,
            temperature=0,
        )
        mes = completion.choices[0].message.content
        content = mes or get_default_answer()
    else:
        content = chat_response.response
    bot_message = ChatMessage(role=MessageRole.ASSISTANT, content=content)
    chat_message_dao.save_chat_history(conversation_id, bot_message)
    return Message.from_chat_message(conversation_id, bot_message)


async def stream_chat(content: str, conversation_id: str):
    # todo: need to use chat engine based on index. otherwise, the local database is not utilized
    # We only support using OpenAI's API
    client = OpenAI()
    user_message = ChatMessage(role=MessageRole.USER, content=content)
    chat_message_dao.save_chat_history(conversation_id, user_message)
    history = chat_message_dao.get_chat_history(conversation_id)
    messages = [ChatCompletionMessageParam(content=c.content, role=c.role) for c in history]
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
            bot_message = ChatMessage(role=MessageRole.ASSISTANT, content=content)
            chat_message_dao.save_chat_history(conversation_id, bot_message)
            break
        if content is None:
            break
        chunks.append(content)
        logger.debug("Chunk message: %s", content)
        yield content
