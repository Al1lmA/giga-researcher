import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import time
from gpt_researcher.config import Config
from gpt_researcher.master.functions import *
from gpt_researcher.context.compression import ContextCompressor
from gpt_researcher.memory import Memory
from modules.google import search_google
from loguru import logger
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import GigaChat
import os
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

class GPTResearcher:

    def __init__(self, query='', config_path=None, websocket=None):
        logger.info("Инициализация GPTResearcher...")
        self.query = query
        self.agent = None
        self.role = None
        self.websocket = websocket
        self.cfg = Config(config_path)
        self.retriever = get_retriever(self.cfg.retriever)
        self.context = []
        self.memory = Memory(self.cfg.embedding_provider)
        logger.info("GPTResearcher успешно создан!")
        self.visited_urls = set()

    async def run(self, facts=''):

        logger.info(f"Поиск информации по теме '{self.query}'")

        
        await stream_output("logs", f"Поиск информации по теме '{self.query}'", self.websocket)
        await asyncio.sleep(1)
        
        self.agent, self.role = await choose_agent(self.query, self.cfg)
        
        await stream_output("logs", self.agent, self.websocket)
        await asyncio.sleep(1)
        try:
            self.context = await self.get_context_by_search(self.query)
        except Exception as e:
            logger.error("Ошибка при сборе информации", e)
        try:
            report = await generate_report(query=self.query, context=self.context, facts=facts,
                                       agent_role_prompt=self.role,
                                       websocket=self.websocket, cfg=self.cfg)
        except Exception as e:
            logger.error("Ошибка создания отчета", e)
        await asyncio.sleep(2)
        return report
    
    async def qa_run(self, question):

        logger.info(f"Поиск информации по теме '{question}'")

        self.context = await self.get_context_by_search(question)

        answer = await get_answer(query=question, context=self.context, cfg=self.cfg)
        return answer


    async def get_context_by_search(self, query):

        context = []
        # Генерация подзапросов
        sub_queries = await get_sub_queries(query, self.role, self.cfg) + [query]
        await stream_output("logs",
                            f"🧠 Для поиска информации будут использованы следующие запросы: {sub_queries}...",
                            self.websocket)
        await asyncio.sleep(0.5)
        
        try:
            for sub_query in sub_queries:
                await stream_output("logs", f"\n🔎 Поиск по запросу '{sub_query}'...", self.websocket)
                scraped_sites = await self.scrape_sites_by_query(sub_query)
                content = await self.get_similar_content_by_query(sub_query, scraped_sites)
                context.append(content)
        except Exception as er:
            logger.exception(er)
        return context

    async def get_new_urls(self, url_set_input):
        new_urls = []
        for url in url_set_input:
            if url not in self.visited_urls:
                await stream_output("logs", f"✅ Добавлен источник для исследования: {url}\n", self.websocket)
                await asyncio.sleep(0.5)
                self.visited_urls.add(url)
                new_urls.append(url)

        return new_urls

    async def scrape_sites_by_query(self, sub_query):

        retriever = self.retriever(sub_query)
        search_results = retriever.search(max_results=self.cfg.max_search_results_per_query)
        new_search_urls = await self.get_new_urls([url.get("href") for url in search_results])
        scraped_content_results = scrape_urls(new_search_urls, self.cfg)
        return scraped_content_results

    async def get_similar_content_by_query(self, query, pages):
        context_compressor = ContextCompressor(documents=pages, embeddings=self.memory.get_embeddings())
        return context_compressor.get_context(query, max_results=8)



    async def add_card_value_(self, org_name):
        try:
            card = {}
            keys = [
            'Год основания',
            'Телефон',
            'Email',
            'Количество сотрудников',
            'Ключевые технологии',
            'Сферы применения',
            'Официальный сайт']

            quest = [
                f'Год основания компании {org_name}?',
                f'Номер телефона или горячая линия компании {org_name}?', 
                f'Электронная почта или Email компании {org_name}?',
                f'Сколько сотрудников работает в {org_name}?', 
                f'Какие ключевые технологии применяет компания {org_name}?', 
                f'Какая сфера примения компании или в какой индустрии работает компания {org_name}?', 
                f'Официальный сайт {org_name}?'    
            ]
            qa_template=generate_qa_prompt()
            
            for key, question in zip(keys, quest):
                try: 
                    chain = await qa_rag_giga(
                    model=self.cfg.smart_llm_model,
                    qa_template=qa_template)
                    response = chain.invoke({"question": question})
                    result = response["answer"]
                    card[key]=result
                except Exception as er:
                    logger.error(er)
        except Exception as er:
            logger.error(er)   

        return card
    

    async def generate_conclusion(self, text):
        result = ""
        try:
            result = await create_chat_completion(
                model=self.cfg.fast_llm_model,
                messages=[
                    {"role": "system", "content": f"{agent_conclusion_prompt()}"},
                    {"role": "user", "content": f"{generate_conclusion_prompt(text)}"}],
                temperature=0.5,
                llm_provider=self.cfg.llm_provider,
                stream=True,
                profanity_check=False,
                verify_ssl_certs=False,
                max_tokens=self.cfg.smart_token_limit,
            )
        except Exception as e:
            logger.error(e)
        
        return result

    async def get_executive_summary(self, text):
        result = ""
        try:
            result = await create_chat_completion(
                model=self.cfg.fast_llm_model,
                messages=[
                    {"role": "system", "content": f"{agent_role_executive_summary_prompt()}"},
                    {"role": "user", "content": f"{generate_executive_summary_prompt(text)}"}],
                temperature=0.5,
                llm_provider=self.cfg.llm_provider,
                stream=True,
                profanity_check=False,
                verify_ssl_certs=False,
                max_tokens=self.cfg.smart_token_limit,
            )
        except Exception as e:
            logger.error(e)
        return result
    
    