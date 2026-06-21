"""
Configuration loader for hybrid DQ system.
Reads environment-specific YAML config and provides unified config interface.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / 'config'
DEFAULT_CONFIG = 'hybrid.yaml'


class ConfigManager:
    """Unified configuration manager for hybrid DQ system."""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Load config if not already loaded."""
        if self._config is None:
            self.load_config()
    
    def load_config(self, config_file: Optional[str] = None):
        """
        Load YAML config file.
        Priority: explicit param > env var DQ_CONFIG > default hybrid.yaml
        """
        # Determine which config file to load
        if config_file:
            config_path = CONFIG_DIR / config_file
        else:
            env_config = os.getenv('DQ_CONFIG')
            if env_config:
                config_path = CONFIG_DIR / env_config
            else:
                config_path = CONFIG_DIR / DEFAULT_CONFIG
        
        if not config_path.exists():
            logger.warning(f"Config file {config_path} not found, using defaults")
            self._config = self._default_config()
            return
        
        try:
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"Loaded config from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config {config_path}: {e}")
            self._config = self._default_config()
    
    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """Default hybrid config if file not found."""
        return {
            'mode': 'hybrid',
            'database': {
                'primary': 'neon',
                'neon': {
                    'enabled': True,
                    'schema': 'dq_validator',
                    'sample_data_table': 'sample_policy_data',
                    'rules_table': 'guidewire_policy_data_cleansing_rules',
                },
                'fallback_on_error': True,
            },
            'paths': {
                'sample_data': 'data/Sample_Policy_Data.csv',
                'cleansing_rules': 'data/Guidewire_Policy_DataCleansing_Rules.csv',
            },
            'output': {
                'dir': 'output/',
                'cleansing_rules_json': 'output/cleansing_rules.json',
            },
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key (e.g., 'database.primary')."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire config section."""
        return self._config.get(section, {})
    
    def is_db_enabled(self) -> bool:
        """Check if Neon DB is enabled."""
        return self.get('database.neon.enabled', False)
    
    def should_fallback(self) -> bool:
        """Check if fallback to local files is enabled."""
        return self.get('database.fallback_on_error', True)
    
    def get_db_schema(self) -> str:
        """Get Neon DB schema name."""
        return self.get('database.neon.schema', 'dq_validator')
    
    def get_db_tables(self) -> Dict[str, str]:
        """Get mapping of data types to table names."""
        return {
            'sample_data': self.get('database.neon.sample_data_table', 'sample_policy_data'),
            'rules': self.get('database.neon.rules_table', 'guidewire_policy_data_cleansing_rules'),
        }
    
    def get_local_paths(self) -> Dict[str, str]:
        """Get local file paths for fallback."""
        return self.get('paths', {})
    
    def get_output_dir(self) -> str:
        """Get output directory."""
        return self.get('output.dir', 'output/')
    
    def get_mode(self) -> str:
        """Get config mode (local, hybrid, cloud)."""
        return self.get('mode', 'hybrid')
    
    def __repr__(self) -> str:
        return f"ConfigManager(mode={self.get_mode()}, db_enabled={self.is_db_enabled()})"


# Singleton instance
config = ConfigManager()


def get_config() -> ConfigManager:
    """Get global config instance."""
    return config
