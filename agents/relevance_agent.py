from agents.base_quality_agent import BaseQualityAgent


class RelevanceAgent(BaseQualityAgent):
    """
    Heuristic relevance checks (non-blocking).
    """

    DIMENSION = "Relevance"
    SUPPORTED_CHECKS = []

    def run(self, context: dict) -> dict:
        flags = []

        if self.llm:
            prompt = f"""
            Identify irrelevant or over-granular fields from:
            {list(context['data'].columns)}
            """
            response = self.llm.complete(prompt)

            if response:
                flags.append({
                    "dimension": self.DIMENSION,
                    "type": "heuristic",
                    "message": response
                })

        return {
            "dimension": self.DIMENSION,
            "violations": flags
        }
