"""
DQ Assessment Engine
Analyzes data quality metrics and generates comprehensive reports
"""

import logging
import pandas as pd
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import Counter

from deterministic_engine.dynamic_rule_executor import RuleExecutionResult

logger = logging.getLogger(__name__)


class DQMetrics:
    """Data quality metrics calculation."""
    
    @staticmethod
    def calculate_completeness(df: pd.DataFrame, violations: List[RuleExecutionResult]) -> Dict[str, Any]:
        """Calculate completeness metrics."""
        not_null_violations = [v for v in violations if v.issue_type == "null_value"]
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = len(not_null_violations)
        completeness_score = ((total_cells - missing_cells) / total_cells * 100) if total_cells > 0 else 100
        
        return {
            "dimension": "Completeness",
            "total_cells": total_cells,
            "missing_cells": missing_cells,
            "score": completeness_score,
            "violations_count": len(not_null_violations)
        }
    
    @staticmethod
    def calculate_validity(violations: List[RuleExecutionResult]) -> Dict[str, Any]:
        """Calculate validity metrics."""
        validity_issues = [v for v in violations if v.issue_type in [
            "regex_mismatch", "invalid_date_format", "value_out_of_range",
            "invalid_numeric_value", "value_not_in_set"
        ]]
        
        return {
            "dimension": "Validity",
            "violations_count": len(validity_issues),
            "score": 100 - min(len(validity_issues) * 2, 100)
        }
    
    @staticmethod
    def calculate_consistency(violations: List[RuleExecutionResult]) -> Dict[str, Any]:
        """Calculate consistency metrics."""
        consistency_issues = [v for v in violations if v.issue_type in [
            "field_less_than_reference", "field_greater_than_reference", "month_diff_mismatch"
        ]]
        
        return {
            "dimension": "Consistency",
            "violations_count": len(consistency_issues),
            "score": 100 - min(len(consistency_issues) * 2, 100)
        }
    
    @staticmethod
    def calculate_uniqueness(violations: List[RuleExecutionResult]) -> Dict[str, Any]:
        """Calculate uniqueness metrics."""
        uniqueness_violations = [v for v in violations if v.issue_type == "duplicate_value"]
        
        return {
            "dimension": "Uniqueness",
            "violations_count": len(uniqueness_violations),
            "score": 100 - min(len(uniqueness_violations) * 3, 100)
        }
    
    @staticmethod
    def calculate_accuracy(violations: List[RuleExecutionResult]) -> Dict[str, Any]:
        """Calculate accuracy metrics."""
        accuracy_violations = [v for v in violations if v.issue_type == "regex_mismatch"]
        
        return {
            "dimension": "Accuracy",
            "violations_count": len(accuracy_violations),
            "score": 100 - min(len(accuracy_violations) * 2, 100)
        }


class AssessmentEngine:
    """
    Comprehensive DQ assessment engine.
    Generates detailed reports with before/after metrics.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def generate_assessment(
        self,
        df: pd.DataFrame,
        violations: List[RuleExecutionResult],
        assessment_id: str,
        phase: str = "before"  # "before" or "after"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive assessment.
        
        Args:
            df: DataFrame being assessed
            violations: List of DQ violations found
            assessment_id: Unique identifier for this assessment
            phase: Whether this is pre or post remediation
        
        Returns:
            Assessment dictionary with detailed metrics
        """
        
        assessment = {
            "assessment_id": assessment_id,
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "total_records": len(df),
            "total_columns": len(df.columns),
            "total_cells": len(df) * len(df.columns),
        }
        
        # Count violations
        assessment["total_violations"] = len(violations)
        assessment["records_with_issues"] = len(set(v.record_id for v in violations))
        assessment["records_with_issues_pct"] = (
            assessment["records_with_issues"] / assessment["total_records"] * 100
            if assessment["total_records"] > 0 else 0
        )
        
        # Calculate pass rate
        assessment["pass_rate"] = (
            (assessment["total_records"] - assessment["records_with_issues"]) / 
            assessment["total_records"] * 100
            if assessment["total_records"] > 0 else 100
        )
        
        # Violations by dimension
        assessment["violations_by_dimension"] = self._get_violations_by_dimension(violations)
        
        # Violations by severity
        assessment["violations_by_severity"] = self._get_violations_by_severity(violations)
        
        # Violations by column
        assessment["violations_by_column"] = self._get_violations_by_column(violations)
        
        # Dimension metrics
        assessment["dimension_metrics"] = {
            "completeness": DQMetrics.calculate_completeness(df, violations),
            "validity": DQMetrics.calculate_validity(violations),
            "consistency": DQMetrics.calculate_consistency(violations),
            "uniqueness": DQMetrics.calculate_uniqueness(violations),
            "accuracy": DQMetrics.calculate_accuracy(violations)
        }
        
        # Overall DQ score
        scores = [m.get("score", m.get("validity_score", m.get("uniqueness_score", 0))) 
                  for m in assessment["dimension_metrics"].values() if m]
        assessment["overall_dq_score"] = sum(scores) / len(scores) if scores else 100
        
        # Top issues
        assessment["top_issues"] = self._get_top_issues(violations, limit=10)
        
        # Issue patterns
        assessment["issue_patterns"] = self._analyze_patterns(violations)
        
        return assessment
    
    def _get_violations_by_dimension(self, violations: List[RuleExecutionResult]) -> Dict[str, int]:
        """Count violations by dimension."""
        counter = Counter(v.issue_type for v in violations)
        return dict(counter)
    
    def _get_violations_by_severity(self, violations: List[RuleExecutionResult]) -> Dict[str, int]:
        """Count violations by severity."""
        # Map issue types to severity
        severity_map = {
            "null_value": "Critical",
            "duplicate_value": "High",
            "invalid_date_format": "High",
            "value_out_of_range": "Medium",
            "regex_mismatch": "Medium",
            "invalid_length": "Low"
        }
        
        severity_counter = Counter(
            severity_map.get(v.issue_type, "Medium") for v in violations
        )
        return dict(severity_counter)
    
    def _get_violations_by_column(self, violations: List[RuleExecutionResult]) -> Dict[str, int]:
        """Count violations by column."""
        counter = Counter(v.column for v in violations)
        return dict(sorted(counter.items(), key=lambda x: -x[1])[:20])  # Top 20
    
    def _get_top_issues(self, violations: List[RuleExecutionResult], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top issues."""
        issue_counter = Counter((v.issue_type, v.column) for v in violations)
        top_issues = []
        
        for (issue_type, column), count in issue_counter.most_common(limit):
            top_issues.append({
                "issue_type": issue_type,
                "column": column,
                "count": count
            })
        
        return top_issues
    
    def _analyze_patterns(self, violations: List[RuleExecutionResult]) -> Dict[str, Any]:
        """Analyze violation patterns."""
        patterns = {
            "most_affected_column": None,
            "most_common_issue": None,
            "affected_records_pct": 0
        }
        
        if not violations:
            return patterns
        
        # Most affected column
        columns = Counter(v.column for v in violations)
        if columns:
            patterns["most_affected_column"] = columns.most_common(1)[0][0]
        
        # Most common issue
        issues = Counter(v.issue_type for v in violations)
        if issues:
            patterns["most_common_issue"] = issues.most_common(1)[0][0]
        
        return patterns
    
    def generate_improvement_report(
        self,
        before_assessment: Dict[str, Any],
        after_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate improvement report comparing before/after.
        """
        
        improvements = {
            "assessment_pair_id": f"{before_assessment['assessment_id']}_{after_assessment['assessment_id']}",
            "timestamp": datetime.now().isoformat(),
            "before": before_assessment,
            "after": after_assessment,
            "improvements": {}
        }
        
        # Calculate improvements
        before_violations = before_assessment["total_violations"]
        after_violations = after_assessment["total_violations"]
        violations_fixed = before_violations - after_violations
        
        improvements["improvements"]["violations_fixed"] = violations_fixed
        improvements["improvements"]["violations_reduction_pct"] = (
            (violations_fixed / before_violations * 100) if before_violations > 0 else 0
        )
        
        # Pass rate improvement
        before_pass_rate = before_assessment["pass_rate"]
        after_pass_rate = after_assessment["pass_rate"]
        pass_rate_improvement = after_pass_rate - before_pass_rate
        
        improvements["improvements"]["pass_rate_improvement"] = pass_rate_improvement
        
        # Overall DQ score improvement
        before_score = before_assessment["overall_dq_score"]
        after_score = after_assessment["overall_dq_score"]
        score_improvement = after_score - before_score
        
        improvements["improvements"]["dq_score_improvement"] = score_improvement
        
        # Records improved
        before_records_with_issues = before_assessment["records_with_issues"]
        after_records_with_issues = after_assessment["records_with_issues"]
        records_improved = before_records_with_issues - after_records_with_issues
        
        improvements["improvements"]["records_improved"] = records_improved
        improvements["improvements"]["records_improved_pct"] = (
            (records_improved / before_assessment["total_records"] * 100)
            if before_assessment["total_records"] > 0 else 0
        )
        
        # Dimension-by-dimension comparison
        improvements["dimension_comparisons"] = {}
        for dimension in before_assessment.get("dimension_metrics", {}):
            if dimension in after_assessment.get("dimension_metrics", {}):
                before_score = before_assessment["dimension_metrics"][dimension].get("score", 0)
                after_score = after_assessment["dimension_metrics"][dimension].get("score", 0)
                
                improvements["dimension_comparisons"][dimension] = {
                    "before_score": before_score,
                    "after_score": after_score,
                    "improvement": after_score - before_score
                }
        
        return improvements


class ReportGenerator:
    """Generates various DQ reports."""
    
    @staticmethod
    def generate_excel_report(
        assessment: Dict[str, Any],
        output_path: str
    ):
        """Generate Excel report with multiple sheets."""
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Overview sheet
            overview_data = {
                "Metric": [
                    "Total Records",
                    "Total Columns",
                    "Total Violations",
                    "Records with Issues",
                    "Records with Issues %",
                    "Pass Rate %",
                    "Overall DQ Score"
                ],
                "Value": [
                    assessment["total_records"],
                    assessment["total_columns"],
                    assessment["total_violations"],
                    assessment["records_with_issues"],
                    f"{assessment['records_with_issues_pct']:.2f}",
                    f"{assessment['pass_rate']:.2f}",
                    f"{assessment['overall_dq_score']:.2f}"
                ]
            }
            pd.DataFrame(overview_data).to_excel(writer, sheet_name="Overview", index=False)
            
            # Violations by dimension
            if assessment.get("violations_by_dimension"):
                dim_data = pd.DataFrame(
                    list(assessment["violations_by_dimension"].items()),
                    columns=["Issue Type", "Count"]
                ).sort_values("Count", ascending=False)
                dim_data.to_excel(writer, sheet_name="Issues by Type", index=False)
            
            # Violations by column
            if assessment.get("violations_by_column"):
                col_data = pd.DataFrame(
                    list(assessment["violations_by_column"].items()),
                    columns=["Column", "Violations"]
                ).sort_values("Violations", ascending=False)
                col_data.to_excel(writer, sheet_name="Issues by Column", index=False)
            
            # Top issues
            if assessment.get("top_issues"):
                top_data = pd.DataFrame(assessment["top_issues"])
                top_data.to_excel(writer, sheet_name="Top Issues", index=False)
        
        logger.info(f"Excel report generated: {output_path}")
    
    @staticmethod
    def generate_summary_text(assessment: Dict[str, Any]) -> str:
        """Generate text summary."""
        summary = f"""
DATA QUALITY ASSESSMENT REPORT
=============================
Assessment ID: {assessment['assessment_id']}
Timestamp: {assessment['timestamp']}
Phase: {assessment.get('phase', 'N/A')}

KEY METRICS
-----------
Total Records: {assessment['total_records']}
Total Columns: {assessment['total_columns']}
Total Violations Found: {assessment['total_violations']}
Records with Issues: {assessment['records_with_issues']} ({assessment['records_with_issues_pct']:.1f}%)
Pass Rate: {assessment['pass_rate']:.1f}%
Overall DQ Score: {assessment['overall_dq_score']:.1f}/100

TOP ISSUES
----------
"""
        for issue in assessment.get("top_issues", [])[:5]:
            summary += f"  - {issue['issue_type']} in {issue['column']}: {issue['count']} occurrences\n"
        
        summary += f"""
DIMENSION METRICS
-----------------
"""
        for dimension, metrics in assessment.get("dimension_metrics", {}).items():
            summary += f"  {dimension.capitalize()}: {metrics.get('violations_count', 0)} violations\n"
        
        return summary
