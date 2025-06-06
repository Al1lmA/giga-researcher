import json
import os


class Config:
    def __init__(self, config_file: str = None):
        self.config_file = config_file if config_file else os.getenv('CONFIG_FILE')
        self.retriever = os.getenv('SEARCH_RETRIEVER', "yandex")
        self.embedding_provider = os.getenv('EMBEDDING_PROVIDER', 'gigachat')
        self.llm_provider = os.getenv('LLM_PROVIDER', "GigaChat")
        self.fast_llm_model = os.getenv('FAST_LLM_MODEL', "GigaChat-Plus")
        self.smart_llm_model = os.getenv('SMART_LLM_MODEL', "GigaChat-Pro")
        self.scope = os.getenv('SCOPE', 'GIGACHAT_API_CORP')
        self.fast_token_limit = int(os.getenv('FAST_TOKEN_LIMIT', 2000)) 
        self.smart_token_limit = int(os.getenv('SMART_TOKEN_LIMIT', 4000)) 
        self.browse_chunk_max_length = int(os.getenv('BROWSE_CHUNK_MAX_LENGTH', 8192))
        self.summary_token_limit = int(os.getenv('SUMMARY_TOKEN_LIMIT', 2000)) #700
        self.temperature = float(os.getenv('TEMPERATURE', 0.55))
        self.user_agent = os.getenv('USER_AGENT', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                   "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0")
        self.max_search_results_per_query = int(os.getenv('MAX_SEARCH_RESULTS_PER_QUERY', 6))
        self.memory_backend = os.getenv('MEMORY_BACKEND', "local")
        self.total_words = int(os.getenv('TOTAL_WORDS', 1000))
        self.report_format = os.getenv('REPORT_FORMAT', "APA")
        self.max_iterations = int(os.getenv('MAX_ITERATIONS', 4))
        self.agent_role = os.getenv('AGENT_ROLE', None)
        self.scraper = os.getenv("SCRAPER", "bs")

        self.load_config_file()

    def load_config_file(self) -> None:
        if self.config_file is None:
            return None
        with open(self.config_file, "r") as f:
            config = json.load(f)
        for key, value in config.items():
            self.__dict__[key] = value

