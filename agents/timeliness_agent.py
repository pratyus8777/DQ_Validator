import pandas as pd
from agents.base_quality_agent import BaseQualityAgent
from rules_engine.dispatcher import run_check


class TimelinessAgent(BaseQualityAgent):
    """
    Checks data freshness, currency windows, SLA breaches.
    """

    DIMENSION = "Timeliness"
    SUPPORTED_CHECKS = [
        "date_format",
        "range",
        "lte_field",
        "gte_field"
    ]

    def run_check(self, df: pd.DataFrame, rule):
        return run_check(df, rule)
