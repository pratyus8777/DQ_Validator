class LearningApplicationAgent:
    """
    Applies prior learnings and suggests new ones.
    """

    def __init__(self, learning_store, llm_client=None):
        self.store = learning_store
        self.llm = llm_client

    def run(self, context: dict) -> dict:
        data = context["data"]

        # Apply stored corrections deterministically
        data = self.store.apply_corrections(data)

        suggestions = None
        if self.llm:
            prompt = "Detect recurring correction patterns."
            suggestions = self.llm.complete(prompt)

        return {
            "data": data,
            "learning_suggestions": suggestions
        }
