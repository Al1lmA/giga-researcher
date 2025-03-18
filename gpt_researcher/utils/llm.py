from __future__ import annotations
import json
from fastapi import WebSocket
from langchain.adapters import openai as lc_openai
from colorama import Fore, Style
from typing import Optional
import os
from langchain_community.vectorstores import FAISS

from gpt_researcher.master.prompts import auto_agent_instructions

from operator import itemgetter
from textwrap import dedent

from IPython.display import Markdown
from langchain_community.chat_models.gigachat import GigaChat
from langchain_community.retrievers.yandex_search import YandexSearchAPIRetriever
from langchain_community.utilities.yandex_search import YandexSearchAPIWrapper
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
from loguru import logger

from dotenv import load_dotenv
load_dotenv()

async def create_chat_completion(
        messages: list,  # type: ignore
        credentials= os.environ["GIGACHAT_CREDENTIALS"],
        scope= os.environ["GIGACHAT_SCOPE"], 
        profanity_check=False,
        verify_ssl_certs=False,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: Optional[int] = 512,
        llm_provider: Optional[str] = None,
        stream: Optional[bool] = False,
        websocket: WebSocket | None = None,
) -> str:

    if model is None:
        raise ValueError("Model cannot be None")
    if max_tokens is not None and max_tokens > 8001:
        raise ValueError(f"Max tokens cannot be more than 8001, but got {max_tokens}")

    # create response
    for attempt in range(10):  # maximum of 10 attempts
        response = await send_chat_completion_request(
            messages, model,  max_tokens, stream, llm_provider, websocket #temperature,
        )
        return response

    logger.error("Failed to get response from API")
    raise RuntimeError("Failed to get response from API")




async def send_chat_completion_request(
        messages, model,  max_tokens, stream, llm_provider, websocket #temperature,
):
    if not stream:
        result = lc_openai.ChatCompletion.create(
            credentials= os.environ["GIGACHAT_CREDENTIALS"],
            scope= os.environ["GIGACHAT_SCOPE"], 
            profanity_check=False,
            verify_ssl_certs=False,
            model=model,  # Change model here to use different models
            messages=messages,
            temperature=0.7,
            max_tokens=max_tokens,
            provider=llm_provider,  # Change provider here to use a different API
        )
        return result["choices"][0]["message"]["content"]
    else:
        return await stream_response(model, messages,  max_tokens, llm_provider, websocket) #temperature,


async def stream_response(model, messages,  max_tokens, llm_provider, websocket=None): #temperature,
    paragraph = ""
    response = ""

    for chunk in lc_openai.ChatCompletion.create(
            credentials= os.environ["GIGACHAT_CREDENTIALS"],
            scope= os.environ["GIGACHAT_SCOPE"], 
            profanity_check=False,
            verify_ssl_certs=False,
            model=model,
            messages=messages,
            # temperature=temperature,
            max_tokens=max_tokens,
            provider=llm_provider,
            stream=True,
    ):
        content = chunk["choices"][0].get("delta", {}).get("content")
        if content is not None:
            response += content
            paragraph += content
            if "\n" in paragraph:
                if websocket is not None:
                    await websocket.send_json({"type": "report", "output": paragraph})
                else:
                    logger.error(f"{paragraph}")
                paragraph = ""
    return response

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

async def qa_rag_giga(model, qa_template):
    model = GigaChat(
    credentials= os.environ["GIGACHAT_CREDENTIALS"],
    scope= os.environ["GIGACHAT_SCOPE"], 
    profanity_check=False,
    verify_ssl_certs=False,
    model=model
    )
    api_wrapper = YandexSearchAPIWrapper()
    retriever = YandexSearchAPIRetriever(api_wrapper=api_wrapper, k=30)

    QA_TEMPLATE = """Пожалуйста, предоставь ответ на вопрос, в заданном формате. Убедись, что ответ КРАТКИЙ и точный. 
        Если информация отсутствует, укажи n/a.

        Примеры:

        **Пример 1:**
        - Вопрос: Какой номер телефона у компании Ромашка?
        - Текст: Компания Ромашка создана в 2000 г. Компании находится по адресу ул. Беговая д. 15. Контакты компании - +7(999)999 99 99, comp@company.ru, www.company.com
        - Ответ: +7(999)999 99 99

        **Пример 2:**
        - Вопрос: Email компании Ромашка
        - Текст: Компания Ромашка создана в 2000 г. Компании находится по адресу ул. Беговая д. 15. Контакты компании - +7(999)999 99 99, comp@company.ru, www.company.com
        - Ответ: comp@company.ru

        **Пример 3:**
        - Вопрос: Численность сотрудников Вкусвилл?
        - Текст: ВкусВилл отмечает 10-летие со дня открытия первых четырёх магазинов продуктов для здорового питания. В честь юбилея вышла книга ценностей бренда, написанная сотрудниками для сотрудников. В магазинах ВкусВилл более 97% товаров представлено под собственной торговой маркой. Компания тщательно выбирает производителей продуктов, проводит проверки качества и безопасности в лицензированной микробиологической лаборатории. В магазинах ВкусВилл представлено более 7700 товарных позиций, в доле продаж лидирует кулинария, ФРОВ (Фрукты-Овощи) и молочная продукция. В компании работает около 30 тысяч сотрудников.
        - Ответ: 30 000

        **Пример 4:**
        - Вопрос: Какие ключевые технологии применяют в компании Ромашка?
        - Текст: Мы начали несколько лет назад переходить на open source, учиться. В интеграционном слое мы используем такие решения как Kafka, ZeroMQ. В качестве BPM-решения мы используем open-source решение Activiti. Мы используем WildFly в качестве сервера приложений.
        - Ответ: Kafka, ZeroMQ, Activiti, WildFly

        Вопрос: {question} 
        Текст: {context}
        
    """
    prompt = ChatPromptTemplate.from_template(QA_TEMPLATE)

    output_parser = StrOutputParser()

    chain_without_source = (
        RunnableParallel(
            {
                "context": itemgetter("context") | RunnableLambda(format_docs),
                "question": itemgetter("question"),
            }
        )
        | prompt
        | model
        | output_parser
    )
    chain_with_source = RunnableParallel(
        {
            "context": itemgetter("question") | retriever,
            "question": itemgetter("question"),
        }
    ).assign(answer=chain_without_source)

    return chain_with_source