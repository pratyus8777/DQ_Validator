import pandas as pd
from agents.base_quality_agent import BaseQualityAgent
from rules_engine.dispatcher import run_check


class ConsistencyAgent(BaseQualityAgent):
    """
    Checks cross-field and domain consistency.
    """

    DIMENSION = "Consistency"
    SUPPORTED_CHECKS = [
        "in_set",
        "length_in",
        "regex",
        "gte_field",
        "lte_field"
    ]

    def run_check(self, df: pd.DataFrame, rule):
        return run_check(df, rule)
