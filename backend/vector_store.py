import chromadb
from chromadb.config import Settings


class VectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )

    # ── Write ──────────────────────────────────────────────────────────────────

    def add_documents(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadata: list[dict],
    ) -> None:
        """
        Upsert document chunks into the collection.

        Args:
            ids:        Unique string ID per chunk  (e.g. "doc_7_chunk_0")
            texts:      Raw text for each chunk     (stored as document)
            embeddings: Pre-computed float vectors  (must match len of ids)
            metadata:   Dicts with at least         {"document_id": int, "workspace_id": int}
        """
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadata,
        )

    # ── Read ───────────────────────────────────────────────────────────────────

    def query(self, query_embedding, workspace_id: int | None = None, n_results: int = 5):
        where_filter = None

        if workspace_id is not None:
            where_filter = {"workspace_id": workspace_id}

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for idx in range(len(results["ids"][0])):
            meta = results["metadatas"][0][idx]
            hits.append(
                {
                    "id":           results["ids"][0][idx],
                    "text":         results["documents"][0][idx],
                    "distance":     results["distances"][0][idx],
                    "document_id":  meta.get("document_id"),
                    "workspace_id": meta.get("workspace_id"),
                }
            )

        return hits

    # ── Helpers ────────────────────────────────────────────────────────────────

    def delete_document(self, document_id: int) -> None:
        """Remove all chunks that belong to a given document."""
        self._collection.delete(
            where={"document_id": document_id}
        )

    def delete_workspace(self, workspace_id: int) -> None:
        """Remove all chunks that belong to a given workspace."""
        self._collection.delete(
            where={"workspace_id": workspace_id}
        )

    def count(self) -> int:
        """Return total number of chunks stored in the collection."""
        return self._collection.count()
'''
---

**Data flow:**
```
embed_text(text)          add_documents(...)
      │                          │
      ▼                          ▼
list[float]  ──────────▶  ChromaDB collection
                               "documents"
                          (persisted to ./chroma_db)
                                 │
              query(embedding) ──┘
                                 │
                                 ▼
                       list[dict]  ← ranked by cosine distance
```

**Key design decisions:**

- **`cosine` space** — set on the collection at creation time; ideal for normalized sentence embeddings from both OpenAI and `sentence-transformers`.
- **`upsert` over `add`** — re-indexing a document is idempotent; no duplicate chunks accumulate on repeated ingestion.
- **Flat result dicts** — the nested Chroma response structure is unwrapped into a clean list so callers don't need to know ChromaDB's internal format.
- **Two bonus helpers** — `delete_document` and `delete_workspace` use Chroma's metadata `where` filter, keeping the vector store in sync when SQLAlchemy rows are deleted.

**Add to `requirements.txt`:**
```
chromadb>=0.5.0'''
