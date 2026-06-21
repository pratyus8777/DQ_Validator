class ThresholdGateAgent:
    """
    Decides whether remediation is allowed
    based on % of affected records.
    """

    def __init__(self, threshold_pct: float):
        self.threshold_pct = threshold_pct

    def run(self, context: dict) -> dict:
        total_records = context.get("total_records", 0)
        violations = context.get("violations", [])

        affected_rows = set()

        for v in violations:
            rows = v.get("rows")
            if isinstance(rows, list):
                affected_rows.update(rows)

        affected_count = len(affected_rows)

        remediation_allowed = (
            total_records > 0 and
            (affected_count / total_records) >= self.threshold_pct
        )

        return {
            "remediation_allowed": remediation_allowed,
            "affected_records": affected_count,
            "total_records": total_records,
            "threshold_pct": self.threshold_pct
        }
