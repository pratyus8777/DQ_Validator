"""
Unit tests for config_validator module.
"""

import pytest
from config_validator import validate_config, ConfigurationError


class TestConfigValidation:
    """Test cases for configuration validation."""
    
    def test_valid_local_config(self):
        """Test validation passes for valid local configuration."""
        config = {
            "mode": "local",
            "paths": {
                "sample_data": "data/sample.csv",
                "dq_rules": "data/rules.csv",
                "cleansing_rules": "data/cleansing.csv",
                "kpis": "data/kpis.csv"
            },
            "thresholds": {
                "remediation_trigger_pct": 0.05
            },
            "output_dir": "output/",
            "llm": {
                "enabled": True,
                "model": "gpt-4.1-mini"
            }
        }
        assert validate_config(config) is True
    
    def test_missing_required_key(self):
        """Test validation fails when required key is missing."""
        config = {
            "mode": "local",
            "paths": {},
            # Missing "thresholds"
            "output_dir": "output/"
        }
        with pytest.raises(ConfigurationError):
            validate_config(config)
    
    def test_invalid_mode(self):
        """Test validation fails for invalid mode."""
        config = {
            "mode": "invalid_mode",
            "paths": {},
            "thresholds": {"remediation_trigger_pct": 0.05},
            "output_dir": "output/"
        }
        with pytest.raises(ConfigurationError):
            validate_config(config)
    
    def test_invalid_threshold_value(self):
        """Test validation fails for out-of-range threshold."""
        config = {
            "mode": "local",
            "paths": {
                "sample_data": "data/sample.csv",
                "dq_rules": "data/rules.csv",
                "cleansing_rules": "data/cleansing.csv",
                "kpis": "data/kpis.csv"
            },
            "thresholds": {
                "remediation_trigger_pct": 1.5  # Invalid: > 1
            },
            "output_dir": "output/"
        }
        with pytest.raises(ConfigurationError):
            validate_config(config)
    
    def test_llm_enabled_without_model(self):
        """Test validation fails when LLM enabled without model."""
        config = {
            "mode": "local",
            "paths": {
                "sample_data": "data/sample.csv",
                "dq_rules": "data/rules.csv",
                "cleansing_rules": "data/cleansing.csv",
                "kpis": "data/kpis.csv"
            },
            "thresholds": {
                "remediation_trigger_pct": 0.05
            },
            "output_dir": "output/",
            "llm": {
                "enabled": True
                # Missing "model"
            }
        }
        with pytest.raises(ConfigurationError):
            validate_config(config)
    
    def test_local_learning_without_path(self):
        """Test validation fails for local learning store without path."""
        config = {
            "mode": "local",
            "paths": {
                "sample_data": "data/sample.csv",
                "dq_rules": "data/rules.csv",
                "cleansing_rules": "data/cleansing.csv",
                "kpis": "data/kpis.csv"
            },
            "thresholds": {
                "remediation_trigger_pct": 0.05
            },
            "output_dir": "output/",
            "learning": {
                "type": "local"
                # Missing "path"
            }
        }
        with pytest.raises(ConfigurationError):
            validate_config(config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
