class RouterAgent:
    """Routes tasks to specialized agents based on intent."""

    def route(self, intent: str) -> str:
        if "schedule" in intent.lower() or "calendar" in intent.lower():
            return "scheduling_agent"
        if "email" in intent.lower() or "mail" in intent.lower():
            return "email_agent"
        if "insight" in intent.lower() or "summary" in intent.lower():
            return "insight_agent"
        return "reasoning_agent"
