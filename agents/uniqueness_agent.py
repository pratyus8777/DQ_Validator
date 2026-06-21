import pandas as pd
from agents.base_quality_agent import BaseQualityAgent
from rules_engine.dispatcher import run_check


class UniquenessAgent(BaseQualityAgent):
    """
    Detects duplicate and composite-duplicate records.
    """

    DIMENSION = "Uniqueness"
    SUPPORTED_CHECKS = [
        "unique_in_dataset"
    ]

    def run_check(self, df: pd.DataFrame, rule):
        return run_check(df, rule)
