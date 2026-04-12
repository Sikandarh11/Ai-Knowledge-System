import os

from backend.rag.retriever import Retriever

PROMPT_TEMPLATE = """You are an assistant. Use the context below to answer.

Context:
{context}

Conversation:
{conversation}

Question:
{query}

Answer:"""


class RAGService:
    def __init__(self, retriever: Retriever | None = None):
        self._retriever = retriever or Retriever()
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._openai_client = None

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=self._api_key)
        return self._openai_client

    @property
    def model_name(self) -> str:
        return self._model_name

    def retrieve(self, query: str, workspace_id: int | None = None) -> list[dict]:
        return self._retriever.retrieve(query, workspace_id=workspace_id)

    def build_prompt(self, query: str, documents: list[dict], conversation: str | None = None) -> str:
        if documents:
            context_lines = [
                f"[{i + 1}] (doc_id={hit['document_id']}, workspace_id={hit['workspace_id']})\n{hit['text']}"
                for i, hit in enumerate(documents)
            ]
            context = "\n\n".join(context_lines)
        else:
            context = "No relevant documents found."

        conversation_block = conversation.strip() if conversation and conversation.strip() else "No prior conversation."
        return PROMPT_TEMPLATE.format(context=context, conversation=conversation_block, query=query)

    def generate_answer(self, prompt: str) -> str:
        if not self._api_key:
            return self._fallback_answer(prompt)

        try:
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            return self._fallback_answer(prompt, error=str(exc))

    def run(
        self,
        query: str,
        *,
        workspace_id: int | None = None,
        conversation: str | None = None,
    ) -> dict:
        hits = self.retrieve(query, workspace_id=workspace_id)
        prompt = self.build_prompt(query, hits, conversation=conversation)
        answer = self.generate_answer(prompt)
        return {
            "query": query,
            "answer": answer,
            "sources": hits,
            "model_name": self.model_name,
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
