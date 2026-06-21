from agents.base_agent import BaseAgent
from rules_engine.dispatcher import run_check


class BaseQualityAgent(BaseAgent):
    """
    Base class for all DQ dimension agents.
    Guarantees row-aware violations.
    """

    DIMENSION = None
    SUPPORTED_CHECKS = []

    def run(self, context: dict) -> dict:
        df = context["data"]
        rules_df = context["dq_rules"]

        violations = []

        scoped_rules = rules_df[
            (rules_df["dimension"] == self.DIMENSION) &
            (rules_df["check_type"].isin(self.SUPPORTED_CHECKS))
        ]

        for _, rule in scoped_rules.iterrows():
            failed_df = run_check(df, rule)

            if not failed_df.empty:
                violations.append({
                    "rule_id": rule["rule_id"],
                    "dimension": self.DIMENSION,
                    "cde": rule["cde"],
                    "check_type": rule["check_type"],
                    "rows": failed_df.index.tolist(),  # 🔥 KEY FIX
                })

        return {
            "dimension": self.DIMENSION,
            "violations": violations
        }
