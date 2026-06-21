"""
Deterministic Fix Engine - Applies deterministic remediation.
Some fixes use LLM for unstructured data (email, phone, free text).
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DeterministicFixEngine:
    """Applies deterministic fixes to violations."""
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    def fix_if_null_fill(
        self,
        df: pd.DataFrame,
        column: str,
        value: Any,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fill null values with default."""
        df = df.copy()
        null_count = df[column].isnull().sum()
        
        df.loc[df[column].isnull(), column] = value
        
        return df, {
            "fix": "if_null_fill",
            "column": column,
            "value": value,
            "records_fixed": null_count,
            "rule_id": rule_id
        }
    
    def fix_standardize(
        self,
        df: pd.DataFrame,
        column: str,
        mapping: Dict[str, str],
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Standardize values using mapping."""
        df = df.copy()
        original = df[column].copy()
        
        for old_val, new_val in mapping.items():
            mask = df[column] == old_val
            df.loc[mask, column] = new_val
        
        records_fixed = (df[column] != original).sum()
        
        return df, {
            "fix": "standardize",
            "column": column,
            "mapping": mapping,
            "records_fixed": records_fixed,
            "rule_id": rule_id
        }
    
    def fix_parse_date(
        self,
        df: pd.DataFrame,
        column: str,
        date_format: str,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Parse and standardize dates."""
        df = df.copy()
        original = df[column].copy()
        
        try:
            parsed = pd.to_datetime(df[column], format=date_format, errors="coerce")
            df[column] = parsed
            
            records_fixed = (df[column] != original).sum()
            
            return df, {
                "fix": "parse_date",
                "column": column,
                "date_format": date_format,
                "records_fixed": records_fixed,
                "rule_id": rule_id
            }
        
        except Exception as e:
            logger.error(f"Date parsing failed: {e}")
            return df, {
                "fix": "parse_date",
                "column": column,
                "error": str(e),
                "rule_id": rule_id
            }
    
    def fix_dedupe_keep_first(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Remove duplicates, keep first occurrence."""
        df = df.copy()
        original_len = len(df)
        
        df = df.drop_duplicates(subset=[column], keep="first")
        
        records_removed = original_len - len(df)
        
        return df, {
            "fix": "dedupe_keep_first",
            "column": column,
            "records_removed": records_removed,
            "rule_id": rule_id
        }
    
    def fix_dedupe_keep_latest(
        self,
        df: pd.DataFrame,
        column: str,
        date_column: str,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Remove duplicates, keep most recent by date."""
        df = df.copy()
        original_len = len(df)
        
        df = df.sort_values(date_column, ascending=False)
        df = df.drop_duplicates(subset=[column], keep="first")
        
        records_removed = original_len - len(df)
        
        return df, {
            "fix": "dedupe_keep_latest",
            "column": column,
            "date_column": date_column,
            "records_removed": records_removed,
            "rule_id": rule_id
        }
    
    def fix_uppercase(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Convert to uppercase."""
        df = df.copy()
        original = df[column].copy()
        
        df[column] = df[column].astype(str).str.upper()
        
        records_fixed = (df[column] != original).sum()
        
        return df, {
            "fix": "uppercase",
            "column": column,
            "records_fixed": records_fixed,
            "rule_id": rule_id
        }
    
    def fix_trim_whitespace(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Trim leading/trailing whitespace."""
        df = df.copy()
        original = df[column].copy()
        
        df[column] = df[column].astype(str).str.strip()
        
        records_fixed = (df[column] != original).sum()
        
        return df, {
            "fix": "trim_whitespace",
            "column": column,
            "records_fixed": records_fixed,
            "rule_id": rule_id
        }
    
    def fix_replace_regex(
        self,
        df: pd.DataFrame,
        column: str,
        pattern: str,
        replacement: str,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Replace using regex."""
        df = df.copy()
        original = df[column].copy()
        
        try:
            df[column] = df[column].astype(str).str.replace(
                pattern, replacement, regex=True
            )
            
            records_fixed = (df[column] != original).sum()
            
            return df, {
                "fix": "replace_regex",
                "column": column,
                "pattern": pattern,
                "replacement": replacement,
                "records_fixed": records_fixed,
                "rule_id": rule_id
            }
        
        except Exception as e:
            logger.error(f"Regex replacement failed: {e}")
            return df, {
                "fix": "replace_regex",
                "column": column,
                "error": str(e),
                "rule_id": rule_id
            }
    
    def fix_llm_email(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Use LLM to fix malformed emails."""
        if not self.llm:
            logger.warning("LLM not available for email fixing")
            return df, {
                "fix": "llm_email",
                "column": column,
                "error": "LLM not available",
                "rule_id": rule_id
            }
        
        df = df.copy()
        original = df[column].copy()
        
        # Find invalid emails
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        invalid_mask = ~df[column].astype(str).str.match(email_pattern, na=True)
        
        invalid_emails = df.loc[invalid_mask, column].unique()
        
        # Fix using LLM
        email_fixes = {}
        for email in invalid_emails:
            if pd.isna(email):
                continue
            
            try:
                fixed = self._llm_correct_email(email)
                if fixed and fixed != email:
                    email_fixes[email] = fixed
            except Exception as e:
                logger.warning(f"Failed to fix email '{email}': {e}")
        
        # Apply fixes
        for old, new in email_fixes.items():
            df.loc[df[column] == old, column] = new
        
        records_fixed = (df[column] != original).sum()
        
        return df, {
            "fix": "llm_email",
            "column": column,
            "fixes_applied": email_fixes,
            "records_fixed": records_fixed,
            "rule_id": rule_id
        }
    
    def fix_llm_phone(
        self,
        df: pd.DataFrame,
        column: str,
        rule_id: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Use LLM to fix malformed phone numbers."""
        if not self.llm:
            logger.warning("LLM not available for phone fixing")
            return df, {
                "fix": "llm_phone",
                "column": column,
                "error": "LLM not available",
                "rule_id": rule_id
            }
        
        df = df.copy()
        original = df[column].copy()
        
        # Find invalid phones
        phone_pattern = r'^\+?1?\d{10,}$'
        invalid_mask = ~df[column].astype(str).str.match(phone_pattern, na=True)
        
        invalid_phones = df.loc[invalid_mask, column].unique()
        
        # Fix using LLM
        phone_fixes = {}
        for phone in invalid_phones:
            if pd.isna(phone):
                continue
            
            try:
                fixed = self._llm_correct_phone(phone)
                if fixed and fixed != phone:
                    phone_fixes[phone] = fixed
            except Exception as e:
                logger.warning(f"Failed to fix phone '{phone}': {e}")
        
        # Apply fixes
        for old, new in phone_fixes.items():
            df.loc[df[column] == old, column] = new
        
        records_fixed = (df[column] != original).sum()
        
        return df, {
            "fix": "llm_phone",
            "column": column,
            "fixes_applied": phone_fixes,
            "records_fixed": records_fixed,
            "rule_id": rule_id
        }
    
    def fix_reject_row(
        self,
        df: pd.DataFrame,
        rule_id: str,
        violation_rows: List[int]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Reject rows with violations."""
        df = df.copy()
        original_len = len(df)
        
        df = df.drop(violation_rows, errors="ignore")
        
        records_rejected = original_len - len(df)
        
        return df, {
            "fix": "reject_row",
            "records_rejected": records_rejected,
            "rule_id": rule_id
        }
    
    def fix_flag_for_review(
        self,
        df: pd.DataFrame,
        rule_id: str,
        violation_rows: List[int],
        reason: str = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Flag rows for human review."""
        df = df.copy()
        
        # Add/update review flag column
        if "_flagged_for_review" not in df.columns:
            df["_flagged_for_review"] = False
        
        df.loc[violation_rows, "_flagged_for_review"] = True
        
        if "_review_reason" not in df.columns:
            df["_review_reason"] = ""
        
        if reason:
            df.loc[violation_rows, "_review_reason"] = reason
        
        return df, {
            "fix": "flag_for_review",
            "records_flagged": len(violation_rows),
            "reason": reason,
            "rule_id": rule_id
        }
    
    def _llm_correct_email(self, email: str) -> Optional[str]:
        """Use LLM to correct email."""
        if not self.llm:
            return email
        
        prompt = f"""Fix this malformed email address to be valid.
        Input: {email}
        
        Output ONLY the corrected email address, nothing else."""
        
        try:
            corrected = self.llm.generate(
                model="mistral",
                prompt=prompt,
                max_tokens=100,
                temperature=0.0
            )
            return corrected.strip()
        except:
            return email
    
    def _llm_correct_phone(self, phone: str) -> Optional[str]:
        """Use LLM to correct phone number."""
        if not self.llm:
            return phone
        
        prompt = f"""Fix this malformed phone number to be valid (10+ digits).
        Input: {phone}
        
        Output ONLY the corrected phone number, nothing else."""
        
        try:
            corrected = self.llm.generate(
                model="mistral",
                prompt=prompt,
                max_tokens=50,
                temperature=0.0
            )
            return corrected.strip()
        except:
            return phone
    
    def apply_fix(
        self,
        df: pd.DataFrame,
        fix_config: Dict[str, Any],
        rule_id: str = None,
        violation_rows: List[int] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Apply a single fix configuration."""
        fix_type = fix_config.get("fix")
        
        try:
            if fix_type == "if_null_fill":
                return self.fix_if_null_fill(
                    df,
                    fix_config["column"],
                    fix_config.get("value"),
                    rule_id
                )
            
            elif fix_type == "standardize":
                return self.fix_standardize(
                    df,
                    fix_config["column"],
                    fix_config.get("mapping", {}),
                    rule_id
                )
            
            elif fix_type == "parse_date":
                return self.fix_parse_date(
                    df,
                    fix_config["column"],
                    fix_config.get("format"),
                    rule_id
                )
            
            elif fix_type == "dedupe_keep_first":
                return self.fix_dedupe_keep_first(
                    df,
                    fix_config["column"],
                    rule_id
                )
            
            elif fix_type == "dedupe_keep_latest":
                return self.fix_dedupe_keep_latest(
                    df,
                    fix_config["column"],
                    fix_config.get("date_column"),
                    rule_id
                )
            
            elif fix_type == "uppercase":
                return self.fix_uppercase(df, fix_config["column"], rule_id)
            
            elif fix_type == "trim":
                return self.fix_trim_whitespace(df, fix_config["column"], rule_id)
            
            elif fix_type == "replace_regex":
                return self.fix_replace_regex(
                    df,
                    fix_config["column"],
                    fix_config.get("pattern"),
                    fix_config.get("replacement"),
                    rule_id
                )
            
            elif fix_type == "llm_email":
                return self.fix_llm_email(df, fix_config["column"], rule_id)
            
            elif fix_type == "llm_phone":
                return self.fix_llm_phone(df, fix_config["column"], rule_id)
            
            elif fix_type == "reject":
                return self.fix_reject_row(df, rule_id, violation_rows or [])
            
            elif fix_type == "flag":
                return self.fix_flag_for_review(
                    df,
                    rule_id,
                    violation_rows or [],
                    fix_config.get("reason")
                )
            
            else:
                logger.warning(f"Unknown fix type: {fix_type}")
                return df, {"fix": fix_type, "error": "Unknown fix type"}
        
        except Exception as e:
            logger.error(f"Fix application failed for {fix_type}: {e}")
            return df, {"fix": fix_type, "error": str(e)}
