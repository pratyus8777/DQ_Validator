"""
HITL (Human-in-the-Loop) Dashboard Backend
Allows humans to validate, override, and improve outputs.
Stores decisions for learning in future runs.
Fully dynamic with rule-based output generation.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
from enum import Enum

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """All possible decision types."""
    APPROVE = "approve"
    REJECT = "reject"
    OVERRIDE = "override"
    CORRECT = "correct"
    ESCALATE = "escalate"
    
    @classmethod
    def all_values(cls):
        return [e.value for e in cls]


class ReviewDecision:
    """Record of a human decision with full context."""
    
    def __init__(
        self,
        record_id: int,
        rule_id: str,
        decision: str,
        user_id: str = "system",
        reason: str = None,
        corrected_value: Any = None,
        original_value: Any = None,
        confidence: float = 1.0,
        dimension: str = None,
        column: str = None,
        check_type: str = None
    ):
        self.record_id = record_id
        self.rule_id = rule_id
        self.decision = decision
        self.user_id = user_id
        self.reason = reason
        self.corrected_value = corrected_value
        self.original_value = original_value
        self.confidence = confidence
        self.timestamp = datetime.utcnow().isoformat()
        self.dimension = dimension
        self.column = column
        self.check_type = check_type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "rule_id": self.rule_id,
            "decision": self.decision,
            "user_id": self.user_id,
            "reason": self.reason,
            "corrected_value": self.corrected_value,
            "original_value": self.original_value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "dimension": self.dimension,
            "column": self.column,
            "check_type": self.check_type
        }


class RecordReview:
    """Human review of a single record with dynamic violation handling."""
    
    def __init__(
        self,
        record_id: int,
        row_data: Dict[str, Any],
        violations: List[Dict[str, Any]],
        rules_metadata: Optional[Dict[str, Any]] = None
    ):
        self.record_id = record_id
        self.row_data = row_data
        self.violations = violations
        self.rules_metadata = rules_metadata or {}
        self.decisions: List[ReviewDecision] = []
        self.reviewed_at = None
        self.reviewed_by = None
        self.final_status = "pending"  # pending, approved, rejected, corrected
        self.corrections_applied = {}  # Track all corrections
    
    def add_decision(self, decision: ReviewDecision) -> None:
        """Add a decision for this record."""
        self.decisions.append(decision)
        
        # Track correction if applicable
        if decision.decision == DecisionType.CORRECT.value:
            self.corrections_applied[decision.column] = {
                "original": decision.original_value,
                "corrected": decision.corrected_value,
                "rule_id": decision.rule_id,
                "reason": decision.reason
            }
    
    def mark_reviewed(self, user_id: str) -> None:
        """Mark record as reviewed."""
        self.reviewed_at = datetime.utcnow().isoformat()
        self.reviewed_by = user_id
    
    def determine_status(self) -> str:
        """Determine final status based on decisions."""
        if not self.decisions:
            return "pending"
        
        statuses = {d.decision for d in self.decisions}
        
        if DecisionType.REJECT.value in statuses:
            return "rejected"
        elif DecisionType.CORRECT.value in statuses:
            return "corrected"
        elif DecisionType.APPROVE.value in statuses:
            return "approved"
        elif DecisionType.ESCALATE.value in statuses:
            return "escalated"
        else:
            return "reviewed"
    
    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of violations for this record."""
        return {
            "total_violations": len(self.violations),
            "by_dimension": self._group_by_dimension(),
            "by_column": self._group_by_column(),
            "by_check_type": self._group_by_check_type()
        }
    
    def _group_by_dimension(self) -> Dict[str, List[str]]:
        """Group violations by dimension."""
        grouped = {}
        for v in self.violations:
            dim = v.get("dimension", "unknown")
            if dim not in grouped:
                grouped[dim] = []
            grouped[dim].append(v.get("rule_id"))
        return grouped
    
    def _group_by_column(self) -> Dict[str, List[str]]:
        """Group violations by column."""
        grouped = {}
        for v in self.violations:
            col = v.get("column", "unknown")
            if col not in grouped:
                grouped[col] = []
            grouped[col].append(v.get("rule_id"))
        return grouped
    
    def _group_by_check_type(self) -> Dict[str, int]:
        """Count violations by check type."""
        counts = {}
        for v in self.violations:
            check = v.get("check", "unknown")
            counts[check] = counts.get(check, 0) + 1
        return counts
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "row_data": self.row_data,
            "violations": self.violations,
            "violation_summary": self.get_violation_summary(),
            "decisions": [d.to_dict() for d in self.decisions],
            "corrections_applied": self.corrections_applied,
            "reviewed_at": self.reviewed_at,
            "reviewed_by": self.reviewed_by,
            "status": self.final_status
        }


class HITLDashboard:
    """
    Optimized dashboard managing human review process with rule-based outputs.
    Fully dynamic: works with any rules, dimensions, check types.
    """
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend
        self.pending_reviews: Dict[int, RecordReview] = {}
        self.completed_reviews: Dict[int, RecordReview] = {}
        self.decisions: List[ReviewDecision] = []
        self.rules_metadata: Dict[str, Dict[str, Any]] = {}
    
    def set_rules_metadata(self, rules: List[Dict[str, Any]]) -> None:
        """Provide rule definitions for context-aware reviews."""
        self.rules_metadata = {
            r.get("rule_id"): r
            for r in rules
        }
        logger.info(f"Loaded metadata for {len(self.rules_metadata)} rules")
    
    def create_review_batch(
        self,
        df: pd.DataFrame,
        violations: List[Dict[str, Any]],
        sample_size: Optional[int] = None,
        strategy: str = "stratified",
        rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a batch of records for human review.
        
        Strategies:
        - random: Random sample
        - stratified: Sample from each violation type
        - high_violation: Records with most violations
        - dimension_balanced: Balanced across dimensions
        """
        if rules:
            self.set_rules_metadata(rules)
        
        if sample_size is None:
            sample_size = min(50, len(df))
        
        # Get indices for review based on strategy
        if strategy == "high_violation":
            indices = self._get_high_violation_indices(df, violations, sample_size)
        elif strategy == "stratified":
            indices = self._get_stratified_indices(df, violations, sample_size)
        elif strategy == "dimension_balanced":
            indices = self._get_dimension_balanced_indices(df, violations, sample_size)
        else:  # random
            indices = df.sample(min(sample_size, len(df)), replace=False).index.tolist()
        
        # Create reviews with metadata
        for idx in indices:
            row_data = df.loc[idx].to_dict()
            row_violations = [
                v for v in violations
                if idx in v.get("failed_rows", [])
            ]
            
            review = RecordReview(
                idx,
                row_data,
                row_violations,
                rules_metadata=self.rules_metadata
            )
            self.pending_reviews[idx] = review
        
        return {
            "batch_size": len(indices),
            "batch_strategy": strategy,
            "total_records": len(df),
            "total_violations": len(violations),
            "pending_reviews": len(self.pending_reviews),
            "violation_types": self._count_violation_types(violations)
        }
    
    def get_pending_review(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Get a record pending review with enhanced context."""
        review = self.pending_reviews.get(record_id)
        if review:
            return {
                "record_id": record_id,
                "data": review.row_data,
                "violations": review.violations,
                "violation_summary": review.get_violation_summary(),
                "violated_rules": self._get_rules_context(review.violations),
                "review_guidance": self._generate_review_guidance(review)
            }
        return None
    
    def submit_decision(
        self,
        record_id: int,
        rule_id: str,
        decision: str,
        user_id: str,
        reason: str = None,
        corrected_value: Any = None,
        original_value: Any = None,
        column: str = None
    ) -> bool:
        """Submit a human decision with full context."""
        if record_id not in self.pending_reviews:
            logger.warning(f"No pending review for record {record_id}")
            return False
        
        review = self.pending_reviews[record_id]
        
        # Get violation context
        violation = next(
            (v for v in review.violations if v.get("rule_id") == rule_id),
            {}
        )
        
        # Create decision with full context
        review_decision = ReviewDecision(
            record_id=record_id,
            rule_id=rule_id,
            decision=decision,
            user_id=user_id,
            reason=reason,
            corrected_value=corrected_value,
            original_value=original_value,
            confidence=1.0,
            dimension=violation.get("dimension"),
            column=column or violation.get("column"),
            check_type=violation.get("check")
        )
        
        review.add_decision(review_decision)
        self.decisions.append(review_decision)
        
        logger.info(
            f"Decision [{decision}] recorded for record {record_id} / {rule_id} "
            f"(dimension: {violation.get('dimension')})"
        )
        return True
    
    def close_review(self, record_id: int, user_id: str) -> bool:
        """Close a record review."""
        if record_id not in self.pending_reviews:
            return False
        
        review = self.pending_reviews.pop(record_id)
        review.mark_reviewed(user_id)
        review.final_status = review.determine_status()
        
        self.completed_reviews[record_id] = review
        
        if self.storage:
            self.storage.save_review(review)
        
        logger.info(f"Review closed for record {record_id}: {review.final_status}")
        return True
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get comprehensive dashboard summary."""
        decision_counts = {}
        for dt in DecisionType:
            decision_counts[dt.value] = sum(
                1 for d in self.decisions if d.decision == dt.value
            )
        
        # Analyze by dimension
        decisions_by_dimension = {}
        for decision in self.decisions:
            dim = decision.dimension or "unknown"
            if dim not in decisions_by_dimension:
                decisions_by_dimension[dim] = {dt.value: 0 for dt in DecisionType}
            decisions_by_dimension[dim][decision.decision] += 1
        
        # Analyze by column
        decisions_by_column = {}
        for decision in self.decisions:
            col = decision.column or "unknown"
            if col not in decisions_by_column:
                decisions_by_column[col] = {dt.value: 0 for dt in DecisionType}
            decisions_by_column[col][decision.decision] += 1
        
        total = len(self.pending_reviews) + len(self.completed_reviews)
        
        return {
            "pending_reviews": len(self.pending_reviews),
            "completed_reviews": len(self.completed_reviews),
            "total_decisions": len(self.decisions),
            "decision_breakdown": decision_counts,
            "decisions_by_dimension": decisions_by_dimension,
            "decisions_by_column": decisions_by_column,
            "completion_rate": (
                len(self.completed_reviews) / total if total > 0 else 0.0
            ),
            "correction_rate": (
                decision_counts.get(DecisionType.CORRECT.value, 0) / len(self.decisions)
                if self.decisions else 0.0
            )
        }
    
    def get_learning_feedback(self) -> Dict[str, Any]:
        """Extract learnings from human decisions for continuous improvement."""
        learnings = {
            "corrections": [],
            "rule_performance": {},
            "patterns": {},
            "by_dimension": {}
        }
        
        # Collect corrections
        for decision in self.decisions:
            if decision.decision == DecisionType.CORRECT.value:
                learnings["corrections"].append({
                    "record_id": decision.record_id,
                    "rule_id": decision.rule_id,
                    "column": decision.column,
                    "original_value": decision.original_value,
                    "corrected_value": decision.corrected_value,
                    "dimension": decision.dimension,
                    "reason": decision.reason,
                    "timestamp": decision.timestamp
                })
        
        # Analyze rule performance
        rule_stats = {}
        for decision in self.decisions:
            rule_id = decision.rule_id
            if rule_id not in rule_stats:
                rule_stats[rule_id] = {
                    "approve": 0, "reject": 0, "correct": 0, "override": 0, "escalate": 0
                }
            rule_stats[rule_id][decision.decision] += 1
        
        for rule_id, stats in rule_stats.items():
            total = sum(stats.values())
            learnings["rule_performance"][rule_id] = {
                "total_decisions": total,
                "approval_rate": stats["approve"] / total if total > 0 else 0,
                "rejection_rate": stats["reject"] / total if total > 0 else 0,
                "correction_rate": stats["correct"] / total if total > 0 else 0,
                "override_rate": stats["override"] / total if total > 0 else 0,
                "escalation_rate": stats["escalate"] / total if total > 0 else 0
            }
        
        # Identify problem rules (high rejection/escalation)
        learnings["patterns"]["high_rejection_rules"] = [
            rule_id for rule_id, perf in learnings["rule_performance"].items()
            if perf["rejection_rate"] > 0.3  # > 30% rejection
        ]
        
        learnings["patterns"]["high_escalation_rules"] = [
            rule_id for rule_id, perf in learnings["rule_performance"].items()
            if perf["escalation_rate"] > 0.2  # > 20% escalation
        ]
        
        # Analyze by dimension
        for decision in self.decisions:
            dim = decision.dimension or "unknown"
            if dim not in learnings["by_dimension"]:
                learnings["by_dimension"][dim] = {dt.value: 0 for dt in DecisionType}
            learnings["by_dimension"][dim][decision.decision] += 1
        
        return learnings
    
    def generate_dynamic_output(
        self,
        df: pd.DataFrame,
        rules: List[Dict[str, Any]],
        violations: List[Dict[str, Any]],
        decisions: Optional[Dict[int, str]] = None
    ) -> pd.DataFrame:
        """
        Generate output DataFrame based on rules and human decisions.
        Fully dynamic: output columns and transformations based on rules.
        
        Args:
            df: Input data
            rules: Rule definitions
            violations: Detected violations
            decisions: Human decisions from HITL review {record_id: decision}
        
        Returns:
            Output DataFrame with dynamic columns based on rules
        """
        output_df = df.copy()
        decisions = decisions or {}
        
        # Track which records had corrections
        correction_flags = {}
        
        # Apply corrections from HITL decisions
        for review in self.completed_reviews.values():
            if review.final_status == "corrected":
                for col, correction in review.corrections_applied.items():
                    if review.record_id in output_df.index:
                        output_df.loc[review.record_id, col] = correction["corrected"]
                        correction_flags[review.record_id] = True
        
        # Add dynamic metadata columns based on rule types
        dimensions = set(r.get("dimension") for r in rules if r.get("dimension"))
        
        for dimension in dimensions:
            output_df[f"_violation_{dimension}"] = False
        
        # Mark violations in output
        for violation in violations:
            dim = violation.get("dimension", "unknown")
            col_name = f"_violation_{dim}"
            
            for row_idx in violation.get("failed_rows", []):
                if row_idx in output_df.index:
                    output_df.loc[row_idx, col_name] = True
        
        # Add correction flag
        output_df["_was_corrected"] = output_df.index.isin(correction_flags)
        
        # Add review status
        output_df["_review_status"] = "not_reviewed"
        for record_id, review in self.completed_reviews.items():
            if record_id in output_df.index:
                output_df.loc[record_id, "_review_status"] = review.final_status
        
        return output_df
    
    def _count_violation_types(self, violations: List[Dict]) -> Dict[str, int]:
        """Count violations by type."""
        counts = {}
        for v in violations:
            check = v.get("check", "unknown")
            counts[check] = counts.get(check, 0) + 1
        return counts
    
    def _get_rules_context(self, violations: List[Dict]) -> Dict[str, Dict]:
        """Get rule metadata for violated rules."""
        context = {}
        for v in violations:
            rule_id = v.get("rule_id")
            if rule_id:
                context[rule_id] = {
                    "check": v.get("check"),
                    "column": v.get("column"),
                    "dimension": v.get("dimension"),
                    "severity": v.get("severity"),
                    "affected_values": v.get("affected_values"),
                    "metadata": self.rules_metadata.get(rule_id, {})
                }
        return context
    
    def _generate_review_guidance(self, review: RecordReview) -> Dict[str, Any]:
        """Generate guidance for reviewer."""
        return {
            "total_violations": len(review.violations),
            "violation_summary": review.get_violation_summary(),
            "critical_violations": [
                v for v in review.violations if v.get("severity") == "Critical"
            ],
            "suggested_action": "review_all" if len(review.violations) > 3 else "quick_review"
        }
    
    def _get_high_violation_indices(
        self,
        df: pd.DataFrame,
        violations: List[Dict],
        sample_size: int
    ) -> List[int]:
        """Get records with most violations."""
        violation_counts = {}
        for v in violations:
            for row_idx in v.get("failed_rows", []):
                violation_counts[row_idx] = violation_counts.get(row_idx, 0) + 1
        
        sorted_indices = sorted(
            violation_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [idx for idx, _ in sorted_indices[:sample_size]]
    
    def _get_stratified_indices(
        self,
        df: pd.DataFrame,
        violations: List[Dict],
        sample_size: int
    ) -> List[int]:
        """Get stratified sample across violation types."""
        violations_by_type = {}
        for v in violations:
            check_type = v.get("check", "unknown")
            if check_type not in violations_by_type:
                violations_by_type[check_type] = set()
            violations_by_type[check_type].update(v.get("failed_rows", []))
        
        indices = []
        if violations_by_type:  # Only proceed if there are violations
            per_type = max(1, sample_size // len(violations_by_type))
            
            for check_type, indices_set in violations_by_type.items():
                sample = list(indices_set)[:per_type]
                indices.extend(sample)
        
        if len(indices) < sample_size:
            remaining = [i for i in range(len(df)) if i not in indices]
            indices.extend(remaining[:sample_size - len(indices)])
        
        return indices[:sample_size]
    
    def _get_dimension_balanced_indices(
        self,
        df: pd.DataFrame,
        violations: List[Dict],
        sample_size: int
    ) -> List[int]:
        """Get sample balanced across dimensions."""
        violations_by_dimension = {}
        for v in violations:
            dim = v.get("dimension", "unknown")
            if dim not in violations_by_dimension:
                violations_by_dimension[dim] = set()
            violations_by_dimension[dim].update(v.get("failed_rows", []))
        
        indices = []
        per_dim = max(1, sample_size // len(violations_by_dimension))
        
        for dimension, indices_set in violations_by_dimension.items():
            sample = list(indices_set)[:per_dim]
            indices.extend(sample)
        
        if len(indices) < sample_size:
            remaining = [i for i in range(len(df)) if i not in indices]
            indices.extend(remaining[:sample_size - len(indices)])
        
        return indices[:sample_size]


class ReviewStorage:
    """Abstract storage backend for review decisions."""
    
    def save_review(self, review: RecordReview) -> None:
        raise NotImplementedError
    
    def load_reviews(self, batch_id: str) -> List[RecordReview]:
        raise NotImplementedError


class LocalReviewStorage(ReviewStorage):
    """Store reviews locally as JSON."""
    
    def __init__(self, storage_dir: str = "output/reviews"):
        self.storage_dir = storage_dir
        import os
        os.makedirs(storage_dir, exist_ok=True)
    
    def save_review(self, review: RecordReview) -> None:
        """Save review to JSON file."""
        file_path = f"{self.storage_dir}/review_{review.record_id}.json"
        with open(file_path, 'w') as f:
            json.dump(review.to_dict(), f, indent=2)
    
    def load_reviews(self, batch_id: str = None) -> List[RecordReview]:
        """Load all reviews from storage."""
        import os
        import glob
        
        reviews = []
        for file_path in glob.glob(f"{self.storage_dir}/review_*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    review = self._dict_to_review(data)
                    reviews.append(review)
            except Exception as e:
                logger.error(f"Failed to load review from {file_path}: {e}")
        
        return reviews
    
    def _dict_to_review(self, data: Dict) -> RecordReview:
        """Reconstruct RecordReview from dict."""
        review = RecordReview(
            data["record_id"],
            data["row_data"],
            data["violations"]
        )
        review.reviewed_at = data.get("reviewed_at")
        review.reviewed_by = data.get("reviewed_by")
        review.final_status = data.get("status", "pending")
        
        for dec_data in data.get("decisions", []):
            decision = ReviewDecision(**dec_data)
            review.add_decision(decision)
        
        return review
