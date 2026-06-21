from agents.base_quality_agent import BaseQualityAgent


class AccuracyAgent(BaseQualityAgent):

    DIMENSION = "Accuracy"
    SUPPORTED_CHECKS = [
        "regex",
        "range",
        "gte_field",
        "lte_field",
        "eq_month_diff"
    ]
