from dashboard.charts import bar_chart


class PreHITLDashboard:
    """
    Generates dashboard before human approval.
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def generate(self, profiling_results: list):
        dimensions = []
        issue_counts = []

        for result in profiling_results:
            dimensions.append(result["dimension"])
            issue_counts.append(
                sum(v["failed_count"] for v in result["violations"])
            )

        bar_chart(
            labels=dimensions,
            values=issue_counts,
            title="DQ Issues by Dimension (Pre-HITL)",
            xlabel="Dimension",
            ylabel="Issue Count",
            output_path=f"{self.output_dir}/DQ_Dashboard_PRE_HITL.png"
        )
