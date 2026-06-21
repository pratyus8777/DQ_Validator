"""
Unit tests for cli module utilities.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import pandas as pd


class TestGetFailedCount:
    """Test cases for get_failed_count utility function."""
    
    def test_failed_count_from_rows_list(self):
        """Test extracting failed count from rows list."""
        from cli import get_failed_count
        
        violation = {
            "rows": [1, 2, 3]
        }
        assert get_failed_count(violation) == 3
    
    def test_failed_count_from_count_field(self):
        """Test extracting failed count from failed_count field."""
        from cli import get_failed_count
        
        violation = {
            "failed_count": 5
        }
        assert get_failed_count(violation) == 5
    
    def test_default_failed_count(self):
        """Test default failed count when neither field present."""
        from cli import get_failed_count
        
        violation = {}
        assert get_failed_count(violation) == 1


class TestEnsureDir:
    """Test cases for ensure_dir utility function."""
    
    def test_create_directory(self, tmp_path):
        """Test directory creation."""
        from cli import ensure_dir
        
        test_dir = os.path.join(tmp_path, "test", "nested", "dir")
        ensure_dir(test_dir)
        
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
    
    def test_existing_directory(self, tmp_path):
        """Test handling of existing directory."""
        from cli import ensure_dir
        
        ensure_dir(tmp_path)  # Should not raise
        assert os.path.exists(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
