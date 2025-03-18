from langchain_community.vectorstores import FAISS
import os
from langchain_community.embeddings import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

class Memory:
    def __init__(self, embedding_provider, **kwargs):

        _embeddings = None
        match embedding_provider:
            case "ollama":
                _embeddings = OllamaEmbeddings(model="llama2")
            case "openai":
                _embeddings = OpenAIEmbeddings()
            case "huggingface":
                from langchain.embeddings import HuggingFaceEmbeddings
                _embeddings = HuggingFaceEmbeddings()
            case "gigachat":
                from langchain_community.embeddings import GigaChatEmbeddings
                _embeddings = GigaChatEmbeddings(
                    credentials= os.environ["GIGACHAT_CREDENTIALS"],
                    scope= os.environ["GIGACHAT_SCOPE"],
                    verify_ssl_certs = False,
                    model='Embeddings',
                    one_by_one_mode=True
                )

            case _:
                raise Exception("Embedding provider not found.")

        self._embeddings = _embeddings

    def get_embeddings(self):
        return self._embeddings
