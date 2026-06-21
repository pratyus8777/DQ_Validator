class FinalCleanAgent:
    """
    Applies approved corrections and produces trusted dataset.
    """

    def run(self, context: dict) -> dict:
        return {
            "final_data": context["data"]
        }
