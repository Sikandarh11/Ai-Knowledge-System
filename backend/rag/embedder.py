import os
import logging
import sys
from typing import Optional

from backend.core.config import settings


OPENAI_EMBED_MODEL = "text-embedding-3-small"
OPENAI_EMBED_DIM = 1536
OPENAI_EMBED_BATCH_SIZE = 64
LOCAL_EMBED_MODEL = "all-MiniLM-L6-v2"
LOCAL_EMBED_DIM = 384

logger = logging.getLogger(__name__)
SSL_ENV_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")


class EmbeddingService:
    def __init__(self):
        self._api_key: Optional[str] = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        self._use_openai: bool = bool(self._api_key)
        self._openai_client = None
        self._local_model = None

    @property
    def model_name(self) -> str:
        return OPENAI_EMBED_MODEL if self._use_openai else LOCAL_EMBED_MODEL

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI

            self._sanitize_ssl_env()

            self._openai_client = OpenAI(api_key=self._api_key)
        return self._openai_client

    @staticmethod
    def _sanitize_ssl_env() -> None:
        """Remove invalid SSL bundle overrides that break httpx/OpenAI init."""
        for name in SSL_ENV_VARS:
            value = os.getenv(name)
            if value and not os.path.exists(value):
                logger.warning("Ignoring invalid %s path: %s", name, value)
                os.environ.pop(name, None)

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
        try:
            if self._use_openai:
                try:
                    return self._embed_openai([text])[0]
                except Exception as exc:
                    logger.exception(
                        "OpenAI embedding failed; switching to local. "
                        "runtime_python=%s provider=%s exc_type=%s exc=%r",
                        sys.executable,
                        self.provider,
                        type(exc).__name__,
                        exc,
                    )
                    self._use_openai = False
                    return self._embed_local([text])[0]
            return self._embed_local([text])[0]
        except Exception as exc:
            raise RuntimeError(f"Embedding failed (provider={self.provider}): {exc}") from exc

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            if self._use_openai:
                try:
                    return self._embed_openai(texts)
                except Exception as exc:
                    logger.exception(
                        "OpenAI embedding batch failed; switching to local. "
                        "runtime_python=%s provider=%s exc_type=%s exc=%r",
                        sys.executable,
                        self.provider,
                        type(exc).__name__,
                        exc,
                    )
                    self._use_openai = False
                    return self._embed_local(texts)
            return self._embed_local(texts)
        except Exception as exc:
            raise RuntimeError(f"Embedding batch failed (provider={self.provider}): {exc}") from exc

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        client = self._get_openai_client()
        vectors: list[list[float]] = []
        for i in range(0, len(texts), OPENAI_EMBED_BATCH_SIZE):
            batch = texts[i : i + OPENAI_EMBED_BATCH_SIZE]
            response = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=batch)
            vectors.extend(item.embedding for item in response.data)
        return vectors

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._get_local_model()
        vectors = model.encode(texts, convert_to_numpy=True)
        return [v.tolist() for v in vectors]
