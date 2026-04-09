from backend.rag.retriever import Retriever


class RetrievalAgent:
    def __init__(self, retriever: Retriever | None = None):
        self._retriever = retriever or Retriever()

    def retrieve(self, query: str) -> list[dict]:
        return self._retriever.retrieve(query)
