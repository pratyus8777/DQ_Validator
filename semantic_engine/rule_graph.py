"""
Semantic Rule Engine - Interprets unstructured governance inputs using free LLMs.
Converts business artifacts (CSVs, text) into normalized rule graphs.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class RuleDimension(str, Enum):
    """Data quality dimensions."""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    UNIQUENESS = "uniqueness"
    RELEVANCE = "relevance"


class CheckType(str, Enum):
    """Deterministic check types."""
    NOT_NULL = "not_null"
    NOT_BLANK = "not_blank"
    REGEX = "regex"
    RANGE = "range"
    LENGTH = "length"
    UNIQUE = "unique"
    UNIQUE_IN_GROUP = "unique_in_group"
    EQUALS_FIELD = "equals_field"
    REGEX_FIELD = "regex_field"
    DATE_FORMAT = "date_format"
    NUMERIC = "numeric"
    ENUM = "enum"
    REFERENCES = "references"
    CUSTOM = "custom"


class FixType(str, Enum):
    """Fix action types."""
    IF_NULL_FILL = "if_null_fill"
    STANDARDIZE = "standardize"
    PARSE_DATE = "parse_date"
    DEDUPE = "dedupe"
    MERGE = "merge"
    LLM_FIX_TEXT = "llm_fix_text"
    LLM_FIX_EMAIL = "llm_fix_email"
    LLM_FIX_PHONE = "llm_fix_phone"
    REJECT = "reject"
    FLAG_FOR_REVIEW = "flag_for_review"


@dataclass
class NormalizedRule:
    """Normalized rule representation (output of semantic engine)."""
    
    rule_id: str
    dimension: RuleDimension
    column: str
    check_type: CheckType
    description: str
    
    # Check parameters
    parameters: Dict[str, Any]
    
    # Fix actions (ordered)
    fix_actions: List[Dict[str, Any]]
    
    # Metadata
    severity: str  # "Critical", "High", "Medium", "Low"
    enabled: bool = True
    created_at: str = None
    source_file: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedKPI:
    """Normalized KPI representation."""
    
    kpi_id: str
    name: str
    description: str
    dimension: Optional[RuleDimension]
    
    # Computation
    function: str  # e.g., "pass_rate", "pass_count", "fail_rate"
    parameters: Dict[str, Any]
    
    # Targets
    target_value: Optional[float] = None
    target_condition: Optional[str] = None  # "gte", "lte", "eq", "range"
    
    # Metadata
    created_at: str = None
    source_file: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RuleRegistry:
    """Registry of all normalized rules."""
    
    def __init__(self):
        self.rules: Dict[str, NormalizedRule] = {}
        self.rules_by_dimension: Dict[RuleDimension, List[NormalizedRule]] = {
            dim: [] for dim in RuleDimension
        }
        self.rules_by_column: Dict[str, List[NormalizedRule]] = {}
    
    def register_rule(self, rule: NormalizedRule) -> None:
        """Register a normalized rule."""
        self.rules[rule.rule_id] = rule
        self.rules_by_dimension[rule.dimension].append(rule)
        
        if rule.column not in self.rules_by_column:
            self.rules_by_column[rule.column] = []
        self.rules_by_column[rule.column].append(rule)
        
        logger.debug(f"Registered rule: {rule.rule_id} ({rule.dimension}) on {rule.column}")
    
    def get_rules_for_dimension(self, dimension: RuleDimension) -> List[NormalizedRule]:
        """Get all rules for a dimension."""
        return self.rules_by_dimension.get(dimension, [])
    
    def get_rules_for_column(self, column: str) -> List[NormalizedRule]:
        """Get all rules for a column."""
        return self.rules_by_column.get(column, [])
    
    def get_rule(self, rule_id: str) -> Optional[NormalizedRule]:
        """Get a specific rule."""
        return self.rules.get(rule_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize all rules."""
        return {
            rule_id: rule.to_dict()
            for rule_id, rule in self.rules.items()
        }


class KPIRegistry:
    """Registry of normalized KPIs."""
    
    def __init__(self):
        self.kpis: Dict[str, NormalizedKPI] = {}
        self.kpis_by_dimension: Dict[Optional[RuleDimension], List[NormalizedKPI]] = {
            dim: [] for dim in list(RuleDimension) + [None]
        }
    
    def register_kpi(self, kpi: NormalizedKPI) -> None:
        """Register a normalized KPI."""
        self.kpis[kpi.kpi_id] = kpi
        self.kpis_by_dimension[kpi.dimension].append(kpi)
        logger.debug(f"Registered KPI: {kpi.kpi_id}")
    
    def get_kpis_for_dimension(self, dimension: Optional[RuleDimension]) -> List[NormalizedKPI]:
        """Get KPIs for a dimension."""
        return self.kpis_by_dimension.get(dimension, [])
    
    def get_kpi(self, kpi_id: str) -> Optional[NormalizedKPI]:
        """Get a specific KPI."""
        return self.kpis.get(kpi_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize all KPIs."""
        return {
            kpi_id: kpi.to_dict()
            for kpi_id, kpi in self.kpis.items()
        }


class SemanticRuleGraph:
    """Complete normalized semantic rule graph."""
    
    def __init__(self):
        self.rules = RuleRegistry()
        self.kpis = KPIRegistry()
        self.created_at = datetime.utcnow().isoformat()
        self.version = "1.0"
        self.metadata: Dict[str, Any] = {}
    
    def add_rule(self, rule: NormalizedRule) -> None:
        """Add a rule to the graph."""
        self.rules.register_rule(rule)
    
    def add_kpi(self, kpi: NormalizedKPI) -> None:
        """Add a KPI to the graph."""
        self.kpis.register_kpi(kpi)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get graph summary."""
        return {
            "total_rules": len(self.rules.rules),
            "rules_by_dimension": {
                dim.value: len(self.rules.rules_by_dimension[dim])
                for dim in RuleDimension
            },
            "total_kpis": len(self.kpis.kpis),
            "created_at": self.created_at,
            "version": self.version
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete graph."""
        return {
            "created_at": self.created_at,
            "version": self.version,
            "summary": self.get_summary(),
            "rules": self.rules.to_dict(),
            "kpis": self.kpis.to_dict(),
            "metadata": self.metadata
        }
    
    def save_to_file(self, path: str) -> None:
        """Save graph to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved semantic rule graph to: {path}")
    
    def load_from_file(cls, path: str) -> 'SemanticRuleGraph':
        """Load graph from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        graph = cls()
        graph.created_at = data.get("created_at")
        graph.version = data.get("version")
        graph.metadata = data.get("metadata", {})
        
        # Load rules
        for rule_id, rule_data in data.get("rules", {}).items():
            rule_data["dimension"] = RuleDimension(rule_data["dimension"])
            rule_data["check_type"] = CheckType(rule_data["check_type"])
            rule_data["fix_actions"] = rule_data.get("fix_actions", [])
            rule = NormalizedRule(**rule_data)
            graph.add_rule(rule)
        
        # Load KPIs
        for kpi_id, kpi_data in data.get("kpis", {}).items():
            if kpi_data["dimension"]:
                kpi_data["dimension"] = RuleDimension(kpi_data["dimension"])
            kpi = NormalizedKPI(**kpi_data)
            graph.add_kpi(kpi)
        
        logger.info(f"Loaded semantic rule graph from: {path}")
        return graph


# Global registries
RULE_REGISTRY = RuleRegistry()
KPI_REGISTRY = KPIRegistry()
SEMANTIC_GRAPH = SemanticRuleGraph()
