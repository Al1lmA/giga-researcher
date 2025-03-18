from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial

import requests


from langchain_community.retrievers import ArxivRetriever
from bs4 import BeautifulSoup
from newspaper import Article
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import WebBaseLoader
from loguru import logger

class WebBaseLoaderScraper:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def scrape(self) -> str:
        """ Извлекает содержимое с веб-страницы """

        try:
            loader = WebBaseLoader(self.link)
            loader.requests_kwargs = {"verify": False}
            docs = loader.load()
            content = ""

            for doc in docs:
                content += doc.page_content

            return content

        except Exception as e:
            logger.error("Scrape 48: Error! : " + str(e))
            return ""


class PyMuPDFScraper:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def scrape(self) -> str:
        loader = PyMuPDFLoader(self.link)
        doc = loader.load()
        return str(doc)


class NewspaperScraper:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def scrape(self) -> str:

        try:
            article = Article(
                self.link,
                language="en",
                memoize_articles=False,
                fetch_images=False,
            )
            article.download()
            article.parse()

            title = article.title
            text = article.text

            if not (title and text):
                return ""

            return f"{title} : {text}"

        except Exception as e:
            logger.error("Scrape 109: Error! : " + str(e))
            return ""



class BeautifulSoupScraper:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def scrape(self):
        try:
            response = self.session.get(self.link, timeout=5, verify=False)
            soup = BeautifulSoup(
                response.content, "lxml", from_encoding=response.encoding
            )

            for script_or_style in soup(["script", "style"]):
                script_or_style.extract()

            raw_content = self.get_content_from_url(soup)
            lines = (line.strip() for line in raw_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = "\n".join(chunk for chunk in chunks if chunk)
            return content

        except Exception as e:
            logger.error("Scrape 147: Error! : " + str(e))
            return ""
        
    def get_content_from_url(self, soup):

        text = ""
        tags = ["p", "h1", "h2", "h3", "h4", "h5"]
        for element in soup.find_all(tags):  # Find all the <p> elements
            text += element.text + "\n"
        return text


class ArxivScraper:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def scrape(self):

        query = self.link.split("/")[-1]
        retriever = ArxivRetriever(load_max_docs=2, doc_content_chars_max=None)
        docs = retriever.get_relevant_documents(query=query)
        return docs[0].page_content


class Scraper:


    def __init__(self, urls, user_agent, scraper):

        self.urls = urls
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.scraper = scraper

    def run(self):

        partial_extract = partial(self.extract_data_from_link, session=self.session)
        with ThreadPoolExecutor(max_workers=20) as executor:
            contents = executor.map(partial_extract, self.urls)
        res = [content for content in contents if content["raw_content"] is not None]
        return res

    def extract_data_from_link(self, link, session):

        content = ""
        try:
            Scraper = self.get_scraper(link)
            scraper = Scraper(link, session)
            content = scraper.scrape()

            if len(content) < 100:
                return {"url": link, "raw_content": None}
            return {"url": link, "raw_content": content}
        except Exception as e:
            return {"url": link, "raw_content": None}

    def get_scraper(self, link):

        SCRAPER_CLASSES = {
            "pdf": PyMuPDFScraper,
            "arxiv": ArxivScraper,
            "newspaper": NewspaperScraper,
            "bs": BeautifulSoupScraper,
            "web_base_loader": WebBaseLoaderScraper,
        }

        scraper_key = None

        if link.endswith(".pdf"):
            scraper_key = "pdf"
        elif "arxiv.org" in link:
            scraper_key = "arxiv"
        else:
            scraper_key = self.scraper

        scraper_class = SCRAPER_CLASSES.get(scraper_key)
        if scraper_class is None:
            raise Exception("Scraper not found.")

        return scraper_class
