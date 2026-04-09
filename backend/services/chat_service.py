from backend.rag.pipeline import RAGService


class ChatService:
    def __init__(self):
        self._rag = RAGService()

    def chat(self, query: str, history: list[dict] | None = None) -> dict:
        history = (history or [])[-6:]
        conversation_lines: list[str] = []
        total_chars = 0

        for msg in history:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = msg.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
                continue

            line = f"User: {content.strip()}" if role == "user" else f"Assistant: {content.strip()}"
            if total_chars + len(line) > 4000:
                break
            conversation_lines.append(line)
            total_chars += len(line)

        conversation_text = "\n".join(conversation_lines)
        if conversation_text:
            query_text = (
                "You are a helpful assistant.\n\n"
                "Conversation so far:\n"
                f"{conversation_text}\n\n"
                "Question:\n"
                f"{query}"
            )
        else:
            query_text = query

        return self._rag.run(query=query_text)
