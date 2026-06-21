from agents.base_quality_agent import BaseQualityAgent
from rules_engine.dispatcher import run_check


class CompletenessAgent(BaseQualityAgent):

    DIMENSION = "Completeness"

    def supported_checks(self):
        return ["not_null", "not_blank"]

    def run_check(self, df, rule):
        return run_check(df, rule)
