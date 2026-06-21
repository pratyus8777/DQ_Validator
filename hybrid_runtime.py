"""
Hybrid Runtime - Unified entry point for any deployment mode
Dispatches to appropriate data sources and storage backends
"""

import logging
from typing import Dict, Any, Optional
import yaml
from enum import Enum

logger = logging.getLogger(__name__)


class DeploymentMode(str, Enum):
    LOCAL = "local"
    HYBRID = "hybrid"
    CLOUD = "cloud"


class RuntimeConfig:
    """Parsed and validated runtime configuration."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict
        self.mode = DeploymentMode(config_dict.get("mode", "local"))
        
        # Input configuration
        self.input_config = config_dict.get("input", config_dict.get("paths", {}))
        
        # LLM configuration
        self.llm_config = config_dict.get("llm", {})
        
        # Memory/learning configuration
        self.memory_config = config_dict.get("memory", config_dict.get("learning", {}))
        
        # Output configuration
        self.output_config = config_dict.get("output", {})
        if not self.output_config:
            self.output_config["type"] = "local"
            self.output_config["location"] = config_dict.get("output_dir", "output/")
        
        # Thresholds
        self.thresholds = config_dict.get("thresholds", {})
        
        # Processing options
        self.processing = config_dict.get("processing", {})
    
    def validate(self) -> bool:
        """Validate configuration."""
        if self.mode not in DeploymentMode:
            raise ValueError(f"Invalid mode: {self.mode}")
        
        if self.mode in [DeploymentMode.LOCAL, DeploymentMode.HYBRID]:
            required_inputs = ["sample_data", "dq_rules", "cleansing_rules", "kpis"]
            for key in required_inputs:
                if key not in self.input_config:
                    raise ValueError(f"Missing input: {key}")
        
        if "remediation_trigger_pct" not in self.thresholds:
            self.thresholds["remediation_trigger_pct"] = 0.05
        
        logger.info(f"Configuration validated (mode: {self.mode.value})")
        return True


class DataSourceFactory:
    """Factory for creating appropriate data sources."""
    
    @staticmethod
    def create_source(config: RuntimeConfig):
        """Create data source based on configuration."""
        input_type = config.input_config.get("type", "local")
        
        if input_type == "local":
            from data_io.local_source import LocalDataSource
            return LocalDataSource(config.input_config)
        
        elif input_type == "s3":
            from data_io.s3_source import S3DataSource
            return S3DataSource(config.input_config)
        
        else:
            raise ValueError(f"Unsupported input type: {input_type}")


class StorageFactory:
    """Factory for creating appropriate storage backends."""
    
    @staticmethod
    def create_learning_store(config: RuntimeConfig):
        """Create learning store based on configuration."""
        memory_type = config.memory_config.get("type", "local")
        
        if memory_type == "local":
            from data_io.local_store import LocalLearningStore
            return LocalLearningStore(
                config.memory_config.get("location", "output/learning_memory.json")
            )
        
        elif memory_type == "neondb":
            from data_io.neondb_store import NeonDBLearningStore
            return NeonDBLearningStore(
                config.memory_config.get("connection_string")
            )
        
        return None
    
    @staticmethod
    def create_output_store(config: RuntimeConfig):
        """Create output storage based on configuration."""
        output_type = config.output_config.get("type", "local")
        
        if output_type == "local":
            return LocalOutputStore(config.output_config.get("location", "output/"))
        
        elif output_type == "s3":
            return S3OutputStore(config.output_config)
        
        return LocalOutputStore("output/")


class LocalOutputStore:
    """Store outputs locally."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        import os
        os.makedirs(output_dir, exist_ok=True)
    
    def write_csv(self, filename: str, df) -> None:
        """Write DataFrame to CSV."""
        import os
        path = os.path.join(self.output_dir, filename)
        df.to_csv(path, index=False)
        logger.info(f"Wrote output: {path}")
    
    def write_json(self, filename: str, data: Dict) -> None:
        """Write JSON data."""
        import json
        import os
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Wrote output: {path}")


class S3OutputStore:
    """Store outputs to S3."""
    
    def __init__(self, config: Dict[str, Any]):
        self.bucket = config.get("bucket")
        self.prefix = config.get("prefix", "outputs/")
        try:
            import boto3
            self.s3 = boto3.client('s3')
        except ImportError:
            logger.warning("boto3 not installed. Install with: pip install boto3")
            self.s3 = None
    
    def write_csv(self, filename: str, df) -> None:
        """Write DataFrame to S3."""
        if not self.s3:
            logger.warning("S3 client not available")
            return
        
        csv_buffer = df.to_csv(index=False)
        key = f"{self.prefix}{filename}"
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=csv_buffer.encode('utf-8')
        )
        logger.info(f"Wrote to S3: s3://{self.bucket}/{key}")
    
    def write_json(self, filename: str, data: Dict) -> None:
        """Write JSON to S3."""
        if not self.s3:
            logger.warning("S3 client not available")
            return
        
        import json
        json_str = json.dumps(data, indent=2)
        key = f"{self.prefix}{filename}"
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json_str.encode('utf-8')
        )
        logger.info(f"Wrote to S3: s3://{self.bucket}/{key}")


class HybridRuntime:
    """Unified runtime that works across all deployment modes."""
    
    def __init__(self, config_path: str):
        # Load and validate configuration
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        self.config = RuntimeConfig(config_dict)
        self.config.validate()
        
        # Create data sources and stores
        self.data_source = DataSourceFactory.create_source(self.config)
        self.learning_store = StorageFactory.create_learning_store(self.config)
        self.output_store = StorageFactory.create_output_store(self.config)
        
        logger.info(f"Hybrid runtime initialized (mode: {self.config.mode.value})")
    
    def get_data_source(self):
        """Get configured data source."""
        return self.data_source
    
    def get_learning_store(self):
        """Get configured learning store."""
        return self.learning_store
    
    def get_output_store(self):
        """Get configured output store."""
        return self.output_store
    
    def get_config(self) -> RuntimeConfig:
        """Get runtime configuration."""
        return self.config


def load_hybrid_runtime(config_path: str) -> HybridRuntime:
    """Load and initialize hybrid runtime."""
    return HybridRuntime(config_path)
