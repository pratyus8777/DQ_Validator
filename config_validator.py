"""
Configuration validation and management for DQ_PE platform.
Ensures all required settings are present and valid.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required fields."""
    pass


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate DQ_PE configuration against requirements.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        True if valid
    
    Raises:
        ConfigurationError: If configuration is invalid
    """
    required_keys = ["mode", "paths", "thresholds", "output_dir"]
    
    # Check required top-level keys
    for key in required_keys:
        if key not in config:
            raise ConfigurationError(f"Missing required config key: {key}")
    
    # Validate mode
    valid_modes = ["local", "hybrid", "cloud"]
    if config["mode"] not in valid_modes:
        raise ConfigurationError(
            f"Invalid mode: {config['mode']}. Must be one of {valid_modes}"
        )
    
    # Validate paths for local/hybrid modes
    if config["mode"] in ["local", "hybrid"]:
        if "paths" not in config or not isinstance(config["paths"], dict):
            raise ConfigurationError("'paths' must be a dictionary for local/hybrid modes")
        
        required_paths = ["sample_data", "dq_rules", "cleansing_rules", "kpis"]
        for path_key in required_paths:
            if path_key not in config["paths"]:
                raise ConfigurationError(f"Missing required path: {path_key}")
    
    # Validate thresholds
    thresholds = config.get("thresholds", {})
    if "remediation_trigger_pct" not in thresholds:
        raise ConfigurationError("Missing threshold: remediation_trigger_pct")
    
    pct_value = thresholds["remediation_trigger_pct"]
    if not (0 <= pct_value <= 1):
        raise ConfigurationError(
            f"remediation_trigger_pct must be between 0 and 1, got {pct_value}"
        )
    
    # Validate LLM config if enabled
    llm_config = config.get("llm", {})
    if llm_config.get("enabled", False):
        if "model" not in llm_config:
            raise ConfigurationError("LLM enabled but no model specified")
    
    # Validate learning store config if present
    learning_config = config.get("learning", {})
    if learning_config:
        if "type" not in learning_config:
            raise ConfigurationError("Learning configuration missing 'type' field")
        
        valid_types = ["local", "neondb"]
        if learning_config["type"] not in valid_types:
            raise ConfigurationError(
                f"Invalid learning type: {learning_config['type']}. "
                f"Must be one of {valid_types}"
            )
        
        if learning_config["type"] == "local" and "path" not in learning_config:
            raise ConfigurationError("Local learning store requires 'path' field")
        
        if learning_config["type"] == "neondb" and "connection_string" not in learning_config:
            raise ConfigurationError("NeonDB learning store requires 'connection_string' field")
    
    logger.info(f"Configuration validated successfully (mode: {config['mode']})")
    return True


def validate_data_schema(df, required_columns: List[str]) -> bool:
    """
    Validate that a DataFrame has required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
    
    Returns:
        True if valid
    
    Raises:
        ConfigurationError: If required columns are missing
    """
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ConfigurationError(
            f"DataFrame missing required columns: {missing}"
        )
    return True
