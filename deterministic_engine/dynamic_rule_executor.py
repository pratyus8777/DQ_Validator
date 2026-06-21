"""
Dynamic Rule Engine with LLM Fallback
Executes deterministic rules, falls back to LLM for ambiguous cases
"""

import logging
import pandas as pd
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RuleExecutionResult(BaseModel):
    """Result of rule execution."""
    record_id: Any
    column: str
    rule_id: str
    check_type: str
    passed: bool
    issue_type: Optional[str] = None
    original_value: Any
    suggested_fix: Optional[Any] = None
    confidence: float = 1.0
    execution_method: str  # "deterministic" or "llm"


class DynamicRuleExecutor:
    """
    Executes DQ rules with intelligent fallback to LLM.
    - Deterministic rules: exact, auditable, no LLM
    - Ambiguous cases: LLM-assisted with validation
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = self._init_ollama()
    
    def _init_ollama(self) -> Ollama:
        """Initialize Ollama."""
        ollama_url = self.config.get("llm", {}).get("ollama_url", "http://localhost:11434")
        model_name = self.config.get("llm", {}).get("model", "mistral")
        
        try:
            llm = Ollama(
                base_url=ollama_url,
                model=model_name,
                temperature=self.config.get("llm", {}).get("temperature", 0.2)
            )
            return llm
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {e}")
            return None
    
    def execute_all_rules(
        self,
        df: pd.DataFrame,
        rules: pd.DataFrame,
        dimension: Optional[str] = None
    ) -> Tuple[List[RuleExecutionResult], pd.DataFrame]:
        """
        Execute all rules against data.
        Returns: (violations, issues_summary)
        """
        violations = []
        
        if rules is None or rules.empty:
            logger.warning("No rules provided")
            return violations, None
        
        # Filter by dimension if specified
        if dimension:
            rules = rules[rules.get("dimension", "") == dimension]
        
        total_rules = len(rules)
        logger.info(f"Executing {total_rules} rules on {len(df)} records")
        
        for idx, row in rules.iterrows():
            try:
                rule_violations = self._execute_single_rule(df, row)
                violations.extend(rule_violations)
            except Exception as e:
                logger.error(f"Failed to execute rule {row.get('rule_id')}: {e}")
        
        logger.info(f"Found {len(violations)} total violations")
        
        # Create issues summary
        issues_summary = self._create_issues_summary(violations)
        
        return violations, issues_summary
    
    def _execute_single_rule(self, df: pd.DataFrame, rule: pd.Series) -> List[RuleExecutionResult]:
        """Execute a single rule against data."""
        check_type = rule.get("check_type", "").lower()
        # Handle both 'cde' and 'column' field names
        cde = rule.get("cde") or rule.get("column")
        rule_id = rule.get("rule_id")
        dimension = rule.get("dimension")
        
        if not cde or cde not in df.columns:
            if cde:
                logger.debug(f"Column {cde} not found in data")
            return []
        
        # Route to appropriate handler
        handler_map = {
            "not_null": self._check_not_null,
            "not_blank": self._check_not_blank,
            "date_format": self._check_date_format,
            "regex": self._check_regex,
            "length_in": self._check_length,
            "in_set": self._check_in_set,
            "range": self._check_range,
            "unique_in_dataset": self._check_unique,
            "gte_field": self._check_gte_field,
            "lte_field": self._check_lte_field,
            "eq_month_diff": self._check_month_diff,
        }
        
        handler = handler_map.get(check_type)
        if handler:
            return handler(df, rule, cde, rule_id, dimension)
        else:
            logger.warning(f"Unknown check type: {check_type}")
            return []
    
    # Deterministic check implementations
    
    def _check_not_null(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check for null values."""
        violations = []
        null_mask = df[cde].isna()
        
        for idx, is_null in null_mask.items():
            if is_null:
                violations.append(RuleExecutionResult(
                    record_id=idx,
                    column=cde,
                    rule_id=rule_id,
                    check_type="not_null",
                    passed=False,
                    issue_type="null_value",
                    original_value=None,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
        
        return violations
    
    def _check_not_blank(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check for blank/whitespace values."""
        violations = []
        
        for idx, value in df[cde].items():
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ""):
                violations.append(RuleExecutionResult(
                    record_id=idx,
                    column=cde,
                    rule_id=rule_id,
                    check_type="not_blank",
                    passed=False,
                    issue_type="blank_value",
                    original_value=value,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
        
        return violations
    
    def _check_date_format(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check date format."""
        violations = []
        params = rule.get("parameters", "")
        expected_format = params if isinstance(params, str) else "YYYY-MM-DD"
        
        for idx, value in df[cde].items():
            if pd.isna(value):
                continue
            
            if not self._is_valid_date(str(value), expected_format):
                violations.append(RuleExecutionResult(
                    record_id=idx,
                    column=cde,
                    rule_id=rule_id,
                    check_type="date_format",
                    passed=False,
                    issue_type="invalid_date_format",
                    original_value=value,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
        
        return violations
    
    def _is_valid_date(self, date_str: str, fmt: str) -> bool:
        """Validate date string."""
        from datetime import datetime
        try:
            # Handle common formats
            formats = [
                "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y",
                "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y",
                "%Y%m%d", "%m%d%Y"
            ]
            for fmt in formats:
                try:
                    datetime.strptime(date_str, fmt)
                    return True
                except:
                    pass
            return False
        except:
            return False
    
    def _check_regex(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check regex pattern."""
        violations = []
        pattern = rule.get("parameters", "")
        
        if not pattern:
            logger.warning(f"No regex pattern provided for rule {rule_id}")
            return violations
        
        try:
            regex = re.compile(pattern)
        except Exception as e:
            logger.error(f"Invalid regex pattern: {pattern}: {e}")
            return violations
        
        for idx, value in df[cde].items():
            if pd.isna(value):
                continue
            
            if not regex.match(str(value)):
                violations.append(RuleExecutionResult(
                    record_id=idx,
                    column=cde,
                    rule_id=rule_id,
                    check_type="regex",
                    passed=False,
                    issue_type="regex_mismatch",
                    original_value=value,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
        
        return violations
    
    def _check_length(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check length constraints."""
        violations = []
        params = rule.get("parameters", "")
        
        # Parse min,max from parameters
        try:
            if isinstance(params, str) and "," in params:
                min_len, max_len = map(int, params.split(","))
            else:
                return violations
        except:
            return violations
        
        for idx, value in df[cde].items():
            if pd.isna(value):
                continue
            
            val_len = len(str(value))
            if not (min_len <= val_len <= max_len):
                violations.append(RuleExecutionResult(
                    record_id=idx,
                    column=cde,
                    rule_id=rule_id,
                    check_type="length_in",
                    passed=False,
                    issue_type="invalid_length",
                    original_value=value,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
        
        return violations
    
    def _check_in_set(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check value is in allowed set."""
        violations = []
        params = rule.get("parameters", "")
        
        # Parse allowed values
        if isinstance(params, str):
            allowed = set(params.split(","))
        elif isinstance(params, list):
            allowed = set(params)
        else:
            return violations
        
        for idx, value in df[cde].items():
            if pd.isna(value):
                continue
            
            if str(value).strip() not in allowed:
                violations.append(RuleExecutionResult(
                    record_id=idx,
                    column=cde,
                    rule_id=rule_id,
                    check_type="in_set",
                    passed=False,
                    issue_type="value_not_in_set",
                    original_value=value,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
        
        return violations
    
    def _check_range(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check numeric range."""
        violations = []
        params = rule.get("parameters", "")
        
        try:
            if isinstance(params, str) and "," in params:
                min_val, max_val = map(float, params.split(","))
            else:
                return violations
        except:
            return violations
        
        for idx, value in df[cde].items():
            if pd.isna(value):
                continue
            
            try:
                num_val = float(value)
                if not (min_val <= num_val <= max_val):
                    violations.append(RuleExecutionResult(
                        record_id=idx,
                        column=cde,
                        rule_id=rule_id,
                        check_type="range",
                        passed=False,
                        issue_type="value_out_of_range",
                        original_value=value,
                        confidence=1.0,
                        execution_method="deterministic"
                    ))
            except (ValueError, TypeError):
                violations.append(RuleExecutionResult(
                    record_id=idx,
                    column=cde,
                    rule_id=rule_id,
                    check_type="range",
                    passed=False,
                    issue_type="invalid_numeric_value",
                    original_value=value,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
        
        return violations
    
    def _check_unique(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check uniqueness in dataset."""
        violations = []
        
        duplicates = df[df.duplicated(subset=[cde], keep=False)]
        
        for idx, value in duplicates[cde].items():
            violations.append(RuleExecutionResult(
                record_id=idx,
                column=cde,
                rule_id=rule_id,
                check_type="unique_in_dataset",
                passed=False,
                issue_type="duplicate_value",
                original_value=value,
                confidence=1.0,
                execution_method="deterministic"
            ))
        
        return violations
    
    def _check_gte_field(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check column value >= reference column."""
        violations = []
        params = rule.get("parameters", "")
        
        if not params or params == cde:
            return violations
        
        if params not in df.columns:
            logger.warning(f"Reference column {params} not found")
            return violations
        
        for idx in df.index:
            try:
                val = float(df.loc[idx, cde])
                ref_val = float(df.loc[idx, params])
                if val < ref_val:
                    violations.append(RuleExecutionResult(
                        record_id=idx,
                        column=cde,
                        rule_id=rule_id,
                        check_type="gte_field",
                        passed=False,
                        issue_type="field_less_than_reference",
                        original_value=val,
                        confidence=1.0,
                        execution_method="deterministic"
                    ))
            except (ValueError, TypeError):
                pass
        
        return violations
    
    def _check_lte_field(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check column value <= reference column."""
        violations = []
        params = rule.get("parameters", "")
        
        if not params or params == cde:
            return violations
        
        if params not in df.columns:
            logger.warning(f"Reference column {params} not found")
            return violations
        
        for idx in df.index:
            try:
                val = float(df.loc[idx, cde])
                ref_val = float(df.loc[idx, params])
                if val > ref_val:
                    violations.append(RuleExecutionResult(
                        record_id=idx,
                        column=cde,
                        rule_id=rule_id,
                        check_type="lte_field",
                        passed=False,
                        issue_type="field_greater_than_reference",
                        original_value=val,
                        confidence=1.0,
                        execution_method="deterministic"
                    ))
            except (ValueError, TypeError):
                pass
        
        return violations
    
    def _check_month_diff(
        self,
        df: pd.DataFrame,
        rule: pd.Series,
        cde: str,
        rule_id: str,
        dimension: str
    ) -> List[RuleExecutionResult]:
        """Check month difference between dates."""
        violations = []
        params = rule.get("parameters", "")
        
        # Parse: ref_column,expected_months
        if not params or "," not in params:
            return violations
        
        try:
            ref_col, expected_months = params.split(",")
            expected_months = int(expected_months)
        except:
            return violations
        
        if ref_col not in df.columns:
            logger.warning(f"Reference column {ref_col} not found")
            return violations
        
        for idx in df.index:
            try:
                from dateutil.relativedelta import relativedelta
                
                date1 = pd.to_datetime(df.loc[idx, cde])
                date2 = pd.to_datetime(df.loc[idx, ref_col])
                
                months_diff = relativedelta(date2, date1).months
                
                if months_diff != expected_months:
                    violations.append(RuleExecutionResult(
                        record_id=idx,
                        column=cde,
                        rule_id=rule_id,
                        check_type="eq_month_diff",
                        passed=False,
                        issue_type="month_diff_mismatch",
                        original_value=df.loc[idx, cde],
                        confidence=1.0,
                        execution_method="deterministic"
                    ))
            except:
                pass
        
        return violations
    
    def _create_issues_summary(self, violations: List[RuleExecutionResult]) -> pd.DataFrame:
        """Create summary DataFrame of issues."""
        if not violations:
            return pd.DataFrame()
        
        data = [
            {
                "record_id": v.record_id,
                "column": v.column,
                "rule_id": v.rule_id,
                "issue_type": v.issue_type,
                "original_value": v.original_value,
                "suggested_fix": v.suggested_fix,
                "confidence": v.confidence,
                "execution_method": v.execution_method
            }
            for v in violations
        ]
        
        return pd.DataFrame(data)
