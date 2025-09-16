from dotenv import load_dotenv
import os
import httpx

# загружаем .env в окружение
load_dotenv()

url = "https://searchapi.api.cloud.yandex.net/v2/web/search"
headers = {
    "Authorization": f"Api-Key {os.environ['YANDEX_API_KEY']}",
    "Content-Type": "application/json"
}
payload = {
    "folderId": os.environ["YANDEX_FOLDER_ID"],
    "query": {
        "searchType": "SEARCH_TYPE_RU",
        "queryText": "Сергей Есенин"
    },
    "pageSize": 5,
    "page": 0,
    "lang": "ru"
}

r = httpx.post(url, headers=headers, json=payload)
print(r.status_code)
print(r.text)
