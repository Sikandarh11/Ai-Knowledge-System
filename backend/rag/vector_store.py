import chromadb
from chromadb.config import Settings


class VectorStore:
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "documents",
    ):
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        *,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadata: list[dict],
    ) -> None:
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadata,
        )

    def query(
        self,
        query_embedding: list[float],
        workspace_id: int | None = None,
        n_results: int = 5,
    ) -> list[dict]:
        if not query_embedding or not any(query_embedding):
            raise ValueError("Query embedding is empty")

        if n_results < 1:
            n_results = 5

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if workspace_id is not None:
            query_kwargs["where"] = {"workspace_id": workspace_id}

        results = self._collection.query(**query_kwargs)

        ids_batches = results.get("ids") or []
        docs_batches = results.get("documents") or []
        metas_batches = results.get("metadatas") or []
        dist_batches = results.get("distances") or []

        if not ids_batches or not docs_batches or not metas_batches or not dist_batches:
            return []

        ids = ids_batches[0]
        docs = docs_batches[0]
        metas = metas_batches[0]
        dists = dist_batches[0]

        n = min(len(ids), len(docs), len(metas), len(dists))
        hits: list[dict] = []
        for i in range(n):
            meta = metas[i] if isinstance(metas[i], dict) else {}
            hits.append(
                {
                    "id": ids[i],
                    "chunk_id": meta.get("chunk_id") or ids[i],
                    "text": docs[i],
                    "distance": dists[i],
                    "doc_id": meta.get("doc_id"),
                    "document_id": meta.get("document_id"),
                    "workspace_id": meta.get("workspace_id"),
                    "chunk_index": meta.get("chunk_index"),
                }
            )

        return hits

    def delete_document(self, document_id: int) -> None:
        self._collection.delete(where={"document_id": document_id})

    def delete_workspace(self, workspace_id: int) -> None:
        self._collection.delete(where={"workspace_id": workspace_id})

    def count(self) -> int:
        return self._collection.count()
