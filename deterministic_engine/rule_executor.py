"""
Deterministic Rule Engine - Executes normalized rules without ML/LLM.
Pure code-based rule enforcement for auditability and compliance.
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Set
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class DeterministicCheckEngine:
    """Pure code-based rule violation detection."""
    
    def __init__(self):
        self.violations: List[Dict[str, Any]] = []
    
    def check_not_null(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check for null/NaN values."""
        violations = df[df[column].isnull()].copy()
        
        if len(violations) == 0:
            return []
        
        return [{
            "rule_id": rule_id,
            "check": "not_null",
            "column": column,
            "failed_rows": violations.index.tolist(),
            "failed_count": len(violations),
            "affected_values": violations[column].tolist()
        }]
    
    def check_not_blank(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check for blank strings."""
        violations = df[
            (df[column].astype(str).str.strip() == "") |
            (df[column].isnull())
        ].copy()
        
        if len(violations) == 0:
            return []
        
        return [{
            "rule_id": rule_id,
            "check": "not_blank",
            "column": column,
            "failed_rows": violations.index.tolist(),
            "failed_count": len(violations)
        }]
    
    def check_regex(
        self,
        df: pd.DataFrame,
        column: str,
        pattern: str,
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check column matches regex pattern."""
        try:
            compiled_pattern = re.compile(pattern)
            violations = df[
                ~df[column].astype(str).str.match(compiled_pattern, na=False)
            ].copy()
            
            if len(violations) == 0:
                return []
            
            return [{
                "rule_id": rule_id,
                "check": "regex",
                "column": column,
                "pattern": pattern,
                "failed_rows": violations.index.tolist(),
                "failed_count": len(violations),
                "affected_values": violations[column].tolist()[:10]  # Sample
            }]
        
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return []
    
    def check_range(
        self,
        df: pd.DataFrame,
        column: str,
        min_val: float = None,
        max_val: float = None,
        rule_id: str = None
    ) -> List[Dict[str, Any]]:
        """Check numeric range."""
        try:
            numeric_col = pd.to_numeric(df[column], errors="coerce")
            violations_mask = pd.Series([False] * len(df), index=df.index)
            
            if min_val is not None:
                violations_mask |= numeric_col < min_val
            if max_val is not None:
                violations_mask |= numeric_col > max_val
            
            violations = df[violations_mask].copy()
            
            if len(violations) == 0:
                return []
            
            return [{
                "rule_id": rule_id,
                "check": "range",
                "column": column,
                "min": min_val,
                "max": max_val,
                "failed_rows": violations.index.tolist(),
                "failed_count": len(violations),
                "affected_values": violations[column].tolist()[:10]
            }]
        
        except Exception as e:
            logger.error(f"Range check failed for {column}: {e}")
            return []
    
    def check_length(
        self,
        df: pd.DataFrame,
        column: str,
        min_len: int = None,
        max_len: int = None,
        rule_id: str = None
    ) -> List[Dict[str, Any]]:
        """Check string length."""
        violations_mask = pd.Series([False] * len(df), index=df.index)
        
        lengths = df[column].astype(str).str.len()
        
        if min_len is not None:
            violations_mask |= lengths < min_len
        if max_len is not None:
            violations_mask |= lengths > max_len
        
        violations = df[violations_mask].copy()
        
        if len(violations) == 0:
            return []
        
        return [{
            "rule_id": rule_id,
            "check": "length",
            "column": column,
            "min_length": min_len,
            "max_length": max_len,
            "failed_rows": violations.index.tolist(),
            "failed_count": len(violations)
        }]
    
    def check_unique(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check for duplicates."""
        duplicates = df[df.duplicated(subset=[column], keep=False)].copy()
        
        if len(duplicates) == 0:
            return []
        
        dup_values = duplicates[column].unique()
        
        return [{
            "rule_id": rule_id,
            "check": "unique",
            "column": column,
            "failed_rows": duplicates.index.tolist(),
            "failed_count": len(duplicates),
            "duplicate_values": dup_values.tolist()[:10]
        }]
    
    def check_unique_in_group(
        self,
        df: pd.DataFrame,
        column: str,
        group_by: List[str],
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check uniqueness within groups."""
        violations = []
        
        for group_name, group_df in df.groupby(group_by):
            if group_df.duplicated(subset=[column]).any():
                dup_indices = group_df[
                    group_df.duplicated(subset=[column], keep=False)
                ].index.tolist()
                violations.extend(dup_indices)
        
        if not violations:
            return []
        
        return [{
            "rule_id": rule_id,
            "check": "unique_in_group",
            "column": column,
            "group_by": group_by,
            "failed_rows": violations,
            "failed_count": len(violations)
        }]
    
    def check_equals_field(
        self,
        df: pd.DataFrame,
        column1: str,
        column2: str,
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check two columns are equal."""
        violations = df[df[column1] != df[column2]].copy()
        
        if len(violations) == 0:
            return []
        
        return [{
            "rule_id": rule_id,
            "check": "equals_field",
            "columns": [column1, column2],
            "failed_rows": violations.index.tolist(),
            "failed_count": len(violations)
        }]
    
    def check_date_format(
        self,
        df: pd.DataFrame,
        column: str,
        date_format: str,
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check date format."""
        try:
            parsed = pd.to_datetime(df[column], format=date_format, errors="coerce")
            violations = df[parsed.isnull() & df[column].notnull()].copy()
            
            if len(violations) == 0:
                return []
            
            return [{
                "rule_id": rule_id,
                "check": "date_format",
                "column": column,
                "expected_format": date_format,
                "failed_rows": violations.index.tolist(),
                "failed_count": len(violations),
                "affected_values": violations[column].tolist()[:10]
            }]
        
        except Exception as e:
            logger.error(f"Date format check failed for {column}: {e}")
            return []
    
    def check_numeric(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check column is numeric."""
        violations = df[
            (pd.to_numeric(df[column], errors="coerce").isnull()) &
            (df[column].notnull())
        ].copy()
        
        if len(violations) == 0:
            return []
        
        return [{
            "rule_id": rule_id,
            "check": "numeric",
            "column": column,
            "failed_rows": violations.index.tolist(),
            "failed_count": len(violations),
            "affected_values": violations[column].tolist()[:10]
        }]
    
    def check_enum(
        self,
        df: pd.DataFrame,
        column: str,
        allowed_values: List[str],
        rule_id: str
    ) -> List[Dict[str, Any]]:
        """Check column values are in allowed set."""
        violations = df[~df[column].isin(allowed_values)].copy()
        
        if len(violations) == 0:
            return []
        
        return [{
            "rule_id": rule_id,
            "check": "enum",
            "column": column,
            "allowed_values": allowed_values,
            "failed_rows": violations.index.tolist(),
            "failed_count": len(violations),
            "affected_values": violations[column].unique().tolist()
        }]
    
    def execute_rule(
        self,
        df: pd.DataFrame,
        rule: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute a single rule."""
        rule_id = rule.get("rule_id")
        check_type = rule.get("check_type")
        column = rule.get("column")
        params = rule.get("parameters", {})
        
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found in DataFrame")
            return []
        
        # Route to specific check function
        if check_type == "not_null":
            return self.check_not_null(df, column, rule_id)
        
        elif check_type == "not_blank":
            return self.check_not_blank(df, column, rule_id)
        
        elif check_type == "regex":
            return self.check_regex(df, column, params.get("pattern"), rule_id)
        
        elif check_type == "range":
            return self.check_range(
                df, column,
                min_val=params.get("min"),
                max_val=params.get("max"),
                rule_id=rule_id
            )
        
        elif check_type == "length":
            return self.check_length(
                df, column,
                min_len=params.get("min_length"),
                max_len=params.get("max_length"),
                rule_id=rule_id
            )
        
        elif check_type == "unique":
            return self.check_unique(df, column, rule_id)
        
        elif check_type == "unique_in_group":
            return self.check_unique_in_group(
                df, column,
                params.get("group_by", []),
                rule_id
            )
        
        elif check_type == "equals_field":
            return self.check_equals_field(
                df, column,
                params.get("other_column"),
                rule_id
            )
        
        elif check_type == "date_format":
            return self.check_date_format(
                df, column,
                params.get("format"),
                rule_id
            )
        
        elif check_type == "numeric":
            return self.check_numeric(df, column, rule_id)
        
        elif check_type == "enum":
            return self.check_enum(
                df, column,
                params.get("values", []),
                rule_id
            )
        
        else:
            logger.warning(f"Unknown check type: {check_type}")
            return []
    
    def execute_all_rules(
        self,
        df: pd.DataFrame,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute all rules on DataFrame."""
        all_violations = []
        rules_executed = 0
        rules_failed = 0
        
        for rule in rules:
            try:
                violations = self.execute_rule(df, rule)
                if violations:
                    all_violations.extend(violations)
                rules_executed += 1
            except Exception as e:
                logger.error(f"Rule execution failed for {rule.get('rule_id')}: {e}")
                rules_failed += 1
        
        return {
            "rules_executed": rules_executed,
            "rules_failed": rules_failed,
            "total_violations": len(all_violations),
            "violations": all_violations,
            "execution_time": datetime.utcnow().isoformat()
        }
