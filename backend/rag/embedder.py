import os
from typing import Optional


OPENAI_EMBED_MODEL = "text-embedding-3-small"
OPENAI_EMBED_DIM = 1536
LOCAL_EMBED_MODEL = "all-MiniLM-L6-v2"
LOCAL_EMBED_DIM = 384


class EmbeddingService:
    def __init__(self):
        self._api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self._use_openai: bool = bool(self._api_key)
        self._openai_client = None
        self._local_model = None

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=self._api_key)
        return self._openai_client

    def _get_local_model(self):
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer

            self._local_model = SentenceTransformer(LOCAL_EMBED_MODEL)
        return self._local_model

    @property
    def provider(self) -> str:
        return "openai" if self._use_openai else "local"

    @property
    def embedding_dimension(self) -> int:
        return OPENAI_EMBED_DIM if self._use_openai else LOCAL_EMBED_DIM

    def collection_name(self, base_name: str = "documents") -> str:
        # Keep vector collections isolated per embedding strategy.
        return f"{base_name}_{self.provider}_{self.embedding_dimension}"

    def embed_text(self, text: str) -> list[float]:
        if self._use_openai:
            return self._embed_openai([text])[0]
        return self._embed_local([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self._use_openai:
            return self._embed_openai(texts)
        return self._embed_local(texts)

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        client = self._get_openai_client()
        response = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=texts)
        return [item.embedding for item in response.data]

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._get_local_model()
        vectors = model.encode(texts, convert_to_numpy=True)
        return [v.tolist() for v in vectors]
