import boto3
import pandas as pd
import io
from data_io.data_source import DataSource


class S3DataSource(DataSource):
    """
    Reads inputs from Amazon S3.
    """

    def __init__(self, s3_config: dict):
        self.bucket = s3_config["bucket"]
        self.prefix = s3_config.get("prefix", "")
        self.client = boto3.client("s3")

    def _read_csv(self, key: str) -> pd.DataFrame:
        obj = self.client.get_object(
            Bucket=self.bucket,
            Key=f"{self.prefix}{key}"
        )
        return pd.read_csv(io.BytesIO(obj["Body"].read()))

    def read_sample_data(self) -> pd.DataFrame:
        try:
            from data_io.db_helpers import read_sample_policy_data
            return read_sample_policy_data()
        except Exception:
            return self._read_csv("Sample_Policy_Data.csv")

    def read_rules(self) -> pd.DataFrame:
        return self._read_csv("DQ_Rule_Repository-Policy.csv")

    def read_cleansing_rules(self) -> pd.DataFrame:
        try:
            from data_io.db_helpers import read_guidewire_cleansing_rules
            return read_guidewire_cleansing_rules()
        except Exception:
            return self._read_csv("Guidewire_Policy_DataCleansing_Rules.csv")

    def read_kpis(self) -> pd.DataFrame:
        return self._read_csv("DQ_Dashboard_KPIs.csv")
