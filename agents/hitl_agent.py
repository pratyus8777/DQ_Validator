"""
HITL (Human-In-The-Loop) Workflow Agent
Manages user review, approval, and feedback integration
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ReviewItem(BaseModel):
    """Item for human review."""
    item_id: str
    record_id: Any
    column: str
    original_value: Any
    suggested_value: Any
    rule_id: str
    confidence: float
    reasoning: str
    issue_type: str


class ReviewResult(BaseModel):
    """Result of human review."""
    item_id: str
    approved: bool
    user_feedback: Optional[str] = None
    user_suggestion: Optional[Any] = None
    timestamp: str


class HITLAgent:
    """
    Manages human-in-the-loop review process.
    - Presents remediations for user approval
    - Captures user feedback and alternative suggestions
    - Integrates approved changes back into the pipeline
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pending_reviews: List[ReviewItem] = []
        self.review_results: List[ReviewResult] = []
        self.storage = None  # Will be set by orchestrator
    
    def prepare_review_batch(
        self,
        issues: List[Dict[str, Any]],
        batch_size: int = 100,
        min_confidence: float = 0.5
    ) -> List[ReviewItem]:
        """
        Prepare issues for human review.
        Filters by confidence and batch size.
        """
        review_items = []
        
        for issue in issues:
            # Skip very high confidence items (deterministic fixes)
            confidence = issue.get("confidence", 0)
            if confidence >= 0.99:
                continue
            
            item = ReviewItem(
                item_id=f"{issue.get('record_id')}_{issue.get('column')}",
                record_id=issue.get("record_id"),
                column=issue.get("column"),
                original_value=issue.get("original_value"),
                suggested_value=issue.get("suggested_value"),
                rule_id=issue.get("rule_id"),
                confidence=confidence,
                reasoning=issue.get("reasoning", ""),
                issue_type=issue.get("issue_type", "")
            )
            review_items.append(item)
        
        # Sort by confidence (lower confidence first)
        review_items.sort(key=lambda x: x.confidence)
        
        self.pending_reviews = review_items[:batch_size]
        logger.info(f"Prepared {len(self.pending_reviews)} items for review")
        
        return self.pending_reviews
    
    def generate_review_summary(self, items: Optional[List[ReviewItem]] = None) -> str:
        """Generate human-readable summary of items for review."""
        if items is None:
            items = self.pending_reviews
        
        if not items:
            return "No items pending review."
        
        summary = f"""
HUMAN REVIEW REQUIRED
====================
Total items to review: {len(items)}

Items are sorted by confidence level (lowest to highest).
Please review each suggestion and approve or provide feedback.

Summary by dimension:
"""
        
        issues_by_type = {}
        for item in items:
            issue_type = item.issue_type
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = 0
            issues_by_type[issue_type] += 1
        
        for issue_type, count in sorted(issues_by_type.items(), key=lambda x: -x[1]):
            summary += f"  - {issue_type}: {count}\n"
        
        return summary
    
    def get_review_item(self, index: int) -> Optional[ReviewItem]:
        """Get a specific review item by index."""
        if 0 <= index < len(self.pending_reviews):
            return self.pending_reviews[index]
        return None
    
    def submit_review(
        self,
        item_id: str,
        approved: bool,
        user_feedback: Optional[str] = None,
        user_suggestion: Optional[Any] = None
    ) -> ReviewResult:
        """Submit review result for a single item."""
        result = ReviewResult(
            item_id=item_id,
            approved=approved,
            user_feedback=user_feedback,
            user_suggestion=user_suggestion,
            timestamp=datetime.now().isoformat()
        )
        
        self.review_results.append(result)
        logger.info(f"Review submitted for {item_id}: {'approved' if approved else 'rejected'}")
        
        return result
    
    def get_approval_summary(self) -> Dict[str, Any]:
        """Get summary of approvals."""
        total = len(self.review_results)
        approved = sum(1 for r in self.review_results if r.approved)
        rejected = total - approved
        
        return {
            "total_reviewed": total,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": (approved / total * 100) if total > 0 else 0,
            "items_with_feedback": sum(1 for r in self.review_results if r.user_feedback)
        }
    
    def get_approved_changes(self) -> List[Dict[str, Any]]:
        """Get all approved changes."""
        approved_changes = []
        
        for result in self.review_results:
            if result.approved:
                # Find the original item
                item = next(
                    (item for item in self.pending_reviews if item.item_id == result.item_id),
                    None
                )
                
                if item:
                    approved_changes.append({
                        "item_id": result.item_id,
                        "record_id": item.record_id,
                        "column": item.column,
                        "original_value": item.original_value,
                        "suggested_value": result.user_suggestion or item.suggested_value,
                        "confidence": item.confidence,
                        "timestamp": result.timestamp
                    })
        
        logger.info(f"Returning {len(approved_changes)} approved changes")
        return approved_changes
    
    def integrate_feedback(
        self,
        learning_store: Any
    ):
        """Integrate user feedback into learning store."""
        feedback_items = []
        
        for result in self.review_results:
            if result.approved and result.user_suggestion is not None:
                # Find the original item
                item = next(
                    (item for item in self.pending_reviews if item.item_id == result.item_id),
                    None
                )
                
                if item:
                    feedback_items.append({
                        "cde": item.column,
                        "old": item.original_value,
                        "new": result.user_suggestion,
                        "rule_id": item.rule_id,
                        "timestamp": result.timestamp
                    })
        
        if feedback_items and learning_store:
            try:
                learning_store.persist_feedback(feedback_items)
                logger.info(f"Integrated {len(feedback_items)} feedback items")
            except Exception as e:
                logger.error(f"Failed to integrate feedback: {e}")
    
    def get_review_status(self) -> Dict[str, Any]:
        """Get current review status."""
        return {
            "pending_reviews": len(self.pending_reviews),
            "completed_reviews": len(self.review_results),
            "approval_summary": self.get_approval_summary(),
            "timestamp": datetime.now().isoformat()
        }


class InteractiveHITLInterface:
    """
    Interactive interface for HITL review process.
    Can be used with CLI, web dashboard, or API.
    """
    
    def __init__(self, hitl_agent: HITLAgent):
        self.agent = hitl_agent
        self.current_index = 0
    
    def start_review(self):
        """Start the review process."""
        print(self.agent.generate_review_summary())
        print("\nStarting review process...")
        print(f"Total items: {len(self.agent.pending_reviews)}\n")
    
    def show_next_item(self) -> bool:
        """Show next item for review."""
        item = self.agent.get_review_item(self.current_index)
        
        if item is None:
            print("Review complete!")
            return False
        
        print(f"\n{'='*60}")
        print(f"Item {self.current_index + 1}/{len(self.agent.pending_reviews)}")
        print(f"{'='*60}")
        print(f"Record ID: {item.record_id}")
        print(f"Column: {item.column}")
        print(f"Original Value: {item.original_value}")
        print(f"Suggested Fix: {item.suggested_value}")
        print(f"Confidence: {item.confidence:.1%}")
        print(f"Issue Type: {item.issue_type}")
        print(f"Reasoning: {item.reasoning}")
        print(f"\nRule: {item.rule_id}")
        
        return True
    
    def review_current(self, approved: bool, feedback: str = "", suggestion: Any = None):
        """Submit review for current item."""
        item = self.agent.get_review_item(self.current_index)
        
        if item:
            self.agent.submit_review(
                item.item_id,
                approved,
                feedback or None,
                suggestion or None
            )
            self.current_index += 1
            return True
        
        return False
    
    def show_summary(self):
        """Show review summary."""
        summary = self.agent.get_approval_summary()
        print(f"\n{'='*60}")
        print("REVIEW SUMMARY")
        print(f"{'='*60}")
        print(f"Total Reviewed: {summary['total_reviewed']}")
        print(f"Approved: {summary['approved']}")
        print(f"Rejected: {summary['rejected']}")
        print(f"Approval Rate: {summary['approval_rate']:.1f}%")
        print(f"Items with Feedback: {summary['items_with_feedback']}")
