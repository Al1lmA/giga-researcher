import asyncio
import json
from typing import List, Dict
from fastapi import WebSocket
from loguru import logger
from gpt_researcher.master.agent import GPTResearcher
from modules.egrul import get_egrul, make_card
from modules.company import Company
from modules.bfo import get_content_from_bfo, get_table_and_graph
from backend.utils import convert_pptx_to_pdf, write_md_to_pdf
from backend.mr_report_type import chain_with_source

async def update_progress(websocket: WebSocket, current_step: int, total_steps: int):
	progress_percentage = int(current_step / total_steps * 100)
	await websocket.send_json({"type": "progress", "output": progress_percentage})

# 2 минуты сборки
async def qcheck_report(websocket: WebSocket, task: str):
	# await websocket.send_json({"type": "logs", "output": f"\nQCHECK REPORT  {task}\n\n"})
	comp = Company(inn=task)

	total_steps = 16 #Количество шагов (блоков) в qcheck_report
	current_step = 0

	#  Сбор данных из ЕГРЮЛ
	try:
		comp = await get_egrul(comp)
		# current_step += 1
		# await update_progress(websocket, current_step, total_steps)
	except Exception as er:
		logger.error(er)
		await websocket.send_json({"type": "logs", "output": f"\nОшибка при получении данных из ЕГРЮЛ\n\nПроверьте ИНН компании"})
		return
	
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	try:
		comp = await make_card(comp)
		# current_step += 1
		# await update_progress(websocket, current_step, total_steps)
		await websocket.send_json({"type": "logs", "output": f"\nПолучены данные из ЕГРЮЛ\n\n"})
	except Exception as er:
		logger.error(er)
		# await websocket.send_json({"type": "logs", "output": f"\nОшибка при получении данных из ЕГРЮЛ\n\n"})
	await websocket.send_json({"type": "logs", "output": f"Компания - {comp.org_name}"})
	await asyncio.sleep(0.5)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	#  Сбор данных из БФО
	try:
		comp = await get_content_from_bfo(comp)
		comp = await get_table_and_graph(comp)
		# current_step += 1
		# await update_progress(websocket, current_step, total_steps)
		await websocket.send_json({"type": "logs", "output": f"\nПолучены данные из БФО\n\n"})
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await asyncio.sleep(0.5)

	# Gigachat
	researcher = GPTResearcher(config_path=None,  websocket=websocket)
	chain = await chain_with_source()

	# О компании
	try:
		query = f'основная информация о компании {comp.org_name}, {comp.inn}'
		response = chain.invoke({"question": query})
		comp.text_o_kompanii = response["answer"]
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	
	# Добавляем данные карточки компании
	try:
		if task == '7707083893':
			comp.card.update({
				'Год основания':'1841 г.',
				'Телефон': '8(800)555-55-50',
				'Email':'sberbank@sberbank.ru',
				'Количество сотрудников':'281 000',
				'Ключевые технологии':'n/a',
				'Сферы применения':'Банковская сфера',
				'Официальный сайт':'www.sberbank.ru'
						})
		elif task == '7707049388':
			comp.card.update({
				'Год основания':'1993 г.',
				'Телефон':'+7(499)999-82-83',
				'Email':'rostelecom@rt.ru',
				'Количество сотрудников':'119 400',
				'Ключевые технологии':'n/a',
				'Сферы применения':'Телекоммуникации и IT',
				'Официальный сайт': 'www.company.rt.ru'
						})
		else:
			comp.card.update(await researcher.add_card_value_(comp.org_name))
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	
	# "Анализ владения"
	try:
		query = f'анализ владельцев компании {comp.org_name}'
		response = chain.invoke({"question": query})
		comp.holders = response["answer"]
		await websocket.send_json({"type": "logs", "output": f"{query}"})
		await websocket.send_json({"type": "report", "output": response["answer"]})
		
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	# await websocket.send_json({"type": "logs", "output": f"\nПолучены данные о компании и владельцах\n\n"})
	await asyncio.sleep(0.5)


	# "Бизнес-модель"
	try:
		query = f'Бизнес-модель компании {comp.org_name}'
		response = chain.invoke({"question": query})
		comp.bm = response["answer"]
		await websocket.send_json({"type": "logs", "output": f"{query}"})
		await websocket.send_json({"type": "report", "output": response["answer"]})
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await asyncio.sleep(0.5)

	# "Инвестиции"
	try:
		query = f'Инвестиции компании {comp.org_name}'
		response = chain.invoke({"question": query})
		comp.invest = response["answer"]
		await websocket.send_json({"type": "logs", "output": f"{query}"})
		await websocket.send_json({"type": "report", "output": response["answer"]})
	except Exception as er:
		logger.error(er)

	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await asyncio.sleep(0.5)

	# "Ключевые клиенты"
	try:
		query = f'Ключевые клиенты компании {comp.org_name}'
		response = chain.invoke({"question": query})
		comp.customers = response['answer']
		await websocket.send_json({"type": "logs", "output": f"{query}"})
		await websocket.send_json({"type": "report", "output": response["answer"]})
	except Exception as er:
		logger.error(er)
	
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await asyncio.sleep(0.1)

	# Продукты
	try:
		query = f'Продукты компании {comp.org_name}'
		response = chain.invoke({"question": query})
		comp.products = response['answer']
		await websocket.send_json({"type": "logs", "output": f"{query}"})
		await websocket.send_json({"type": "report", "output": response["answer"]})
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await asyncio.sleep(0.1)

	# ИТ-Инфраструктура
	try:
		query = f'ИТ-Инфраструктура компании {comp.org_name}'
		response = chain.invoke({"question": query})
		comp.infra = response['answer']
		await websocket.send_json({"type": "logs", "output": f"{query}"})
		await websocket.send_json({"type": "report", "output": response["answer"]})
	except Exception as er:
		logger.error(er)

	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await asyncio.sleep(0.1)

	# Оценка рынка и конкурентов
	try:
		try:
			market = comp.card['Сферы применения']
		except:
			market = ''
		query = f'Оценка рынка {market} и конкурентов компании {comp.org_name}'
		response = chain.invoke({"question": query})
		comp.competitors = response['answer']
		await websocket.send_json({"type": "logs", "output": f"{query}"})
		await websocket.send_json({"type": "report", "output": response["answer"]})
	except Exception as er:
		logger.error(er)

	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await asyncio.sleep(0.1)
	
	# Оценка команды
	try:
		query = f'Оценка команды компании {comp.org_name}'
		response = chain.invoke({"question": query})
		comp.team = response['answer']
		await websocket.send_json({"type": "logs", "output": f"{query}"})
		await websocket.send_json({"type": "report", "output": response["answer"]})
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	

	text = comp.combine_texts()
	# Заключение
	try:      
		comp.conclusion = await researcher.generate_conclusion(text)
		text += '\n' + comp.conclusion
	except Exception as er:
		logger.error(er)
	
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	# Executive summary
	try:
		comp.summ = await researcher.get_executive_summary(text)
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	# Формирование презентации 
	try:
		pptx_path  = await comp.make_pptx()
	except Exception as er:
		logger.error(er)

	try:
		pdf_path = await convert_pptx_to_pdf(pptx_path, "/home/TIsAmbrosyeva/giga_researcher/outputs")
	except Exception as er:
		logger.error(er) 
	
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	return pptx_path.replace('/home/TIsAmbrosyeva/giga_researcher/', ''), pdf_path.replace('/home/TIsAmbrosyeva/giga_researcher/', '')


# 1-й вариант, 8 минут сборки
async def qcheck_report_(websocket: WebSocket, task: str):
	await websocket.send_json({"type": "logs", "output": f"\nQCHECK REPORT  {task}\n\n"})
	comp = Company(inn=task)

	total_steps = 16 #Количество шагов (блоков) в qcheck_report
	current_step = 0

	#  Сбор данных из ЕГРЮЛ
	try:
		comp = await get_egrul(comp)
		# current_step += 1
		# await update_progress(websocket, current_step, total_steps)
	except Exception as er:
		logger.error(er)
		await websocket.send_json({"type": "logs", "output": f"\nОшибка при получении данных из ЕГРЮЛ\n\nПроверьте ИНН компании"})
		return
	
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	try:
		comp = await make_card(comp)
		# current_step += 1
		# await update_progress(websocket, current_step, total_steps)
		await websocket.send_json({"type": "logs", "output": f"\nПолучены данные из ЕГРЮЛ\n\n"})
	except Exception as er:
		logger.error(er)
		# await websocket.send_json({"type": "logs", "output": f"\nОшибка при получении данных из ЕГРЮЛ\n\n"})
	await websocket.send_json({"type": "logs", "output": f"Компания - {comp.org_name}"})
	await asyncio.sleep(0.5)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	#  Сбор данных из БФО
	try:
		comp = await get_content_from_bfo(comp)
		comp = await get_table_and_graph(comp)
		# current_step += 1
		# await update_progress(websocket, current_step, total_steps)
		await websocket.send_json({"type": "logs", "output": f"\nПолучены данные из БФО\n\n"})
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await asyncio.sleep(0.5)

	# Gigachat
	researcher = GPTResearcher(config_path=None,  websocket=websocket)

	# О компании
	try:
		researcher.query = f'основная информация о компании {comp.org_name}, {comp.inn}'
		comp.text_o_kompanii = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	
	# Добавляем данные карточки компании
	try:
		if task == '7707083893':
			comp.card.update({
				'Год основания':'1841 г.',
				'Телефон': '8(800)555-55-50',
				'Email':'sberbank@sberbank.ru',
				'Количество сотрудников':'281 000',
				'Ключевые технологии':'n/a',
				'Сферы применения':'Банковская сфера',
				'Официальный сайт':'www.sberbank.ru'
						})
		elif task == '7707049388':
			comp.card.update({
				'Год основания':'1993 г.',
				'Телефон':'+7(499)999-82-83',
				'Email':'rostelecom@rt.ru',
				'Количество сотрудников':'119 400',
				'Ключевые технологии':'n/a',
				'Сферы применения':'Телекоммуникации и IT',
				'Официальный сайт': 'www.company.rt.ru'
						})
		else:
			comp.card.update(await researcher.add_card_value_(comp.org_name))
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	
	# "Анализ владения"
	try:
		researcher.query = f'анализ владельцев компании {comp.org_name}'
		comp.holders = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	await websocket.send_json({"type": "logs", "output": f"\nПолучены данные о компании и владельцах\n\n"})
	await asyncio.sleep(0.5)


	# "Бизнес-модель"
	try:
		researcher.query = f'Бизнес-модель компании {comp.org_name}'
		comp.bm = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	# "Инвестиции"
	try:
		researcher.query = f'Инвестиции компании {comp.org_name}'
		comp.invest = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)

	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	# "Ключевые клиенты"
	try:
		researcher.query = f'Ключевые клиенты компании {comp.org_name}'
		comp.customers = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)
	
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	# Продукты
	try:
		researcher.query = f'Продукты компании {comp.org_name}'
		comp.products = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	# ИТ-Инфраструктура
	try:
		researcher.query = f'ИТ-Инфраструктура компании {comp.org_name}'
		comp.infra = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)

	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	# Оценка рынка и конкурентов
	try:
		try:
			market = comp.card['Сферы применения']
		except:
			market = ''
		researcher.query = f'Оценка рынка {market} и конкурентов компании {comp.org_name}'
		comp.competitors = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)

	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	# Оценка команды
	try:
		researcher.query = f'Оценка команды компании {comp.org_name}'
		comp.team = await researcher.run(facts=json.dumps(comp.card, ensure_ascii=False, indent=4))
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	
	text = comp.combine_texts()
	# Заключение
	try:      
		comp.conclusion = await researcher.generate_conclusion(text)
		text += '\n' + comp.conclusion
	except Exception as er:
		logger.error(er)
	
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	# Executive summary
	try:
		comp.summ = await researcher.get_executive_summary(text)
	except Exception as er:
		logger.error(er)
	current_step += 1
	await update_progress(websocket, current_step, total_steps)
	# Формирование презентации 
	try:
		pptx_path  = await comp.make_pptx()
	except Exception as er:
		logger.error(er)

	try:
		pdf_path = await convert_pptx_to_pdf(pptx_path, "/home/TIsAmbrosyeva/giga_researcher/outputs")
	except Exception as er:
		logger.error(er) 
	
	current_step += 1
	await update_progress(websocket, current_step, total_steps)

	return pptx_path.replace('/home/TIsAmbrosyeva/giga_researcher/', ''), pdf_path.replace('/home/TIsAmbrosyeva/giga_researcher/', '')
