from backend.rag.embedder import EmbeddingService
from backend.rag.vector_store import VectorStore


class Retriever:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        n_results: int = 5,
    ):
        self._embedder = embedding_service or EmbeddingService()
        self._store = vector_store or VectorStore(collection_name=self._embedder.collection_name())
        self._n = n_results

    def retrieve(self, query: str, workspace_id: int | None = None) -> list[dict]:
        query_embedding = self._embedder.embed_text(query)
        return self._store.query(query_embedding, workspace_id=workspace_id, n_results=self._n)
