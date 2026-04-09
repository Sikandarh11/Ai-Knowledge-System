class InsightAgent:
    """Produces compact insights from model outputs."""

    def summarize(self, answer: str) -> str:
        text = answer.strip()
        if len(text) <= 300:
            return text
        return text[:297] + "..."
