from .retriever import SearchAPIRetriever
from langchain.retrievers import (
    ContextualCompressionRetriever,
)
from langchain.retrievers.document_compressors import (
    DocumentCompressorPipeline,
    EmbeddingsFilter,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

   
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from typing import List


class CustomRetriever(BaseRetriever):
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        return [Document(page_content=query)]


class ContextCompressor:
    def __init__(self, documents, embeddings, max_results=5, **kwargs):
        self.max_results = max_results
        self.documents = documents
        self.kwargs = kwargs
        self.embeddings = embeddings

    def _get_contextual_retriever(self):
        splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=100) # 512 максимальное кол-во токенов Giga Embedding
        relevance_filter = EmbeddingsFilter(embeddings=self.embeddings, similarity_threshold=0.78)
        pipeline_compressor = DocumentCompressorPipeline(
            transformers=[splitter, relevance_filter]
        )
        base_retriever = SearchAPIRetriever(
            pages=self.documents
        )
        contextual_retriever = ContextualCompressionRetriever(
            base_compressor=pipeline_compressor, base_retriever=base_retriever
        )
        return contextual_retriever

    def _pretty_print_docs(self, docs, top_n):
        result = f"\n".join(f"Source: {d.metadata.get('source')}\n"
                          f"Title: {d.metadata.get('title')}\n"
                          f"Content: {d.page_content}\n"
                          for i, d in enumerate(docs) if i < top_n)

        
        return result

    def get_context(self, query, max_results=5):
        compressed_docs = self._get_contextual_retriever()
        relevant_docs = compressed_docs.invoke(query)
        return self._pretty_print_docs(relevant_docs, max_results)
 