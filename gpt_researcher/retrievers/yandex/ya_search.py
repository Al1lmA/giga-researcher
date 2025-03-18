
import os
import requests
from bs4 import BeautifulSoup
from loguru import logger

class YandexSearch:

	def __init__(self, query):

		self.query = query
		self.apikey = self.get_api_key()
		self.follderid = self.get_folderid() 
		self.domen = "ru"

	def get_api_key(self):

		try:
			api_key = os.environ["YANDEX_API_KEY"]
		except:
			raise Exception("Установите YANDEX_API_KEY")
		return api_key

	def get_folderid(self):

		try:
			folderid = os.environ["YANDEX_FOLDER_ID"]
		except:
			raise Exception("Установите YANDEX_FOLDER_ID")
		return folderid

	def search(self, max_results=1):

		logger.info("Поиск по запросу {0}...".format(self.query))
		url = f'https://yandex.{self.domen}/search/xml?folderid={self.follderid}&apikey={self.apikey}&query={self.query}&l10n=ru&sortby=rlv.order%3Dascending&filter=none&maxpassages=5'
		resp = requests.get(url)

		if resp is None:
			return
		xml_data = resp.text
		soup = BeautifulSoup(xml_data, 'xml')
		search_results = []
		try:
			# Извлечение всех элементов <doc> из XML
			for doc in soup.find_all('doc'):
				title = doc.find('title').get_text() if doc.find('title') else ''
				href = doc.find('url').get_text() if doc.find('url') else ''
				if "youtube.com" in href:
					continue
				# Извлечение текста из всех тегов <passage>
				passages = doc.find_all('passage')
				body = ' '.join(p.get_text() for p in passages) if passages else doc.find('headline').get_text() if doc.find('headline') else ''

				# Создание словаря для результата
				search_result = {
					"title": title,
					"href": href,
					"body": body,
				}

				# Добавление результата в список
				search_results.append(search_result)
		except Exception as er:
			logger.error(er)

		return search_results
