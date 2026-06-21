from dashboard.charts import bar_chart


class PostHITLDashboard:
    """
    Generates dashboard after human approval.
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def generate(self, improvement_results: dict):
        before = improvement_results["before"]
        after = improvement_results["after"]

        dimensions = []
        before_counts = []
        after_counts = []

        for b, a in zip(before, after):
            dimensions.append(b["dimension"])
            before_counts.append(
                sum(v["failed_count"] for v in b["violations"])
            )
            after_counts.append(
                sum(v["failed_count"] for v in a["violations"])
            )

        bar_chart(
            labels=dimensions,
            values=before_counts,
            title="DQ Issues Before HITL",
            xlabel="Dimension",
            ylabel="Issue Count",
            output_path=f"{self.output_dir}/DQ_Issues_Before.png"
        )

        bar_chart(
            labels=dimensions,
            values=after_counts,
            title="DQ Issues After HITL",
            xlabel="Dimension",
            ylabel="Issue Count",
            output_path=f"{self.output_dir}/DQ_Issues_After.png"
        )
