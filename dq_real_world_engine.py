"""
Enhanced Data Quality Rules Engine
Detects and fixes real data quality violations across all dimensions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class DQViolation:
    """Represents a single data quality violation"""
    def __init__(self, row_idx: int, column: str, dimension: str, 
                 violation_type: str, original_value: Any, 
                 suggested_fix: Any = None, severity: str = "high"):
        self.row_idx = row_idx
        self.column = column
        self.dimension = dimension
        self.violation_type = violation_type
        self.original_value = original_value
        self.suggested_fix = suggested_fix
        self.severity = severity
        self.fixed = False
    
    def to_dict(self):
        return {
            'row_index': self.row_idx,
            'column': self.column,
            'dimension': self.dimension,
            'violation_type': self.violation_type,
            'original_value': str(self.original_value),
            'suggested_fix': str(self.suggested_fix),
            'severity': self.severity,
            'fixed': self.fixed
        }


class RealWorldRulesEngine:
    """Real-world DQ rules with actual violation detection and fixes"""
    
    def __init__(self):
        self.violations = []
        self.fixes_applied = {}
    
    def detect_all_violations(self, df: pd.DataFrame) -> Tuple[List[DQViolation], pd.DataFrame]:
        """Detect all violations across all dimensions"""
        self.violations = []
        
        # Run all checks
        self._check_completeness(df)
        self._check_validity(df)
        self._check_uniqueness(df)
        self._check_consistency(df)
        self._check_accuracy(df)
        
        # Create summary
        violation_summary = self._create_summary(df, self.violations)
        
        logger.info(f"Detected {len(self.violations)} total violations across {len(df)} records")
        return self.violations, violation_summary
    
    def _check_completeness(self, df: pd.DataFrame):
        """Check for NULL/missing values (Completeness dimension)"""
        required_columns = [
            'Policy Number', 'Policy Effective Date', 'Policy Expiry Date',
            'Policy Status', 'Customer ID', 'Customer Name', 'Coverage ID'
        ]
        
        for col in required_columns:
            if col in df.columns:
                null_mask = df[col].isna()
                for idx in df[null_mask].index:
                    self.violations.append(DQViolation(
                        row_idx=idx,
                        column=col,
                        dimension='Completeness',
                        violation_type='Missing Value',
                        original_value=None,
                        suggested_fix='[MISSING - Requires Manual Review]',
                        severity='critical'
                    ))
    
    def _check_validity(self, df: pd.DataFrame):
        """Check for format/validity issues (Validity dimension)"""
        
        # 1. Date format validation
        date_columns = {
            'Policy Effective Date': ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d'],
            'Policy Expiry Date': ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d'],
            'Customer DOB': ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d'],
            'Endorsement Effective Date': ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d'],
            'Cancellation Effective Date': ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d'],
        }
        
        for col, formats in date_columns.items():
            if col in df.columns:
                for idx, val in df[col].items():
                    if pd.isna(val):
                        continue
                    if not self._is_valid_date(str(val), formats):
                        self.violations.append(DQViolation(
                            row_idx=idx,
                            column=col,
                            dimension='Validity',
                            violation_type='Invalid Date Format',
                            original_value=val,
                            suggested_fix=self._normalize_date(str(val)),
                            severity='high'
                        ))
        
        # 2. Policy Status validation - must be in allowed set
        valid_statuses = ['Active', 'Bound', 'Expired', 'Submitted', 'Cancelled', 'Draft']
        if 'Policy Status' in df.columns:
            for idx, val in df['Policy Status'].items():
                if val not in valid_statuses:
                    self.violations.append(DQViolation(
                        row_idx=idx,
                        column='Policy Status',
                        dimension='Validity',
                        violation_type='Invalid Status Value',
                        original_value=val,
                        suggested_fix='Active',  # Default to Active
                        severity='high'
                    ))
        
        # 3. Renewal Indicator validation - must be Y or N
        if 'Renewal Indicator' in df.columns:
            for idx, val in df['Renewal Indicator'].items():
                if val not in ['Y', 'N']:
                    self.violations.append(DQViolation(
                        row_idx=idx,
                        column='Renewal Indicator',
                        dimension='Validity',
                        violation_type='Invalid Renewal Indicator',
                        original_value=val,
                        suggested_fix='N',  # Default to No
                        severity='high'
                    ))
        
        # 4. ID format validation (Policy Number, Customer ID, etc.)
        id_columns = ['Policy Number', 'Customer ID', 'Coverage ID', 'Agent ID']
        for col in id_columns:
            if col in df.columns:
                for idx, val in df[col].items():
                    if pd.isna(val):
                        continue
                    val_str = str(val).strip()
                    if len(val_str) == 0:
                        self.violations.append(DQViolation(
                            row_idx=idx,
                            column=col,
                            dimension='Validity',
                            violation_type='Empty ID',
                            original_value=val,
                            suggested_fix=f"INVALID_{idx}",
                            severity='high'
                        ))
    
    def _check_uniqueness(self, df: pd.DataFrame):
        """Check for duplicate records (Uniqueness dimension)"""
        
        # Policy Number should be unique
        if 'Policy Number' in df.columns:
            policy_dupes = df[df['Policy Number'].duplicated(keep=False)]
            for idx, row in policy_dupes.iterrows():
                self.violations.append(DQViolation(
                    row_idx=idx,
                    column='Policy Number',
                    dimension='Uniqueness',
                    violation_type='Duplicate Policy',
                    original_value=row['Policy Number'],
                    suggested_fix=f"{row['Policy Number']}_DUP{idx}",
                    severity='high'
                ))
    
    def _check_consistency(self, df: pd.DataFrame):
        """Check for inconsistent relationships (Consistency dimension)"""
        
        # Policy Effective Date should be before Expiry Date
        if 'Policy Effective Date' in df.columns and 'Policy Expiry Date' in df.columns:
            for idx in df.index:
                eff_date = df.loc[idx, 'Policy Effective Date']
                exp_date = df.loc[idx, 'Policy Expiry Date']
                
                if pd.isna(eff_date) or pd.isna(exp_date):
                    continue
                
                try:
                    eff = pd.to_datetime(eff_date, format='%m/%d/%Y', errors='coerce')
                    if eff is pd.NaT:
                        eff = pd.to_datetime(eff_date, format='%d-%m-%Y', errors='coerce')
                    
                    exp = pd.to_datetime(exp_date, format='%m/%d/%Y', errors='coerce')
                    if exp is pd.NaT:
                        exp = pd.to_datetime(exp_date, format='%d-%m-%Y', errors='coerce')
                    
                    if eff is not pd.NaT and exp is not pd.NaT and eff >= exp:
                        self.violations.append(DQViolation(
                            row_idx=idx,
                            column='Policy Effective Date vs Expiry Date',
                            dimension='Consistency',
                            violation_type='Date Logic Error',
                            original_value=f"{eff_date} >= {exp_date}",
                            suggested_fix="Swap or correct dates",
                            severity='high'
                        ))
                except:
                    pass
    
    def _check_accuracy(self, df: pd.DataFrame):
        """Check for accuracy issues (Accuracy dimension)"""
        
        # Percentage fields should be 0-100
        percentage_cols = ['Agent Commission %']
        for col in percentage_cols:
            if col in df.columns:
                for idx, val in df[col].items():
                    if pd.isna(val):
                        continue
                    try:
                        num_val = float(val)
                        if num_val < 0 or num_val > 100:
                            self.violations.append(DQViolation(
                                row_idx=idx,
                                column=col,
                                dimension='Accuracy',
                                violation_type='Out of Range',
                                original_value=val,
                                suggested_fix=max(0, min(100, num_val)),
                                severity='medium'
                            ))
                    except:
                        pass
        
        # Numeric fields should be positive
        numeric_cols = ['Coverage Limit', 'Coverage Deductible', 'Premium Amount']
        for col in numeric_cols:
            if col in df.columns:
                for idx, val in df[col].items():
                    if pd.isna(val):
                        continue
                    try:
                        num_val = float(val)
                        if num_val < 0:
                            self.violations.append(DQViolation(
                                row_idx=idx,
                                column=col,
                                dimension='Accuracy',
                                violation_type='Negative Value',
                                original_value=val,
                                suggested_fix=abs(num_val),
                                severity='high'
                            ))
                    except:
                        pass
    
    def _is_valid_date(self, date_str: str, formats: List[str]) -> bool:
        """Check if string is valid date in any of the given formats"""
        for fmt in formats:
            try:
                pd.to_datetime(date_str, format=fmt)
                return True
            except:
                continue
        return False
    
    def _normalize_date(self, date_str: str) -> str:
        """Try to parse and normalize date to MM/DD/YYYY format"""
        formats = ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y']
        for fmt in formats:
            try:
                dt = pd.to_datetime(date_str, format=fmt)
                return dt.strftime('%m/%d/%Y')
            except:
                continue
        return date_str  # Return original if can't parse
    
    def _create_summary(self, df: pd.DataFrame, violations: List[DQViolation]) -> pd.DataFrame:
        """Create violation summary DataFrame"""
        if not violations:
            return pd.DataFrame()
        
        summary_data = [v.to_dict() for v in violations]
        return pd.DataFrame(summary_data)
    
    def apply_fixes(self, df: pd.DataFrame, violations: List[DQViolation]) -> pd.DataFrame:
        """Apply suggested fixes to dataframe"""
        df_clean = df.copy()
        
        for violation in violations:
            if violation.suggested_fix is not None and violation.suggested_fix != '[MISSING - Requires Manual Review]':
                try:
                    df_clean.loc[violation.row_idx, violation.column] = violation.suggested_fix
                    violation.fixed = True
                except:
                    pass
        
        return df_clean
    
    def get_violation_stats(self, violations: List[DQViolation]) -> Dict[str, Any]:
        """Get statistics on violations"""
        if not violations:
            return {
                'total_violations': 0,
                'affected_records': 0,
                'by_dimension': {},
                'by_severity': {}
            }
        
        affected_rows = set(v.row_idx for v in violations)
        
        stats = {
            'total_violations': len(violations),
            'affected_records': len(affected_rows),
            'by_dimension': {},
            'by_severity': {},
            'by_type': {}
        }
        
        for v in violations:
            # By dimension
            if v.dimension not in stats['by_dimension']:
                stats['by_dimension'][v.dimension] = 0
            stats['by_dimension'][v.dimension] += 1
            
            # By severity
            if v.severity not in stats['by_severity']:
                stats['by_severity'][v.severity] = 0
            stats['by_severity'][v.severity] += 1
            
            # By type
            if v.violation_type not in stats['by_type']:
                stats['by_type'][v.violation_type] = 0
            stats['by_type'][v.violation_type] += 1
        
        return stats
