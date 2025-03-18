import asyncio
from gpt_researcher.utils.llm import *
from gpt_researcher.scraper import Scraper
from gpt_researcher.master.prompts import *
import json
from loguru import logger
import re

def get_retriever(retriever):

    match retriever:
        case "google":
            from gpt_researcher.retrievers import GoogleSearch
            retriever = GoogleSearch
        
        case "yandex":
            from gpt_researcher.retrievers import YandexSearch
            retriever = YandexSearch

        case _:
            raise Exception("Retriever not found.")

    return retriever

def extract_values(data):
    # Используем регулярные выражения для поиска пар ключ-значение
    pattern = r'"([^"]+)":\s*"([^"]+)"'
    matches = re.findall(pattern, data) 
    # Преобразуем список кортежей в словарь
    result_dict = {key: value for key, value in matches}
    
    return result_dict

async def choose_agent(query, cfg):
    try:
        response = await create_chat_completion(
            model=cfg.smart_llm_model,
            messages=[
                {"role": "system", "content": f"{auto_agent_instructions()}"},
                {"role": "user", "content": f"task: {query}"}],
            temperature=0.5,
            llm_provider=cfg.llm_provider,
            profanity_check=False,
            verify_ssl_certs=False,
            max_tokens=cfg.smart_token_limit,
        )
        logger.info(response)
        try:
            agent_dict = json.loads(response)
            return agent_dict["server"], agent_dict["agent_role_prompt"]
        except Exception as e:
            logger.error(e)
            agent_dict = extract_values(response)
            return agent_dict["server"], agent_dict["agent_role_prompt"]
    except Exception as e:
        logger.error(e)
        try:
            s = response
            start = s.find('{')
            end = s.rfind('}') + 1
            agent_dict = json.loads(re.sub(r'[\t\n\r\f\v]', '', s[start:end]))
            return agent_dict["server"], agent_dict["agent_role_prompt"]
        except Exception as e:
            logger.error(e)
            return "Агент исследователь", "Вы - AI-ассистент исследователя.У вас критическое мышление. Ваша единственная цель - написать хорошо структурированные, критически оцененные, объективные отчеты по теме исследования. Старайтесь НЕ повторять информацию, которая уже есть в отчете"
    
async def get_sub_queries(query, agent_role_prompt, cfg):

    max_research_iterations = cfg.max_iterations if cfg.max_iterations else 1
    response = await create_chat_completion(
        model=cfg.smart_llm_model,
        messages=[
            {"role": "system", "content": f"{agent_role_prompt}"},
            {"role": "user", "content": generate_search_queries_prompt(query, max_iterations=max_research_iterations)}],
        temperature=0.5,
        llm_provider=cfg.llm_provider,
        profanity_check=False,
        verify_ssl_certs=False,
        max_tokens=cfg.smart_token_limit,
    )
    sub_queries = json.loads(response)
    return sub_queries


def scrape_urls(urls, cfg=None):

    content = []
    user_agent = cfg.user_agent if cfg else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
    try:
        content = Scraper(urls, user_agent, cfg.scraper).run()
    except Exception as e:
        logger.error(f"Error in scrape_urls: {e}")
    return content


async def summarize(query, content, agent_role_prompt, cfg, websocket=None):

    async def handle_task(url, chunk):
        summary = await summarize_url(query, chunk, agent_role_prompt, cfg)
        return url, summary

    def chunk_content(raw_content, chunk_size=10000):
        words = raw_content.split()
        for i in range(0, len(words), chunk_size):
            yield ' '.join(words[i:i+chunk_size])

    concatenated_summaries = []
    for item in content:
        url = item['url']
        raw_content = item['raw_content']
        chunk_tasks = [handle_task(url, chunk) for chunk in chunk_content(raw_content)]
        chunk_summaries = await asyncio.gather(*chunk_tasks)
        summaries = [summary for _, summary in chunk_summaries if summary]
        concatenated_summary = ' '.join(summaries)
        concatenated_summaries.append({'url': url, 'summary': concatenated_summary})

    return concatenated_summaries


async def summarize_url(query, raw_data, agent_role_prompt, cfg):
    summary = ""
    try:
        summary = await create_chat_completion(
            model=cfg.fast_llm_model,
            messages=[
                {"role": "system", "content": f"{agent_role_prompt}"},
                {"role": "user", "content": f"{generate_summary_prompt(query, raw_data)}"}],
            temperature=0.5,
            llm_provider=cfg.llm_provider,
            stream=True,
            profanity_check=False,
            verify_ssl_certs=False,
            max_tokens=cfg.smart_token_limit,
        )
    except Exception as e:
        logger.error(f"Error in summarize: {e}")
    return summary



async def generate_report(query, context, facts, agent_role_prompt, websocket, cfg):

    generate_prompt = generate_report_prompt()
    report = ""
    try:
        report = await create_chat_completion(
            model=cfg.fast_llm_model,
            messages=[
                {"role": "system", "content": f"{agent_role_prompt}"},
                {"role": "user", "content": f"{generate_prompt(query, context, facts, cfg.report_format, cfg.total_words)}"}],
            temperature=0.5,
            llm_provider=cfg.llm_provider,
            stream=True,
            websocket=websocket,
            max_tokens=cfg.smart_token_limit,
            profanity_check=False,
            verify_ssl_certs=False
        )
    except Exception as e:
        logger.error(f"Ошибка создания отчета: {e}")
    
    try:
        report = await refine_text(report, query, cfg)

    except Exception as e:
        logger.error(e)
        
    return report



async def get_answer(query, context, cfg):
    
    answer = ""
    
    try:
        answer = await create_chat_completion(
            model=cfg.fast_llm_model,
            messages=[
                {"role": "system", "content": f"{qa_agent_prompt()}"},
                {"role": "user", "content": f"{generate_qa_prompt(query, context)}"}],
            temperature=0.5,
            llm_provider=cfg.llm_provider,
            stream=True,
            # max_tokens=cfg.smart_token_limit,
            profanity_check=False,
            verify_ssl_certs=False
        )
    except Exception as e:
        logger.error(e)
        
    return answer

async def stream_output(type, output, websocket=None, logging=True):

    if websocket:
        await websocket.send_json({"type": type, "output": output})





async def refine_text(text, query, cfg):
    """ Проверяет и улучшает текст, сохраняя научный стиль изложения. """


    agent_role_prompt = f"""
    Вы - опытный AI-помощник профессора филолога, специализирующегося на русском языке.
    Ваша задача - проверять и улучшать тексты научных работ.

    """

    try:
        # Улучшение текста
        messages = [
            {"role": "system", "content": f"{agent_role_prompt}"},
            {"role": "user", "content": f"""
                Улучшите следующий текст, устранив ошибки, грамматические и стилистические неточности, а также повторяющиеся фразы. Необходимо внести улучшения для повышения его качества. Перепишите текст, чтобы:

                1. Устранить повторы слов и фраз
                2. Улучшить логическую связность предложений
                3. Упростить сложные предложения
                4. Сохранить научный стиль изложения

                Примеры улучшенных предложений:
                - Вместо "Данный метод является наиболее эффективным методом" лучше написать "Данный метод является наиболее эффективным".
                - Вместо "Результаты исследования показали, что результаты исследования подтвердили гипотезу" лучше написать "Результаты исследования подтвердили гипотезу".

                Пример когда текст не требует улучшений:
                - "Результаты исследования подтвердили гипотезу", ответ должен быть - "Результаты исследования подтвердили гипотезу"
                
                Пожалуйста, верните только текст без дополнительных комментариев и оценок
                Если текст выглядит хорошо, верните ТОЛЬКО текст отправленный для проверки. НЕ пишите дополнительные комментарии и оценки.
             
                Текст для улучшения:
                {text}

                
                """
            }
        ]
        refined_text = await create_chat_completion(
            model=cfg.fast_llm_model,
            stream=True,
            messages=messages,
            llm_provider=cfg.llm_provider,
            profanity_check=False,
            verify_ssl_certs=False,
            temperature=0.5,
            max_tokens=cfg.smart_token_limit
        )
        
        return refined_text
    
    except Exception as e:
        logger.error(f"Error in refine_text: {e}")
        return text

