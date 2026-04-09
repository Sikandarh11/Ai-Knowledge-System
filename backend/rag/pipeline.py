import os

from backend.rag.retriever import Retriever

PROMPT_TEMPLATE = """You are an assistant. Use the context below to answer.

Context:
{context}

Question:
{query}

Answer:"""


class RAGService:
    def __init__(self, retriever: Retriever | None = None):
        self._retriever = retriever or Retriever()
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._openai_client = None

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=self._api_key)
        return self._openai_client

    def retrieve(self, query: str) -> list[dict]:
        return self._retriever.retrieve(query)

    def build_prompt(self, query: str, documents: list[dict]) -> str:
        if documents:
            context_lines = [
                f"[{i + 1}] (doc_id={hit['document_id']}, workspace_id={hit['workspace_id']})\n{hit['text']}"
                for i, hit in enumerate(documents)
            ]
            context = "\n\n".join(context_lines)
        else:
            context = "No relevant documents found."

        return PROMPT_TEMPLATE.format(context=context, query=query)

    def generate_answer(self, prompt: str) -> str:
        if not self._api_key:
            return self._fallback_answer(prompt)

        try:
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            return self._fallback_answer(prompt, error=str(exc))

    def run(self, query: str) -> dict:
        hits = self.retrieve(query)
        prompt = self.build_prompt(query, hits)
        answer = self.generate_answer(prompt)
        return {
            "query": query,
            "answer": answer,
            "sources": hits,
            "used_llm": bool(self._api_key),
        }

    @staticmethod
    def _fallback_answer(prompt: str, error: str | None = None) -> str:
        header = f"[LLM unavailable{f': {error}' if error else ''}] "
        try:
            context_block = prompt.split("Context:\n")[1].split("\nQuestion:")[0].strip()
            return header + context_block
        except IndexError:
            return header + prompt
