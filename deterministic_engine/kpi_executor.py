"""
KPI Execution Engine - Computes data quality metrics deterministically.
No ML, pure metrics from rule violations.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class KPIExecutor:
    """Computes KPIs from rule violations."""
    
    def compute_pass_rate(
        self,
        total_records: int,
        violations: List[Dict[str, Any]],
        dimension: Optional[str] = None,
        rule_ids: Optional[List[str]] = None
    ) -> float:
        """
        Compute pass rate: % of records without violations.
        
        Formula: (total_records - failed_records) / total_records * 100
        """
        if total_records == 0:
            return 0.0
        
        violations_to_check = violations
        
        # Filter by dimension if specified
        if dimension:
            violations_to_check = [
                v for v in violations if v.get("dimension") == dimension
            ]
        
        # Filter by rules if specified
        if rule_ids:
            violations_to_check = [
                v for v in violations_to_check
                if v.get("rule_id") in rule_ids
            ]
        
        # Get unique failed record indices
        failed_records = set()
        for violation in violations_to_check:
            failed_records.update(violation.get("failed_rows", []))
        
        pass_count = total_records - len(failed_records)
        return (pass_count / total_records) * 100.0
    
    def compute_fail_rate(
        self,
        total_records: int,
        violations: List[Dict[str, Any]],
        dimension: Optional[str] = None,
        rule_ids: Optional[List[str]] = None
    ) -> float:
        """
        Compute fail rate: % of records with violations.
        
        Formula: failed_records / total_records * 100
        """
        return 100.0 - self.compute_pass_rate(
            total_records, violations, dimension, rule_ids
        )
    
    def compute_pass_count(
        self,
        total_records: int,
        violations: List[Dict[str, Any]],
        dimension: Optional[str] = None,
        rule_ids: Optional[List[str]] = None
    ) -> int:
        """Compute absolute count of passing records."""
        if total_records == 0:
            return 0
        
        violations_to_check = violations
        
        if dimension:
            violations_to_check = [
                v for v in violations if v.get("dimension") == dimension
            ]
        
        if rule_ids:
            violations_to_check = [
                v for v in violations_to_check
                if v.get("rule_id") in rule_ids
            ]
        
        failed_records = set()
        for violation in violations_to_check:
            failed_records.update(violation.get("failed_rows", []))
        
        return total_records - len(failed_records)
    
    def compute_fail_count(
        self,
        violations: List[Dict[str, Any]],
        dimension: Optional[str] = None,
        rule_ids: Optional[List[str]] = None
    ) -> int:
        """Compute absolute count of failing records."""
        violations_to_check = violations
        
        if dimension:
            violations_to_check = [
                v for v in violations if v.get("dimension") == dimension
            ]
        
        if rule_ids:
            violations_to_check = [
                v for v in violations_to_check
                if v.get("rule_id") in rule_ids
            ]
        
        failed_records = set()
        for violation in violations_to_check:
            failed_records.update(violation.get("failed_rows", []))
        
        return len(failed_records)
    
    def compute_violation_count(
        self,
        violations: List[Dict[str, Any]],
        dimension: Optional[str] = None,
        rule_ids: Optional[List[str]] = None
    ) -> int:
        """Compute total violation count (may be > failed_records if multiple rules fail per record)."""
        violations_to_check = violations
        
        if dimension:
            violations_to_check = [
                v for v in violations if v.get("dimension") == dimension
            ]
        
        if rule_ids:
            violations_to_check = [
                v for v in violations_to_check
                if v.get("rule_id") in rule_ids
            ]
        
        return sum(v.get("failed_count", 0) for v in violations_to_check)
    
    def compute_avg_violations_per_record(
        self,
        total_records: int,
        violations: List[Dict[str, Any]],
        dimension: Optional[str] = None,
        rule_ids: Optional[List[str]] = None
    ) -> float:
        """Compute average violations per record."""
        if total_records == 0:
            return 0.0
        
        violation_count = self.compute_violation_count(
            violations, dimension, rule_ids
        )
        
        return violation_count / total_records
    
    def compute_dimension_scores(
        self,
        total_records: int,
        violations: List[Dict[str, Any]],
        dimensions: List[str]
    ) -> Dict[str, float]:
        """Compute pass rate for each dimension."""
        scores = {}
        
        for dimension in dimensions:
            scores[dimension] = self.compute_pass_rate(
                total_records,
                violations,
                dimension=dimension
            )
        
        return scores
    
    def compute_overall_quality_score(
        self,
        total_records: int,
        violations: List[Dict[str, Any]],
        dimension_weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Compute weighted overall quality score.
        
        Default: equal weight to all dimensions.
        """
        if not violations:
            return 100.0
        
        # Get unique dimensions
        dimensions = set(
            v.get("dimension", "unknown") for v in violations
        )
        dimensions.discard(None)
        dimensions = list(dimensions)
        
        if not dimensions:
            dimensions = ["accuracy", "completeness", "consistency", "timeliness", "uniqueness", "relevance"]
        
        # Default weights: equal
        if dimension_weights is None:
            weight = 1.0 / len(dimensions)
            dimension_weights = {dim: weight for dim in dimensions}
        
        # Compute weighted score
        scores = self.compute_dimension_scores(total_records, violations, dimensions)
        
        overall = sum(
            scores.get(dim, 0.0) * dimension_weights.get(dim, 0.0)
            for dim in dimensions
        )
        
        return overall
    
    def compute_improvement_metrics(
        self,
        total_records: int,
        violations_before: List[Dict[str, Any]],
        violations_after: List[Dict[str, Any]],
        dimension: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute improvement from before/after violations."""
        pass_before = self.compute_pass_rate(
            total_records, violations_before, dimension
        )
        pass_after = self.compute_pass_rate(
            total_records, violations_after, dimension
        )
        
        fail_count_before = self.compute_fail_count(violations_before, dimension)
        fail_count_after = self.compute_fail_count(violations_after, dimension)
        
        remediated_count = fail_count_before - fail_count_after
        
        return {
            "pass_rate_before": pass_before,
            "pass_rate_after": pass_after,
            "pass_rate_improvement": pass_after - pass_before,
            "fail_count_before": fail_count_before,
            "fail_count_after": fail_count_after,
            "remediated_count": remediated_count,
            "remediation_rate": (remediated_count / fail_count_before) if fail_count_before > 0 else 0.0
        }
    
    def execute_kpi_set(
        self,
        kpis: List[Dict[str, Any]],
        total_records: int,
        violations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute all KPIs."""
        results = {}
        
        for kpi in kpis:
            kpi_id = kpi.get("kpi_id")
            function = kpi.get("function")
            params = kpi.get("parameters", {})
            
            try:
                if function == "pass_rate":
                    value = self.compute_pass_rate(
                        total_records,
                        violations,
                        dimension=params.get("dimension"),
                        rule_ids=params.get("rule_ids")
                    )
                
                elif function == "fail_rate":
                    value = self.compute_fail_rate(
                        total_records,
                        violations,
                        dimension=params.get("dimension"),
                        rule_ids=params.get("rule_ids")
                    )
                
                elif function == "pass_count":
                    value = self.compute_pass_count(
                        total_records,
                        violations,
                        dimension=params.get("dimension"),
                        rule_ids=params.get("rule_ids")
                    )
                
                elif function == "fail_count":
                    value = self.compute_fail_count(
                        violations,
                        dimension=params.get("dimension"),
                        rule_ids=params.get("rule_ids")
                    )
                
                elif function == "violation_count":
                    value = self.compute_violation_count(
                        violations,
                        dimension=params.get("dimension"),
                        rule_ids=params.get("rule_ids")
                    )
                
                elif function == "overall_score":
                    value = self.compute_overall_quality_score(
                        total_records,
                        violations,
                        params.get("weights")
                    )
                
                else:
                    logger.warning(f"Unknown KPI function: {function}")
                    value = None
                
                results[kpi_id] = {
                    "name": kpi.get("name"),
                    "value": value,
                    "function": function,
                    "dimension": kpi.get("dimension"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            except Exception as e:
                logger.error(f"Failed to compute KPI {kpi_id}: {e}")
                results[kpi_id] = {
                    "name": kpi.get("name"),
                    "value": None,
                    "error": str(e)
                }
        
        return results
