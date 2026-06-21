class ReportingAgent:
    """
    Generates reports, KPIs, dashboards, summaries.
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def run(self, context: dict) -> dict:
        narrative = None

        if self.llm:
            prompt = f"""
            Create executive data quality summary:
            {context}
            """
            narrative = self.llm.complete(prompt)

        return {
            "llm_summary": narrative
        }
