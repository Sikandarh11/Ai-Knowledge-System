import os
from typing import Optional


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

            self._local_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._local_model

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
        response = client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [item.embedding for item in response.data]

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._get_local_model()
        vectors = model.encode(texts, convert_to_numpy=True)
        return [v.tolist() for v in vectors]
