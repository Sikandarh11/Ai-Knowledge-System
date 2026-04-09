class ReasoningAgent:
    """Applies lightweight reasoning over retrieved context."""

    def reason(self, query: str, context: list[dict]) -> dict:
        return {
            "query": query,
            "context_count": len(context),
            "context": context,
        }
