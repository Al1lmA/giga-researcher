import os
import requests
import json



class GoogleSearch:

    def __init__(self, query):
        self.query = query
        self.api_key = self.get_api_key() #GOOGLE_API_KEY
        self.cx_key = self.get_cx_key() #GOOGLE_CX_KEY

    def get_api_key(self):

        try:
            api_key = os.environ["GOOGLE_API_KEY"]
        except:
            raise Exception("GOOGLE_API_KEY не найден")
        return api_key

    def get_cx_key(self):

        try:
            api_key = os.environ["GOOGLE_CX_KEY"]
        except:
            raise Exception("GOOGLE_CX_KEY не найден")
        return api_key

    def search(self, max_results=7):
        url = f"https://www.googleapis.com/customsearch/v1?key={self.api_key}&cx={self.cx_key}&q={self.query}&start=1&sort=date"
        resp = requests.get(url)

        if resp is None:
            return
        try:
            search_results = json.loads(resp.text)
        except Exception:
            return
        if search_results is None:
            return

        results = search_results.get("items", [])
        search_results = []

        for result in results:
            if "youtube.com" in result["link"]:
                continue
            search_result = {
                "title": result["title"],
                "href": result["link"],
                "body": result["snippet"],
            }
            search_results.append(search_result)

        return search_results
