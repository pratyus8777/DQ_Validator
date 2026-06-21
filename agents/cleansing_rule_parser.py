"""
Cleansing Rule Parser
Converts descriptive cleansing rules from CSV into actionable fix configurations.
Maps text descriptions to specific fix actions and parameters.
"""

import pandas as pd
import re
from typing import Dict, List, Any, Optional


class CleansingRuleParser:
    """
    Parses cleansing rules and generates actionable fix configurations.
    Handles both null-filling, standardization, and format fixes.
    """

    # Column name mappings from cleansing rules CSV
    REMEDIATION_COLUMNS = {
        "completeness": "Completeness Remediation",
        "validity": "Validity Remediation",
        "accuracy": "Accuracy Remediation",
        "consistency": "Consistency Remediation",
        "deduplication": "Deduplication Remediation",
        "timeliness": "Timeliness Remediation",
        "integrity": "Integrity Remediation",
        "reasonableness": "Reasonableness Remediation"
    }

    # Map rule CDE names to actual data column names
    CDE_TO_COLUMN_MAP = {
        "Policy Number": "Policy Number",
        "Policy Effective Date": "Policy Effective Date",
        "Policy Expiry Date": "Policy Expiry Date",
        "Policy Term Type": "Policy Term Type",
        "Policy Status": "Policy Status",
        "Insured Customer ID": "Customer ID",
        "Insured Name": "Customer Name",
        "Customer ID": "Customer ID",
        "Customer Name": "Customer Name",
        "Date of Birth / Incorporation Date": "Customer DOB",
        "National ID (PAN/SSN/Aadhaar)": "National ID",
        "Address (Risk/Insured)": "Address",
        "Contact Email": "Email",
        "Contact Phone": "Phone",
        "Product / Line of Business Code": "Line of Business",
        "Coverage ID": "Coverage ID",
        "Coverage Limit Amount": "Coverage Limit",
        "Coverage Deductible Amount": "Coverage Deductible",
        "Premium Amount": "Premium Amount",
        "Payment Plan": "Payment Plan",
        "Agent / Producer ID": "Agent ID",
        "Agent Commission %": "Agent Commission %",
        "Underwriter ID": "Underwriter ID",
        "Risk Object ID (Vehicle/Property)": "Risk Object ID",
        "Vehicle VIN / Property ID": "VIN/Property ID",
        "Risk Location GeoCode": "GeoCode",
        "Endorsement ID": "Endorsement ID",
        "Endorsement Effective Date": "Endorsement Effective Date",
        "Cancellation Effective Date": "Cancellation Effective Date",
        "Renewal Indicator": "Renewal Indicator",
        "Reinsurance Contract ID": "Reinsurance Contract ID",
        "Regulatory Reporting Flag": "Regulatory Reporting Flag",
    }
    
    # Also expose individual column mappings for direct lookups
    ACTUAL_COLUMNS = {
        "Policy Number", "Policy Effective Date", "Policy Expiry Date", 
        "Policy Term Type", "Policy Status", "Customer ID", "Customer Name", 
        "Customer DOB", "National ID", "Address", "Phone", "Email", 
        "Line of Business", "Coverage ID", "Coverage Limit", "Coverage Deductible", 
        "Premium Amount", "Payment Plan", "Agent ID", "Agent Commission %", 
        "Underwriter ID", "Risk Object ID", "VIN/Property ID", "GeoCode", 
        "Endorsement ID", "Endorsement Effective Date", "Cancellation Effective Date", 
        "Renewal Indicator", "Reinsurance Contract ID", "Regulatory Reporting Flag"
    }

    # Column types and their default fix strategies
    COLUMN_PATTERNS = {
        "Date": {"fix_action": "parse_date", "format": "auto"},
        "Email": {"fix_action": "validate_email", "format": None},
        "Phone": {"fix_action": "validate_phone", "format": None},
        "ID": {"fix_action": "standardize", "format": None},
        "Amount": {"fix_action": "numeric_standardize", "format": None},
        "Percentage": {"fix_action": "numeric_standardize", "format": None},
    }

    def __init__(self):
        self.parsed_rules = []

    def parse_cleansing_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert raw cleansing rules DataFrame to actionable fix configurations.
        
        Args:
            df: DataFrame with columns like 'S No', 'CDE', and remediation columns
            
        Returns:
            DataFrame with columns: cde, fix_action, fix_parameters, priority, remediation_type
        """
        results = []
        deduplication_added = False  # Track if we've added dedup once

        for idx, row in df.iterrows():
            cde = row.get("CDE") or row.get("cde")
            if pd.isna(cde):
                continue

            cde = str(cde).strip()
            
            # Map CDE to actual column name using lookup table
            actual_column = self.CDE_TO_COLUMN_MAP.get(cde, cde)
            
            # Skip if column doesn't exist in data (won't validate here, will validate during apply)
            if actual_column not in self.ACTUAL_COLUMNS:
                # Try exact match if not in mapping
                if cde not in self.ACTUAL_COLUMNS:
                    continue
                actual_column = cde

            # Parse each remediation type
            for rem_type, col_name in self.REMEDIATION_COLUMNS.items():
                if col_name not in df.columns:
                    continue

                remedy_text = row.get(col_name)
                if pd.isna(remedy_text) or str(remedy_text).strip() == "":
                    continue

                # Skip deduplication if already added (apply only once)
                if rem_type == "deduplication":
                    if deduplication_added:
                        continue
                    deduplication_added = True

                remedy_text = str(remedy_text).strip()

                # Generate fix action from remediation text
                fix_config = self._parse_remediation_text(
                    actual_column, rem_type, remedy_text
                )

                if fix_config:
                    fix_config["remediation_type"] = rem_type
                    fix_config["priority"] = self._get_priority(rem_type)
                    results.append(fix_config)

        if not results:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                "cde", "fix_action", "fix_parameters", 
                "priority", "remediation_type"
            ])

        return pd.DataFrame(results)

    def _parse_remediation_text(
        self, cde: str, rem_type: str, text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract fix action and parameters from remediation text.
        
        Args:
            cde: Column/Data Element name (actual column name)
            rem_type: Type of remediation (completeness, validity, etc)
            text: Full remediation text description
            
        Returns:
            Dict with fix_action and fix_parameters, or None
        """

        # COMPLETENESS: Handle null values
        if rem_type == "completeness":
            if "null" in text.lower():
                return {
                    "cde": cde,
                    "fix_action": "if_null_fill",
                    "fix_parameters": self._infer_default_value(cde)
                }

        # VALIDITY: Fix format/regex issues
        elif rem_type == "validity":
            if "format" in text.lower() or "regex" in text.lower():
                if self._is_email_column(cde):
                    return {
                        "cde": cde,
                        "fix_action": "validate_email",
                        "fix_parameters": None
                    }
                elif self._is_phone_column(cde):
                    return {
                        "cde": cde,
                        "fix_action": "validate_phone",
                        "fix_parameters": None
                    }
                elif self._is_date_column(cde):
                    return {
                        "cde": cde,
                        "fix_action": "parse_date",
                        "fix_parameters": "auto"
                    }

        # ACCURACY: Cross-check with trusted sources
        elif rem_type == "accuracy":
            # For now, flag for manual review
            return {
                "cde": cde,
                "fix_action": "flag_for_review",
                "fix_parameters": "accuracy_check"
            }

        # CONSISTENCY: Standardization
        elif rem_type == "consistency":
            if self._is_date_column(cde):
                return {
                    "cde": cde,
                    "fix_action": "parse_date",
                    "fix_parameters": "auto"
                }
            elif self._is_enum_column(cde):
                return {
                    "cde": cde,
                    "fix_action": "standardize",
                    "fix_parameters": None
                }

        # DEDUPLICATION
        elif rem_type == "deduplication":
            return {
                "cde": cde,
                "fix_action": "dedupe_keep_first",
                "fix_parameters": None
            }

        # TIMELINESS
        elif rem_type == "timeliness":
            if "delayed" in text.lower():
                return {
                    "cde": cde,
                    "fix_action": "flag_for_review",
                    "fix_parameters": "timeliness_check"
                }

        # INTEGRITY
        elif rem_type == "integrity":
            return {
                "cde": cde,
                "fix_action": "validate_referential",
                "fix_parameters": None
            }

        # REASONABLENESS
        elif rem_type == "reasonableness":
            if self._is_numeric_column(cde):
                return {
                    "cde": cde,
                    "fix_action": "validate_range",
                    "fix_parameters": None
                }

        return None

    def _is_date_column(self, cde: str) -> bool:
        """Check if column contains date data."""
        keywords = ["date", "effective", "expiry", "birth", "incorporation", "dob"]
        cde_lower = cde.lower()
        return any(kw in cde_lower for kw in keywords)

    def _is_email_column(self, cde: str) -> bool:
        """Check if column contains email data."""
        keywords = ["email"]
        cde_lower = cde.lower()
        return any(kw in cde_lower for kw in keywords)

    def _is_phone_column(self, cde: str) -> bool:
        """Check if column contains phone data."""
        keywords = ["phone", "telephone"]
        cde_lower = cde.lower()
        return any(kw in cde_lower for kw in keywords)

    def _is_numeric_column(self, cde: str) -> bool:
        """Check if column contains numeric data."""
        keywords = [
            "amount", "limit", "deductible", "premium", "commission", 
            "percent", "percentage", "commission %"
        ]
        cde_lower = cde.lower()
        return any(kw in cde_lower for kw in keywords)

    def _is_enum_column(self, cde: str) -> bool:
        """Check if column has enumerated values."""
        keywords = [
            "status", "type", "plan", "indicator", "flag", "business",
            "term", "lob"
        ]
        cde_lower = cde.lower()
        return any(kw in cde_lower for kw in keywords)

    def _infer_default_value(self, cde: str) -> Optional[str]:
        """
        Infer a reasonable default value for a column.
        """
        cde_lower = cde.lower()

        if "flag" in cde_lower or "indicator" in cde_lower:
            return "N"
        elif "status" in cde_lower:
            return "Unknown"
        elif any(x in cde_lower for x in ["id", "code"]):
            return "UNASSIGNED"
        elif "date" in cde_lower:
            return ""  # Leave empty or handle as special case
        else:
            return ""

    def _get_priority(self, rem_type: str) -> int:
        """
        Assign priority to fix types.
        Lower = executed first
        """
        priorities = {
            "completeness": 1,      # Fill nulls first
            "deduplication": 2,     # Remove duplicates
            "validity": 3,          # Fix format issues
            "consistency": 4,       # Standardize
            "accuracy": 5,          # Check accuracy
            "integrity": 6,         # Validate relationships
            "reasonableness": 7,    # Check ranges
            "timeliness": 8,        # Check timing
        }
        return priorities.get(rem_type, 99)

    @staticmethod
    def merge_with_data_schema(rules_df: pd.DataFrame, data_df: pd.DataFrame) -> pd.DataFrame:
        """
        Enrich cleansing rules with column type information from actual data.
        """
        for idx, row in rules_df.iterrows():
            cde = row["cde"]
            if cde not in data_df.columns:
                continue

            col_data = data_df[cde]

            # Detect column type from actual data
            if pd.api.types.is_datetime64_any_dtype(col_data):
                rules_df.at[idx, "detected_type"] = "datetime"
            elif pd.api.types.is_numeric_dtype(col_data):
                rules_df.at[idx, "detected_type"] = "numeric"
            else:
                rules_df.at[idx, "detected_type"] = "string"

        return rules_df
