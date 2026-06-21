from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any


class DataSource(ABC):
    """
    Abstract interface for all data access.
    Fully dynamic: supports local, S3, NeonDB with zero agent changes.
    """

    @abstractmethod
    def read_sample_data(self) -> pd.DataFrame:
        """Read main data for quality evaluation."""
        pass

    @abstractmethod
    def read_rules(self) -> pd.DataFrame:
        """Read rule definitions (unstructured CSV)."""
        pass

    @abstractmethod
    def read_cleansing_rules(self) -> pd.DataFrame:
        """Read cleansing/remediation rules."""
        pass

    @abstractmethod
    def read_kpis(self) -> pd.DataFrame:
        """Read KPI definitions."""
        pass


class DataSourceFactory:
    """Factory for creating appropriate data source dynamically."""
    
    @staticmethod
    def create(
        source_type: str,
        config: Dict[str, Any]
    ) -> DataSource:
        """
        Create data source based on type and config.
        
        Args:
            source_type: 'local', 's3', 'neondb', 'hybrid'
            config: Source-specific configuration dict
        
        Returns:
            DataSource instance
        
        Raises:
            ValueError: If source type not recognized
        """
        source_type = source_type.lower().strip()
        
        if source_type == "local":
            from data_io.local_source import LocalDataSource
            return LocalDataSource(config.get("paths", {}))
        
        elif source_type == "s3":
            from data_io.s3_source import S3DataSource
            return S3DataSource(
                bucket=config.get("bucket"),
                region=config.get("region", "us-east-1"),
                prefix=config.get("prefix", "")
            )
        
        elif source_type == "neondb":
            try:
                from data_io.neondb_store import NeonDBDataSource
                return NeonDBDataSource(
                    connection_string=config.get("connection_string")
                )
            except ImportError:
                raise ValueError("NeonDB support not installed (psycopg2 required)")
        
        elif source_type == "hybrid":
            # Hybrid: try local first, fallback to S3
            from data_io.local_source import LocalDataSource
            from data_io.s3_source import S3DataSource
            
            try:
                return LocalDataSource(config.get("paths", {}))
            except Exception as e:
                print(f"Local source failed ({e}), falling back to S3...")
                return S3DataSource(
                    bucket=config.get("bucket"),
                    region=config.get("region", "us-east-1"),
                    prefix=config.get("prefix", "")
                )
        
        else:
            raise ValueError(
                f"Unknown source type: {source_type}. "
                f"Supported: local, s3, neondb, hybrid"
            )
