import pandas as pd
from data_io.data_source import DataSource
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LocalDataSource(DataSource):
    """
    Reads inputs from local filesystem.
    Handles non-UTF8 CSVs safely.
    Supports dynamic file discovery and multiple encodings.
    """

    def __init__(self, paths: dict = None):
        # Provide sensible defaults for local testing when no paths supplied
        if paths is None:
            base = "data"
            paths = {
                "sample_data": f"{base}/Sample_Policy_Data.csv",
                "dq_rules": f"{base}/DQ_Rule_Repository-Policy.csv",
                "cleansing_rules": f"{base}/Guidewire_Policy_DataCleansing_Rules.csv",
                "kpis": f"{base}/DQ_Dashboard_KPIs.csv",
            }
        self.paths = paths

    def _read_csv(self, path: str) -> pd.DataFrame:
        """Read CSV with multiple encoding fallbacks."""
        try:
            # Try UTF-8 first (fast path)
            return pd.read_csv(path, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            try:
                # Fallback for Windows / Excel CSVs
                return pd.read_csv(path, encoding="latin1", low_memory=False)
            except:
                # Last resort
                return pd.read_csv(path, encoding="iso-8859-1", low_memory=False)

    def read_sample_data(self) -> pd.DataFrame:
        """Read main data for quality evaluation."""
        df = self._read_csv(self.paths["sample_data"])
        logger.info(f"✓ Loaded sample data: {len(df)} rows, {len(df.columns)} columns")
        return df

    def read_rules(self) -> pd.DataFrame:
        """Read DQ rules."""
        df = self._read_csv(self.paths["dq_rules"])
        logger.info(f"✓ Loaded DQ rules: {len(df)} rules")
        return df

    def read_cleansing_rules(self) -> pd.DataFrame:
        """Read cleansing rules."""
        df = self._read_csv(self.paths["cleansing_rules"])
        logger.info(f"✓ Loaded cleansing rules: {len(df)} rules")
        return df

    def read_kpis(self) -> pd.DataFrame:
        """Read KPI definitions."""
        df = self._read_csv(self.paths["kpis"])
        logger.info(f"✓ Loaded KPIs: {len(df)} KPIs")
        return df
    
    def list_available_csv_files(self, directory: str = "data") -> list:
        """List all CSV files in a directory for dynamic input selection."""
        data_dir = Path(directory)
        if data_dir.exists():
            csv_files = [f.name for f in data_dir.glob("*.csv")]
            logger.info(f"Found {len(csv_files)} CSV files in {directory}")
            return csv_files
        return []
