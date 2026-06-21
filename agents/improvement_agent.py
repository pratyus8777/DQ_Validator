class ImprovementAgent:
    """
    Measures DQ improvement using row-aware profiling.
    """

    def __init__(self, profiling_orchestrator, llm_client=None):
        self.profiler = profiling_orchestrator
        self.llm = llm_client

    def run(self, context: dict) -> dict:
        before_results = context["profiling_results"]

        after_results = self.profiler.run({
            "data": context["data"],
            "dq_rules": context["dq_rules"]
        })["profiling_results"]

        return {
            "before": before_results,
            "after": after_results
        }
