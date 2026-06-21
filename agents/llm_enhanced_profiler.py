"""
LLM-Enhanced Data Quality Profiler
Uses LLM to perform comprehensive violation detection and analysis
"""

import pandas as pd
import numpy as np
import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class LLMEnhancedProfiler:
    """
    Enhanced profiler using LLM for deeper violation analysis
    Detects semantic, pattern-based, and cross-field violations
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.violations = []
        self.violation_details = {}
    
    def analyze_comprehensive(self, df: pd.DataFrame, sample_size: int = 50) -> Dict[str, Any]:
        """
        Perform comprehensive analysis with LLM enhancement
        
        Args:
            df: DataFrame to analyze
            sample_size: Number of rows to sample for LLM analysis
        
        Returns:
            Comprehensive analysis report with all violations found
        """
        logger.info("Starting LLM-Enhanced Comprehensive Analysis...")
        
        self.violations = []
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "total_records": len(df),
            "total_columns": len(df.columns),
            "violations": {
                "completeness": [],
                "validity": [],
                "consistency": [],
                "uniqueness": [],
                "accuracy": [],
                "semantic": [],
            },
            "violation_count": 0,
            "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "affected_records": set(),
            "column_quality": {},
            "insights": []
        }
        
        # 1. Check Completeness (NULL/Empty values)
        logger.info("Analyzing Completeness (NULL/Empty values)...")
        self._analyze_completeness(df, analysis)
        
        # 2. Check Validity (format, range, type issues)
        logger.info("Analyzing Validity (format/range/type)...")
        self._analyze_validity(df, analysis)
        
        # 3. Check Uniqueness (duplicates)
        logger.info("Analyzing Uniqueness (duplicates)...")
        self._analyze_uniqueness(df, analysis)
        
        # 4. Check Consistency (cross-field logic)
        logger.info("Analyzing Consistency (cross-field logic)...")
        self._analyze_consistency(df, analysis)
        
        # 5. Check Accuracy (value range, business rules)
        logger.info("Analyzing Accuracy (value ranges/business rules)...")
        self._analyze_accuracy(df, analysis)
        
        # 6. LLM-based semantic analysis (if LLM available)
        if self.llm_client and self.llm_client.available:
            logger.info("Performing LLM-Enhanced Semantic Analysis...")
            self._analyze_semantic_with_llm(df, sample_size, analysis)
        
        # 7. Calculate column quality scores
        self._calculate_column_quality(df, analysis)
        
        # Convert sets to lists for JSON serialization
        analysis["affected_records"] = sorted(list(analysis["affected_records"]))
        analysis["violation_count"] = len(analysis["affected_records"])
        
        logger.info(f"✓ Analysis complete: {len(analysis['affected_records'])} records with issues, "
                   f"{sum(len(v) for v in analysis['violations'].values())} total violations")
        
        return analysis
    
    def _analyze_completeness(self, df: pd.DataFrame, analysis: Dict):
        """Detect missing/NULL values in all columns"""
        required_columns = {
            'Policy Number', 'Policy Effective Date', 'Policy Expiry Date',
            'Policy Status', 'Customer ID', 'Customer Name', 'Coverage ID',
            'National ID', 'Email'
        }
        
        for col in df.columns:
            null_mask = df[col].isna() | (df[col] == '') | (df[col].astype(str).str.strip() == '')
            
            for idx in df[null_mask].index:
                severity = 'critical' if col in required_columns else 'high'
                analysis["violations"]["completeness"].append({
                    "row": idx,
                    "column": col,
                    "issue": f"Missing/NULL value in {col}",
                    "value": str(df.loc[idx, col]),
                    "severity": severity
                })
                analysis["severity_breakdown"][severity] += 1
                analysis["affected_records"].add(idx)
    
    def _analyze_validity(self, df: pd.DataFrame, analysis: Dict):
        """Detect format, type, and range violations"""
        
        # Date validation
        date_columns = {
            'Policy Effective Date', 'Policy Expiry Date', 'Customer DOB',
            'Endorsement Effective Date', 'Cancellation Effective Date'
        }
        
        for col in date_columns:
            if col not in df.columns:
                continue
            
            for idx, val in df[col].items():
                if pd.isna(val) or val == '':
                    continue
                
                if not self._is_valid_date(str(val)):
                    analysis["violations"]["validity"].append({
                        "row": idx,
                        "column": col,
                        "issue": f"Invalid date format: {val}",
                        "value": str(val),
                        "severity": "high",
                        "expected_format": "MM/DD/YYYY or DD-MM-YYYY or YYYY-MM-DD"
                    })
                    analysis["severity_breakdown"]["high"] += 1
                    analysis["affected_records"].add(idx)
        
        # Policy Status validation
        valid_statuses = {'Active', 'Bound', 'Expired', 'Submitted', 'Cancelled', 'Draft'}
        if 'Policy Status' in df.columns:
            for idx, val in df['Policy Status'].items():
                if val not in valid_statuses:
                    analysis["violations"]["validity"].append({
                        "row": idx,
                        "column": "Policy Status",
                        "issue": f"Invalid status value: {val}",
                        "value": str(val),
                        "severity": "high",
                        "allowed_values": list(valid_statuses)
                    })
                    analysis["severity_breakdown"]["high"] += 1
                    analysis["affected_records"].add(idx)
        
        # Email validation
        if 'Email' in df.columns:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            for idx, val in df['Email'].items():
                if pd.isna(val) or val == '':
                    continue
                if not re.match(email_pattern, str(val)):
                    analysis["violations"]["validity"].append({
                        "row": idx,
                        "column": "Email",
                        "issue": f"Invalid email format: {val}",
                        "value": str(val),
                        "severity": "medium",
                        "expected_format": "user@domain.com"
                    })
                    analysis["severity_breakdown"]["medium"] += 1
                    analysis["affected_records"].add(idx)
        
        # Phone validation
        if 'Phone' in df.columns:
            for idx, val in df['Phone'].items():
                if pd.isna(val) or val == '':
                    continue
                digits = re.sub(r'\D', '', str(val))
                if len(digits) < 10:
                    analysis["violations"]["validity"].append({
                        "row": idx,
                        "column": "Phone",
                        "issue": f"Phone number too short: {val}",
                        "value": str(val),
                        "severity": "medium"
                    })
                    analysis["severity_breakdown"]["medium"] += 1
                    analysis["affected_records"].add(idx)
        
        # Numeric range validation
        numeric_ranges = {
            'Premium Amount': (0, float('inf')),
            'Coverage Limit': (0, float('inf')),
            'Coverage Deductible': (0, float('inf')),
            'Agent Commission %': (0, 100)
        }
        
        for col, (min_val, max_val) in numeric_ranges.items():
            if col not in df.columns:
                continue
            
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                try:
                    num_val = float(val)
                    if num_val < min_val or num_val > max_val:
                        analysis["violations"]["validity"].append({
                            "row": idx,
                            "column": col,
                            "issue": f"Value out of valid range [{min_val}, {max_val}]: {num_val}",
                            "value": str(val),
                            "severity": "high",
                            "valid_range": f"[{min_val}, {max_val}]"
                        })
                        analysis["severity_breakdown"]["high"] += 1
                        analysis["affected_records"].add(idx)
                except (ValueError, TypeError):
                    analysis["violations"]["validity"].append({
                        "row": idx,
                        "column": col,
                        "issue": f"Non-numeric value in numeric column: {val}",
                        "value": str(val),
                        "severity": "high"
                    })
                    analysis["severity_breakdown"]["high"] += 1
                    analysis["affected_records"].add(idx)
    
    def _analyze_uniqueness(self, df: pd.DataFrame, analysis: Dict):
        """Detect duplicate values and records"""
        
        unique_columns = {'Policy Number', 'Customer ID', 'National ID', 'Coverage ID'}
        
        for col in unique_columns:
            if col not in df.columns:
                continue
            
            duplicated = df[df.duplicated(subset=[col], keep=False)]
            
            for idx, row in duplicated.iterrows():
                # Count occurrences
                occurrences = len(df[df[col] == row[col]])
                analysis["violations"]["uniqueness"].append({
                    "row": idx,
                    "column": col,
                    "issue": f"Duplicate {col} (appears {occurrences} times): {row[col]}",
                    "value": str(row[col]),
                    "severity": "high",
                    "occurrences": occurrences
                })
                analysis["severity_breakdown"]["high"] += 1
                analysis["affected_records"].add(idx)
    
    def _analyze_consistency(self, df: pd.DataFrame, analysis: Dict):
        """Detect cross-field inconsistencies"""
        
        # Policy dates logic: Effective Date should be before Expiry Date
        if 'Policy Effective Date' in df.columns and 'Policy Expiry Date' in df.columns:
            for idx in df.index:
                eff_str = str(df.loc[idx, 'Policy Effective Date']).strip()
                exp_str = str(df.loc[idx, 'Policy Expiry Date']).strip()
                
                if eff_str == 'nan' or exp_str == 'nan' or eff_str == '' or exp_str == '':
                    continue
                
                try:
                    eff_date = pd.to_datetime(eff_str, format='%m/%d/%Y', errors='coerce')
                    if pd.isna(eff_date):
                        eff_date = pd.to_datetime(eff_str, format='%d-%m-%Y', errors='coerce')
                    if pd.isna(eff_date):
                        eff_date = pd.to_datetime(eff_str, errors='coerce')
                    
                    exp_date = pd.to_datetime(exp_str, format='%m/%d/%Y', errors='coerce')
                    if pd.isna(exp_date):
                        exp_date = pd.to_datetime(exp_str, format='%d-%m-%Y', errors='coerce')
                    if pd.isna(exp_date):
                        exp_date = pd.to_datetime(exp_str, errors='coerce')
                    
                    if not pd.isna(eff_date) and not pd.isna(exp_date):
                        if eff_date >= exp_date:
                            analysis["violations"]["consistency"].append({
                                "row": idx,
                                "columns": ["Policy Effective Date", "Policy Expiry Date"],
                                "issue": f"Effective Date ({eff_str}) must be before Expiry Date ({exp_str})",
                                "values": {"Effective": eff_str, "Expiry": exp_str},
                                "severity": "critical"
                            })
                            analysis["severity_breakdown"]["critical"] += 1
                            analysis["affected_records"].add(idx)
                except:
                    pass
        
        # Premium amount should be consistent with coverage limit
        if 'Premium Amount' in df.columns and 'Coverage Limit' in df.columns:
            for idx in df.index:
                try:
                    premium = float(df.loc[idx, 'Premium Amount'])
                    coverage = float(df.loc[idx, 'Coverage Limit'])
                    
                    # Premium should typically be 2-5% of coverage limit
                    if coverage > 0 and (premium < coverage * 0.001 or premium > coverage * 0.1):
                        analysis["violations"]["consistency"].append({
                            "row": idx,
                            "columns": ["Premium Amount", "Coverage Limit"],
                            "issue": f"Premium ({premium}) seems inconsistent with Coverage ({coverage}) - expected 0.1%-10% ratio",
                            "values": {"Premium": premium, "Coverage": coverage},
                            "severity": "medium"
                        })
                        analysis["severity_breakdown"]["medium"] += 1
                        analysis["affected_records"].add(idx)
                except:
                    pass
    
    def _analyze_accuracy(self, df: pd.DataFrame, analysis: Dict):
        """Detect accuracy and business rule violations"""
        
        # Policy term validation
        if 'Policy Term Type' in df.columns:
            valid_terms = {'Annual', 'Monthly', 'Quarterly', 'Semi-Annual'}
            for idx, val in df['Policy Term Type'].items():
                if val not in valid_terms:
                    analysis["violations"]["accuracy"].append({
                        "row": idx,
                        "column": "Policy Term Type",
                        "issue": f"Invalid policy term: {val}",
                        "value": str(val),
                        "severity": "high",
                        "allowed_values": list(valid_terms)
                    })
                    analysis["severity_breakdown"]["high"] += 1
                    analysis["affected_records"].add(idx)
        
        # Age validation (Customer DOB)
        if 'Customer DOB' in df.columns:
            for idx, dob_str in df['Customer DOB'].items():
                if pd.isna(dob_str) or dob_str == '':
                    continue
                try:
                    dob = pd.to_datetime(str(dob_str), errors='coerce')
                    if not pd.isna(dob):
                        age = (datetime.now() - dob).days / 365.25
                        if age < 18:
                            analysis["violations"]["accuracy"].append({
                                "row": idx,
                                "column": "Customer DOB",
                                "issue": f"Customer age ({age:.1f} years) below minimum (18 years)",
                                "value": str(dob_str),
                                "severity": "critical"
                            })
                            analysis["severity_breakdown"]["critical"] += 1
                            analysis["affected_records"].add(idx)
                        elif age > 150:
                            analysis["violations"]["accuracy"].append({
                                "row": idx,
                                "column": "Customer DOB",
                                "issue": f"Customer age ({age:.1f} years) unrealistic",
                                "value": str(dob_str),
                                "severity": "medium"
                            })
                            analysis["severity_breakdown"]["medium"] += 1
                            analysis["affected_records"].add(idx)
                except:
                    pass
    
    def _analyze_semantic_with_llm(self, df: pd.DataFrame, sample_size: int, analysis: Dict):
        """Use LLM to detect semantic and pattern-based violations"""
        if not self.llm_client or not self.llm_client.available:
            return
        
        try:
            # Sample data for LLM analysis
            sample_indices = np.random.choice(df.index, min(sample_size, len(df)), replace=False)
            sample_df = df.loc[sample_indices]
            
            # Create analysis prompt
            prompt = f"""Analyze this sample of insurance policy data and identify potential data quality issues:

{sample_df.to_string()}

For each issue found, provide:
1. Row number (if applicable)
2. Column name
3. Issue description
4. Severity (critical/high/medium/low)
5. Suggested fix

Focus on:
- Pattern inconsistencies (e.g., policy numbers that don't follow expected format)
- Semantic issues (e.g., customer names that are too short, too long, or suspicious)
- Business logic violations
- Data entry errors
- Suspicious patterns

Provide response as JSON array."""

            response = self.llm_client.complete(prompt)
            
            if response:
                try:
                    # Parse LLM response
                    issues = json.loads(response)
                    for issue in issues:
                        if isinstance(issue, dict):
                            analysis["violations"]["semantic"].append({
                                "row": issue.get("row"),
                                "column": issue.get("column"),
                                "issue": issue.get("issue", ""),
                                "severity": issue.get("severity", "medium"),
                                "suggested_fix": issue.get("suggested_fix", "")
                            })
                            if "row" in issue and issue["row"] is not None:
                                analysis["severity_breakdown"][issue.get("severity", "medium")] += 1
                                if isinstance(issue["row"], (int, np.integer)):
                                    analysis["affected_records"].add(int(issue["row"]))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Could not parse LLM semantic analysis response")
        
        except Exception as e:
            logger.warning(f"LLM semantic analysis failed: {e}")
    
    def _calculate_column_quality(self, df: pd.DataFrame, analysis: Dict):
        """Calculate quality score for each column"""
        for col in df.columns:
            col_violations = []
            col_violations.extend([v for v in analysis["violations"]["completeness"] if v["column"] == col])
            col_violations.extend([v for v in analysis["violations"]["validity"] if v["column"] == col])
            col_violations.extend([v for v in analysis["violations"]["uniqueness"] if v["column"] == col])
            col_violations.extend([v for v in analysis["violations"]["accuracy"] if v["column"] == col])
            
            violation_count = len(col_violations)
            quality_score = max(0, 100 - (violation_count / len(df) * 100))
            
            analysis["column_quality"][col] = {
                "violation_count": violation_count,
                "quality_score": quality_score,
                "affected_rows": len(set(v["row"] for v in col_violations if "row" in v and v["row"] is not None))
            }
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string is a valid date in common formats"""
        formats = ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']
        for fmt in formats:
            try:
                pd.to_datetime(date_str, format=fmt)
                return True
            except:
                pass
        
        # Try flexible parsing
        try:
            pd.to_datetime(date_str)
            return True
        except:
            return False
