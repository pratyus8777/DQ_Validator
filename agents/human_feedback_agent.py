class HumanFeedbackAgent:
    """
    Captures human decisions (approve/reject/correct).
    """

    def run(self, context: dict) -> dict:
        # Placeholder: actual UI / input mechanism plugs here
        feedback = context.get("human_feedback", [])

        return {
            "feedback": feedback
        }
