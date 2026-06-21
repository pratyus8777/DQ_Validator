class HITLDashboardAgent:
    """
    Prepares human-review artifacts and explanations.
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def run(self, context: dict) -> dict:
        summary = None

        if self.llm:
            prompt = f"""
            Summarize proposed data quality fixes for business users:
            {context.get('improvement')}
            """
            summary = self.llm.complete(prompt)

        return {
            "human_summary": summary,
            "changes_preview": context.get("data")
        }
