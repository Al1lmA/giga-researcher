from operator import itemgetter
from gpt_researcher.master.functions import *
from langchain_community.chat_models.gigachat import GigaChat
from langchain_community.retrievers.yandex_search import YandexSearchAPIRetriever
from langchain_community.utilities.yandex_search import YandexSearchAPIWrapper
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
import asyncio
import json
from datetime import datetime
from typing import List, Dict
from fastapi import WebSocket
from loguru import logger
from gpt_researcher.master.agent import GPTResearcher
from backend.utils import convert_pptx_to_pdf
from modules.mr.mr_report import make_mr_pptx
from modules.mr.mr_report_image import make_mr_images_pptx
import locale
import requests
from io import BytesIO
from base64 import b64encode, b64decode
from time import sleep
from bs4 import BeautifulSoup
import time

from modules.mr.mr_sources import make_sources_file

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs", "mr")

locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))


async def update_progress(websocket: WebSocket, current_step: int, total_steps: int):
    progress_percentage = int(current_step / total_steps * 100)
    await websocket.send_json({"type": "progress", "output": progress_percentage})


def generate_headings_prompt(topic, num_headings=5):
	""" Генерирует запрос для нейросети на создание подзаголовков по заданной теме.
	Аргументы:
		topic (str): Тема, по которой генерируются подзаголовки.
		num_headings (int): Количество подзаголовков для генерации.
	Возвращает:
		str: Запрос для нейросети.
	"""

	return (f'Напишите {num_headings} подзаголовков для отчета по теме: "{topic}". '
			f'Каждый подзаголовок должен отражать ключевые аспекты темы и быть структурированным. Если в теме есть название, подзаголовки ДОЛЖНЫ включать его.'
            f'НЕ пиши подзаголовок "Заключение" или "Введение"'
			f'Используйте текущую дату, если это необходимо: {datetime.now().strftime("%d %B %Y")}.\n'
			f'Ответьте списком строк в следующем формате: ["подзаголовок 1", "подзаголовок 2", "подзаголовок 3"].')

async def get_headings(query, agent_role_prompt, cfg):
	"""
	"""
	max_research_iterations = cfg.max_iterations if cfg.max_iterations else 1
	response = await create_chat_completion(
		model=cfg.smart_llm_model,
		messages=[
			{"role": "system", "content": f"{agent_role_prompt}"},
			{"role": "user", "content": generate_headings_prompt(query, num_headings=max_research_iterations)}],
		temperature=0.5,
		llm_provider=cfg.llm_provider,
		profanity_check=False,
		verify_ssl_certs=False,
		max_tokens=cfg.smart_token_limit,
	)
	headings = json.loads(response)
	return headings

def format_docs(docs):
	return "\n\n".join([doc.page_content for doc in docs])



def log_step(step_name: str):
    def wrapper(x):
        logger.info(f"[STEP: {step_name}] START")
        start = time.time()
        result = x
        duration = time.time() - start
        logger.info(f"[STEP: {step_name}] END — took {duration:.2f}s")
        return result
    return RunnableLambda(wrapper)

async def chain_with_source():
    model = GigaChat(
model="GigaChat-2-Pro",
	# model="GigaChat-Plus",
    # model="GigaChat-2-Max",
	verify_ssl_certs=False,
	profanity_check=False,
      
    #request_timeout=60
    )
    api_wrapper = YandexSearchAPIWrapper()
    retriever = YandexSearchAPIRetriever(api_wrapper=api_wrapper, k=30)

    QA_TEMPLATE = """Напишите подробный отчет по теме: "{question}". 
                Отчет должен быть сосредоточен на теме, хорошо структурирован, информативен, глубок и всеобъемлющ, с фактами и цифрами, если они доступны.

                Вы должны стремиться написать отчет как можно длиннее, используя всю соответствующую и необходимую предоставленную информацию. Избегайте общих фраз и неясных выводов. 
                Пишите на чем основывается вывод. Пишите как можно больше конкретной информации.
                Например если отчет о продуктах компании - пишите название продуктов.

                Используйте беспристрастный и журналистский тон. 

                ВЫ ДОЛЖНЫ определить свое собственное конкретное и обоснованное мнение на основе предоставленной информации. Старайтесь быть критичным.
                НЕ ОТКЛОНЯЙТЕСЬ к общим и бессмысленным выводам.


                Цитируйте результаты поиска с помощью встроенных обозначений. Цитируйте только наиболее актуальные результаты, которые точно отвечают на запрос. 
                Поместите эти цитаты в конце предложения или абзаца, которые на них ссылаются.


                Пожалуйста, предоставьте только содержание отчета без дополнительных описаний или комментариев.
                
                Тема: "{question}"
                Информация: {context}
                """

    prompt = ChatPromptTemplate.from_template(QA_TEMPLATE)

    output_parser = StrOutputParser()
    '''
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
    '''
    chain_without_source = (
        RunnableParallel(
            {
                "context": itemgetter("context") | RunnableLambda(format_docs) | log_step("formatted_context"),
                "question": itemgetter("question") | log_step("question_passed"),
            }
        )
        | log_step("prompt_building")
        | prompt
        | log_step("prompt_rendered")
        | model
        | log_step("model_output")
        | output_parser
    )
    chain_with_source = (
        RunnableParallel(
            {
                "context": itemgetter("question") | log_step("retrieving_context") | retriever | log_step("retrieved_docs"),
                "question": itemgetter("question") | log_step("raw_question"),
            }
        ).assign(answer=chain_without_source)
    )
    return chain_with_source

# def get_image(task, image_list):
# 	follderid = os.getenv('YANDEX_FOLDER_ID')
# 	apikey = os.getenv('YANDEX_API_KEY')

# 	url = f'https://yandex.ru/images-xml?folderid={follderid}&apikey={apikey}&text={task}&itype=jpg&iorient=horizontal&isize=medium&icolor=color'

# 	resp = requests.get(url=url, verify=False)
# 	soup = BeautifulSoup(resp.text, 'xml')
# 	error_list = []
# 	# Извлечение всех элементов <doc> из XML
# 	for doc in soup.find_all('doc'):
# 		href = doc.find('url').get_text() if doc.find('url') else ''
# 		try:
# 			sleep(1)
# 			# if href and href not in image_list:
# 			if href and href not in image_list and href not in error_list:
# 				response = requests.get(href, verify=False)
# 				if response.status_code == 200:
# 					image_stream = BytesIO(response.content)
# 					# Кодируем изображение в base64
# 					image_data = b64encode(image_stream.getvalue()).decode('utf-8')
# 					return image_data, href
# 				else:
# 					logger.error(f'ERROR- {response.status_code} - {href}')
# 					error_list.append(href)		
# 		except Exception as er:
# 			logger.error(er)

def get_image(task, image_list):
    folder_id = os.getenv('YANDEX_FOLDER_ID')
    api_key = os.getenv('YANDEX_API_KEY')
    
    if not folder_id or not api_key:
        logger.error("YANDEX_FOLDER_ID или YANDEX_API_KEY не заданы в переменных окружения")
        return None, None

    url = "https://searchapi.api.cloud.yandex.net/v2/image/search"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "folderId": folder_id,
        "query": {
             "searchType": "SEARCH_TYPE_COM",
             "queryText": task,
        },
        "imageSpec": {
            "format": "IMAGE_FORMAT_JPEG",
            "orientation": "IMAGE_ORIENTATION_HORIZONTAL",
            "size": "IMAGE_SIZE_MEDIUM",
            "color": "IMAGE_COLOR_COLOR"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Yandex API request failed: {e}; response: {getattr(e, 'response', None)}")
        return None, None
    
    try:
        data = response.json()
        raw_xml_b64 = data.get("rawData")
        if not raw_xml_b64:
            logger.warning("Ответ не содержит rawData")
            return None, None
        raw_xml = b64decode(raw_xml_b64).decode("utf-8")
    except Exception as e:
        logger.error(f"Ошибка при декодировании XML: {e}")
        return None, None

    # парсим XML
    soup = BeautifulSoup(raw_xml, "xml")
    docs = soup.find_all("doc")
    error_list = []

    if not docs:
        logger.warning("Yandex Search API не вернул результатов для запроса")
        logger.debug(f"XML: {raw_xml}")
        return None, None

    for doc in docs:
        href = doc.find("url").get_text() if doc.find("url") else None
        if not href or href in image_list or href in error_list:
            continue
        try:
            sleep(1)
            img_resp = requests.get(
                href,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/117.0.0.0 Safari/537.36",
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                    "Referer": "https://yandex.ru/",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
                }
            )
            if img_resp.status_code == 200 and "image" in img_resp.headers.get("Content-Type", ""):
                image_stream = BytesIO(img_resp.content)
                image_data = b64encode(image_stream.getvalue()).decode('utf-8')
                return image_data, href
            else:
                logger.error(f"Bad response {img_resp.status_code} - {href}")
                error_list.append(href)
        except Exception as er:
            logger.error(f"Ошибка скачивания {href}: {er}")
            error_list.append(href)

    return None, None

                 
async def mr_report(websocket: WebSocket, task: str, image=False): # 
    # await websocket.send_json({"type": "logs", "output": f"\nMR REPORT  {task}\n\n"})

    total_steps = 13 #Количество шагов (блоков)
    current_step = 0
    researcher = GPTResearcher(config_path=None,  websocket=websocket) #
    #researcher = GPTResearcher(source_urls=None, config_path=None,  websocket=websocket) #
    context = []
    sources = []
    image_list = []
    researcher.query = task
    researcher.cfg.max_iterations = 10 #Количество блоков/разделов
    logger.info(f"Generated researcher")
    chain = await chain_with_source()
    logger.info(f"Generated chain")

    # Формируем разделы/подзаголовки
    agent, role = await choose_agent(researcher.query, researcher.cfg)
    logger.info(f"Generated agent, role")
    await asyncio.sleep(0.1)
    sub_queries = await get_headings(researcher.query, role, researcher.cfg)
    logger.info(f"Разделы для поиска - {sub_queries}")

    for question in sub_queries:
        await websocket.send_json({"type": "logs", "output": f"Поиск информации по теме '{question}'"})
        try:
            logger.info(f"[CHAIN] invoke started for question: {question}")
            # response = await chain.invoke({"question": question})
            try:
                logger.info("Invoking chain...")
                response = await asyncio.wait_for(
                    asyncio.to_thread(chain.invoke, {"question": question}),
                    timeout=120
                )
            except asyncio.TimeoutError:
                logger.error("Timeout while waiting for GigaChat response")
                response = {
                    "question": question,
                    "answer": "⚠️ Ответ от модели не получен — превышено время ожидания.",
                    "context": []
                }
            logger.info("[CHAIN] response received")

            if image:
                  image, url = get_image(task=question, image_list=image_list)
                  image_list.append(url)
                  context.append({response["question"]:[response["answer"], image, url]})
            else:
                context.append({response["question"]:response["answer"]})
            # источники
            sources.extend([{response["question"]:[{f"{doc.page_content}": f'{doc.metadata["url"]}'} for doc in response["context"] ]}])
            await websocket.send_json({"type": "report", "output": response["answer"]})
            logger.info(f"send_json")
        except Exception as er:
             logger.error(er)
        current_step += 1
        await update_progress(websocket, current_step, total_steps)
        await asyncio.sleep(0.1)


    # Формирование презентации 
    try:
        if image:
              pptx_path  = await make_mr_images_pptx(task, qna_list=context)
        else:
            pptx_path  = await make_mr_pptx(task, qna_list=context)
    except Exception as er:
        logger.error(er)

    current_step += 1
    await update_progress(websocket, current_step, total_steps)
    
    try:
        pdf_path = await convert_pptx_to_pdf(pptx_path, OUTPUTS_DIR)
    except Exception as er:
        logger.error(er) 
    
    current_step += 1
    await update_progress(websocket, current_step, total_steps)
    
    # Формирование файла с источниками
    sources_path = await make_sources_file(task, sources)
    current_step += 1
    await update_progress(websocket, current_step, total_steps)

    return pptx_path.replace(BASE_DIR, ''), pdf_path.replace(BASE_DIR, ''), sources_path.replace(BASE_DIR, '')