
import requests
import json
import zipfile
from io import BytesIO
import pandas as pd
import re
from docx import Document
import plotly.graph_objects as go
import os
from os.path import isdir
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from modules.company import *


from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

async def get_content_from_bfo(cls=Company):
	"""
	Получение контента с сайта https://bfo.ru/
	Выписка сохраняется в папке /data/ИНН/
	"""

	inn = cls.inn

	if inn == '7707083893' or inn == '7707049388':
		return cls

	# Подключение к главной странице, поиск компании по ИНН и получение ссылки на страницу компании
	options = webdriver.ChromeOptions()
	options.add_argument('--headless') 
	options.add_argument('--no-sandbox')
	bfo_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
	url = f"https://bo.nalog.ru/search?query={inn}&page=1"
	bfo_driver.get(url)
	url = bfo_driver.find_element(By.CSS_SELECTOR, "a.results-search-table-row").get_attribute("href")

	bfo_driver.quit()

	org_id = re.search(r'organizations-card/(\d+)', url).group(1)
	# Переход на страницу организации и получение json с корректирующими id для скачивания
	url = f"https://bo.nalog.ru/nbo/organizations/{org_id}/bfo/"
	# url = f"{url}/bfo"
	s = requests.Session()
	s.verify = False   
	headers = 	{"Host": "bo.nalog.ru",
				"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
				"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
				"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
				"Connection": "keep-alive",
				"Accept-Encoding": "gzip, deflate, br",
				"Referer": f"https://bo.nalog.ru/",
				"Sec-Fetch-Dest": "document",
				"Sec-Fetch-Mode": "navigate",
				"Sec-Fetch-Site": "same-origin",
				"Upgrade-Insecure-Requests": "1"} 
	r = s.get(url, headers=headers, cookies=s.cookies)
	jsn = json.loads(r.text)

	# Скачивание выписок БФО
	try:
		report = []
		for i in range(len(jsn)):
			period = jsn[i]['period']
			cor_id = jsn[i]['correction']['id']
			r = s.get(f"https://bo.nalog.ru/download/bfo/{org_id}?auditReport=true&balance=true&capitalChange=true&clarification=false&targetedFundsUsing=false&detailsId={cor_id}&financialResult=true&fundsMovement=true&type=WORD&period={period}", headers=headers, cookies=s.cookies)
			cls.resources.append(r.url)
			z = zipfile.ZipFile(BytesIO(r.content))
			z.extractall(f'./data/{inn}/{period}/')
			if z.filelist.__len__() > 1:
				report.append(z.filelist[1].filename) 

	except Exception as e:
		logger.error(e)
	s.close()
	logger.info(f"Выписки из БФО сохранены в папке /data/{inn}/")
	return cls





# Сохраняем данные по прибыли и обязательствам из выписки
def get_content_from_bfo_v1(df_list):
	val_=pd.DataFrame(columns=['Год', 'Чистая прибыль', 'Выручка', 'Краткосрочные обязательства', 'Долгосрочные обязательства'])
	val_['Год']= re.findall(r'\d{4}',  str(df_list[2].loc[1,8:].unique()))  #re.findall(r'\d+', str(df_list[3].loc[5,8:].unique())) 
	val_['Чистая прибыль']=[int(str(x).replace('(', '-').replace(' ', '').replace(')', '')) if x  else 0 for x in df_list[3].loc[23,8:].unique().tolist() ]
	val_['Выручка']=[int(str(x).replace('(', '-').replace(' ', '').replace(')', '')) if x  else 0 for x in df_list[3].loc[7,8:].unique().tolist()]
	val_['Краткосрочные обязательства'] = pd.Series([int(str(x).replace('(', '-').replace(' ', '').replace(')', ''))   for x in df_list[2].loc[24,8:12].unique().tolist() if x and x != '-'], dtype='float64')
	val_['Долгосрочные обязательства'] = pd.Series ([int(str(x).replace('(', '-').replace(' ', '').replace(')', '')) for x in df_list[2].loc[17,8:12].unique().tolist() if x and x != '-'], dtype='float64')
	return val_

	# Форма по КНД 0710096 -(Упрощенка)
def get_content_from_bfo_v2(df_list):
	val_=pd.DataFrame(columns=['Год', 'Чистая прибыль', 'Выручка', 'Краткосрочные обязательства', 'Долгосрочные обязательства'])
	val_['Год']= re.findall(r'\d{4}',  str(df_list[2].loc[4,9:].unique()))  #re.findall(r'\d+', str(df_list[3].loc[5,8:].unique())) 
	val_['Чистая прибыль']=pd.Series([int(str(x).replace('(', '-').replace(' ', '').replace(')', ''))  for x in df_list[2].loc[12,9:15].unique().tolist() if x and x != '-'])
	val_['Выручка']=pd.Series([int(str(x).replace('(', '-').replace(' ', '').replace(')', '')) for x in df_list[2].loc[6,9:15].unique().tolist() if x and x != '-'])
	val_['Краткосрочные обязательства'] = pd.Series([int(str(x).replace('(', '-').replace(' ', '').replace(')', ''))   for x in df_list[1].loc[19,9:12].unique().tolist() if x and x != '-'], dtype='float64')
	val_['Долгосрочные обязательства'] = pd.Series ([int(str(x).replace('(', '-').replace(' ', '').replace(')', '')) for x in df_list[1].loc[17,9:12].unique().tolist() if x and x != '-'], dtype='float64')
	return val_





# Формирование таблицы и графика
async def get_table_and_graph(cls= Company):
	try:
		inn = cls.inn
		if inn == '7707083893':
			
			table=pd.DataFrame({'Год' : [2020, 2021, 2022, 2023], 
						'Всего активов':[32979678372, 37799262365, 40348353059, 50308142066], 
						'Всего обязательств': [28255016171, 32450551738, 34763447400, 43976386587],
						'Прибыль за отчетный период':[709891879, 1219880284, 295765454, 1480818552]
						})
		elif inn == '7707049388':
			table=pd.DataFrame({'Год' : [2020, 2021, 2022, 2023], 
						'Чистая прибыль':[-9297531000, 17630466000, 8002597000, 13276028000],
						'Выручка':[348257696000, 350588729000, 364809057000,407505285000], 
						'Краткосрочные обязательства':[150808435000, 224966318000, 258527237000, 373207232000], 
						'Долгосрочные обязательства':[368223968000, 364962913000, 400503721000, 355583844000]
						})
		else:
			table=pd.DataFrame(columns=['Год', 'Чистая прибыль', 'Выручка', 'Краткосрочные обязательства', 'Долгосрочные обязательства'])

			for dir in os.listdir(f'./data/{inn}'):
				if isdir(f'./data/{inn}/{dir}'):
					for file in os.listdir(f'./data/{inn}/{dir}'):
						if file.endswith('docx'):
							try:
								doc = Document(f'./data/{inn}/{dir}/{file}')
								df_list = []
								for t in doc.tables:
									df = [['' for i in range(len(t.columns))] for j in range (len(t.rows))]
									for i, row in enumerate(t.rows):
										for j, cell in enumerate(row.cells):
											if cell.text:
												df[i][j] = cell.text
									df_list.append(pd.DataFrame(df))
							except Exception as e:
								logger.error(file, e)
							try:
								val_ = get_content_from_bfo_v1(df_list)
								table = pd.concat([table, val_], ignore_index=True)
							except Exception as e:
								# logger.error(e, ' ', file)
								try:
									val_ = get_content_from_bfo_v2(df_list)
									table = pd.concat([table, val_], ignore_index=True)
								except Exception as e:
									logger.error(e, ' ', file)
			table.drop_duplicates(subset=['Год'], inplace=True)
			table = table.sort_values(by=['Год'])
	except Exception as er:
		logger.error(er)
	try:
		table['Год'] = table['Год'].astype('str')
		y = table.set_index('Год', drop=True)


		fig = go.Figure()
		for i in y.columns:
			fig.add_trace(go.Scatter(x=y.index, y=y[i],
								mode='lines', 
								name=i))

		fig.update_layout(title_text='Выручка и прибыль компании.', yaxis_title='тыс. ₽', xaxis_title='год')
		fig.update_layout(
			autosize=False,
			width=1000,
			height=550)
		try:
			fig.write_image(f'./data/{inn}/graph.png')
		except Exception as er:
			logger.error(er)
		# Записываем график в переменную в виде байтов для использования в отчете
		graph = fig.to_image(format='png')
		cls.table = table
		cls.graph = graph
		logger.info("Формирование таблицы и графика завершено")
	except Exception as er:
		logger.exception(er)
	return cls


