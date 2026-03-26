import os
from backend.embeddings import EmbeddingService
from backend.vector_store import VectorStore


PROMPT_TEMPLATE = """You are an assistant. Use the context below to answer.

Context:
{context}

Question:
{query}

Answer:"""


class RAGService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        n_results: int = 5,
    ):
        self._embedder = embedding_service or EmbeddingService()
        self._store    = vector_store or VectorStore()
        self._n        = n_results
        self._api_key  = os.getenv("OPENAI_API_KEY")

        # Lazy-loaded OpenAI client
        self._openai_client = None

    # ── Private loader ─────────────────────────────────────────────────────────

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self._api_key)
        return self._openai_client

    # ── Pipeline steps ─────────────────────────────────────────────────────────

    def retrieve(self, query: str) -> list[dict]:
        """
        Step 1 + 2: Embed the query, then fetch top-n matching chunks.

        Returns a list of hit dicts from VectorStore.query().
        """
        query_embedding = self._embedder.embed_text(query)
        return self._store.query(query_embedding, n_results=self._n)

    def build_prompt(self, query: str, documents: list[dict]) -> str:
        """
        Step 3: Combine retrieved chunks into a single numbered context block,
        then render the prompt template.
        """
        if documents:
            context_lines = [
                f"[{i + 1}] (doc_id={hit['document_id']}, "
                f"workspace_id={hit['workspace_id']})\n{hit['text']}"
                for i, hit in enumerate(documents)
            ]
            context = "\n\n".join(context_lines)
        else:
            context = "No relevant documents found."

        return PROMPT_TEMPLATE.format(context=context, query=query)

    def generate_answer(self, prompt: str) -> str:
        """
        Step 4: Send the prompt to gpt-4o-mini.
        Falls back to returning the raw prompt context if OpenAI is unavailable.
        """
        if not self._api_key:
            return self._fallback_answer(prompt)

        try:
            client   = self._get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()

        except Exception as exc:
            return self._fallback_answer(prompt, error=str(exc))

    # ── Full pipeline ──────────────────────────────────────────────────────────

    def run(self, query: str) -> dict:
        """
        Execute the full RAG pipeline.

        Returns:
            {
                "query":     str,
                "answer":    str,
                "sources":   list[dict],   # hits returned by vector store
                "used_llm":  bool,
            }
        """
        hits   = self.retrieve(query)
        prompt = self.build_prompt(query, hits)
        answer = self.generate_answer(prompt)

        return {
            "query":    query,
            "answer":   answer,
            "sources":  hits,
            "used_llm": bool(self._api_key),
        }

    # ── Fallback ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_answer(prompt: str, error: str | None = None) -> str:
        """
        Return the context block extracted from the prompt so the caller
        still gets something useful when no LLM is available.
        """
        header = f"[LLM unavailable{f': {error}' if error else ''}] "
        # Extract just the context section for a cleaner fallback response
        try:
            context_block = prompt.split("Context:\n")[1].split("\nQuestion:")[0].strip()
            return header + context_block
        except IndexError:
            return header + prompt
'''
---

**Full pipeline at a glance:**
```
run(query)
    │
    ├─ 1. retrieve(query)
    │       ├─ EmbeddingService.embed_text(query) → list[float]
    │       └─ VectorStore.query(embedding)       → list[dict] (hits)
    │
    ├─ 2. build_prompt(query, hits)
    │       └─ numbered context block + PROMPT_TEMPLATE → str
    │
    ├─ 3. generate_answer(prompt)
    │       ├─ [OpenAI available] gpt-4o-mini chat completion → str
    │       └─ [fallback]         return context block as-is  → str
    │
    └─ 4. return { query, answer, sources, used_llm }
```

**Key design decisions:**

- **Dependency injection** — `EmbeddingService` and `VectorStore` are passed in (or defaulted), making the class trivially testable with mocks.
- **Lazy OpenAI client** — same pattern as `EmbeddingService`; no import cost until the first LLM call.
- **Numbered context** — each chunk is prefixed with its index and metadata (`doc_id`, `workspace_id`) so the model can cite sources and you can trace answers back to rows.
- **Graceful fallback** — if `OPENAI_API_KEY` is absent *or* the API call throws, `_fallback_answer` extracts the context block from the prompt and returns it with a clear warning header, so `run()` never raises.
- **`temperature=0.2`** — low temperature for factual, context-grounded answers rather than creative generation.

**Add to `requirements.txt`:**
```
openai>=1.0.0'''