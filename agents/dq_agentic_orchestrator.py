"""
LanGraph-based Agentic Data Quality Orchestrator
Implements end-to-end DQ workflow with LLM agents and HITL
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import pandas as pd
from enum import Enum

from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProcessingState(str, Enum):
    """States in the DQ pipeline."""
    INITIALIZED = "initialized"
    DATA_FETCHED = "data_fetched"
    RULES_LOADED = "rules_loaded"
    PROFILING = "profiling"
    ASSESSMENT_COMPLETE = "assessment_complete"
    REMEDIATION_IN_PROGRESS = "remediation_in_progress"
    HITL_PENDING = "hitl_pending"
    HITL_APPROVED = "hitl_approved"
    REMEDIATION_COMPLETE = "remediation_complete"
    IMPROVEMENT_ASSESSMENT = "improvement_assessment"
    COMPLETED = "completed"


class DQIssue(BaseModel):
    """Represents a data quality issue."""
    record_id: Any
    column: str
    rule_id: str
    dimension: str
    issue_type: str
    original_value: Any
    severity: str
    suggested_fix: Optional[str] = None
    confidence: Optional[float] = None


class DQAssessment(BaseModel):
    """Results of DQ assessment."""
    timestamp: str
    total_records: int
    issues_found: int
    issues_by_dimension: Dict[str, int]
    issues_by_severity: Dict[str, int]
    detailed_issues: List[DQIssue] = Field(default_factory=list)
    pass_rate: float
    before_or_after: str  # "before" or "after"


class RemediationSuggestion(BaseModel):
    """Suggested remediation for an issue."""
    issue_id: str
    original_value: Any
    suggested_value: Any
    action: str
    confidence: float
    reasoning: str
    rule_id: str


@dataclass
class PipelineState:
    """State container for the DQ pipeline."""
    # Data
    raw_data: Optional[pd.DataFrame] = None
    clean_data: Optional[pd.DataFrame] = None
    current_data: Optional[pd.DataFrame] = None
    
    # Rules
    dq_rules: Optional[pd.DataFrame] = None
    cleansing_rules: Optional[pd.DataFrame] = None
    kpi_rules: Optional[pd.DataFrame] = None
    
    # Assessments
    pre_remediation_assessment: Optional[DQAssessment] = None
    post_remediation_assessment: Optional[DQAssessment] = None
    
    # Remediations
    remediation_suggestions: List[RemediationSuggestion] = field(default_factory=list)
    applied_remediations: List[Dict[str, Any]] = field(default_factory=list)
    
    # HITL
    hitl_approvals: Dict[str, bool] = field(default_factory=dict)
    hitl_pending: bool = False
    
    # Status
    status: ProcessingState = ProcessingState.INITIALIZED
    errors: List[str] = field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)


class DQAgenticOrchestrator:
    """
    LanGraph-based orchestrator for data quality assessment and remediation.
    Orchestrates multiple agents in a state graph.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize orchestrator with config."""
        self.config = config
        self.llm = self._init_ollama()
        self.state_graph = self._build_state_graph()
        logger.info("DQ Agentic Orchestrator initialized")
    
    def _init_ollama(self) -> Ollama:
        """Initialize Ollama LLM client."""
        ollama_url = self.config.get("llm", {}).get("ollama_url", "http://localhost:11434")
        model_name = self.config.get("llm", {}).get("model", "mistral")
        
        try:
            llm = Ollama(
                base_url=ollama_url,
                model=model_name,
                temperature=self.config.get("llm", {}).get("temperature", 0.3)
            )
            logger.info(f"Ollama LLM initialized: {model_name}")
            return llm
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {e}")
            raise
    
    def _build_state_graph(self) -> StateGraph:
        """Build LanGraph state graph."""
        workflow = StateGraph(PipelineState)
        
        # Add nodes for each processing step
        workflow.add_node("fetch_data", self._fetch_data_node)
        workflow.add_node("load_rules", self._load_rules_node)
        workflow.add_node("profile_data", self._profile_data_node)
        workflow.add_node("assess_quality", self._assess_quality_node)
        workflow.add_node("decide_remediation", self._decide_remediation_node)
        workflow.add_node("generate_suggestions", self._generate_suggestions_node)
        workflow.add_node("hitl_review", self._hitl_review_node)
        workflow.add_node("apply_remediations", self._apply_remediations_node)
        workflow.add_node("reassess_quality", self._reassess_quality_node)
        workflow.add_node("generate_report", self._generate_report_node)
        workflow.add_node("persist_results", self._persist_results_node)
        
        # Set up edges
        workflow.set_entry_point("fetch_data")
        
        workflow.add_edge("fetch_data", "load_rules")
        workflow.add_edge("load_rules", "profile_data")
        workflow.add_edge("profile_data", "assess_quality")
        
        # Conditional edge: decide remediation
        workflow.add_conditional_edges(
            "assess_quality",
            self._should_remediate,
            {
                "remediate": "decide_remediation",
                "skip": "generate_report"
            }
        )
        
        workflow.add_edge("decide_remediation", "generate_suggestions")
        workflow.add_edge("generate_suggestions", "hitl_review")
        
        # Conditional edge: HITL approval
        workflow.add_conditional_edges(
            "hitl_review",
            self._hitl_approved,
            {
                "approved": "apply_remediations",
                "rejected": "generate_report"
            }
        )
        
        workflow.add_edge("apply_remediations", "reassess_quality")
        workflow.add_edge("reassess_quality", "generate_report")
        workflow.add_edge("generate_report", "persist_results")
        workflow.add_edge("persist_results", END)
        
        return workflow.compile()
    
    # Node implementations
    
    async def _fetch_data_node(self, state: PipelineState) -> PipelineState:
        """Fetch data from NeonDB or local source."""
        logger.info("Fetching data...")
        try:
            from data_io.data_source import get_data_source
            
            source = get_data_source(self.config)
            state.raw_data = source.fetch_data()
            state.current_data = state.raw_data.copy()
            state.status = ProcessingState.DATA_FETCHED
            
            logger.info(f"Data fetched: {len(state.raw_data)} records, {len(state.raw_data.columns)} columns")
        except Exception as e:
            state.errors.append(f"Data fetch failed: {str(e)}")
            logger.error(f"Data fetch error: {e}")
        
        return state
    
    async def _load_rules_node(self, state: PipelineState) -> PipelineState:
        """Load DQ, cleansing, and KPI rules."""
        logger.info("Loading rules...")
        try:
            from agents.cleansing_rule_parser import CleansingRuleParser
            
            # Load DQ rules
            if "dq_rules_path" in self.config.get("input", {}):
                dq_path = self.config["input"]["dq_rules_path"]
                state.dq_rules = pd.read_excel(dq_path) if dq_path.endswith('.xlsx') else pd.read_csv(dq_path)
            
            # Load cleansing rules
            if "cleansing_rules_path" in self.config.get("input", {}):
                cleansing_path = self.config["input"]["cleansing_rules_path"]
                state.cleansing_rules = pd.read_excel(cleansing_path) if cleansing_path.endswith('.xlsx') else pd.read_csv(cleansing_path)
            
            # Load KPI rules
            if "kpis_path" in self.config.get("input", {}):
                kpi_path = self.config["input"]["kpis_path"]
                state.kpi_rules = pd.read_csv(kpi_path)
            
            state.status = ProcessingState.RULES_LOADED
            logger.info(f"Rules loaded: DQ={len(state.dq_rules) if state.dq_rules is not None else 0}, "
                       f"Cleansing={len(state.cleansing_rules) if state.cleansing_rules is not None else 0}")
        except Exception as e:
            state.errors.append(f"Rules load failed: {str(e)}")
            logger.error(f"Rules load error: {e}")
        
        return state
    
    async def _profile_data_node(self, state: PipelineState) -> PipelineState:
        """Profile data to understand structure."""
        logger.info("Profiling data...")
        try:
            state.status = ProcessingState.PROFILING
            # Additional profiling logic can be added here
        except Exception as e:
            state.errors.append(f"Profiling failed: {str(e)}")
        
        return state
    
    async def _assess_quality_node(self, state: PipelineState) -> PipelineState:
        """Assess data quality against rules."""
        logger.info("Assessing data quality...")
        try:
            from deterministic_engine.rule_executor import DeterministicCheckEngine
            
            engine = DeterministicCheckEngine(self.config)
            assessment = engine.assess(state.current_data, state.dq_rules)
            state.pre_remediation_assessment = assessment
            state.status = ProcessingState.ASSESSMENT_COMPLETE
            
            logger.info(f"Assessment complete: {assessment.issues_found} issues, {assessment.pass_rate:.1%} pass rate")
        except Exception as e:
            state.errors.append(f"Assessment failed: {str(e)}")
            logger.error(f"Assessment error: {e}")
        
        return state
    
    def _should_remediate(self, state: PipelineState) -> str:
        """Decide if remediation is needed."""
        if state.pre_remediation_assessment is None:
            return "skip"
        
        threshold = self.config.get("thresholds", {}).get("remediation_trigger_pct", 0.05)
        issue_rate = state.pre_remediation_assessment.issues_found / state.pre_remediation_assessment.total_records
        
        return "remediate" if issue_rate >= threshold else "skip"
    
    async def _decide_remediation_node(self, state: PipelineState) -> PipelineState:
        """Prepare for remediation."""
        logger.info("Preparing remediation...")
        state.status = ProcessingState.REMEDIATION_IN_PROGRESS
        return state
    
    async def _generate_suggestions_node(self, state: PipelineState) -> PipelineState:
        """Generate remediation suggestions using LLM."""
        logger.info("Generating remediation suggestions...")
        try:
            suggestions = []
            
            if state.pre_remediation_assessment is None:
                return state
            
            # For each issue, generate suggestion
            for issue in state.pre_remediation_assessment.detailed_issues[:100]:  # Limit for now
                try:
                    suggestion = await self._llm_generate_suggestion(issue, state)
                    if suggestion:
                        suggestions.append(suggestion)
                except Exception as e:
                    logger.warning(f"Suggestion generation failed for issue: {e}")
            
            state.remediation_suggestions = suggestions
            logger.info(f"Generated {len(suggestions)} remediation suggestions")
        except Exception as e:
            state.errors.append(f"Suggestion generation failed: {str(e)}")
        
        return state
    
    async def _llm_generate_suggestion(self, issue: DQIssue, state: PipelineState) -> Optional[RemediationSuggestion]:
        """Use LLM to generate remediation suggestion for an issue."""
        try:
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="You are a data quality expert. Generate a single remediation suggestion."),
                HumanMessage(content=f"""
Column: {issue.column}
Original Value: {issue.original_value}
Issue Type: {issue.issue_type}
Rule: {issue.rule_id}
Dimension: {issue.dimension}

Suggest ONE specific value that would fix this issue. Respond in JSON format only:
{{"suggested_value": "...", "action": "...", "confidence": 0.9, "reasoning": "..."}}
                """)
            ])
            
            response = self.llm.invoke(prompt.format_messages())
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON from response
            import json
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    suggestion_data = json.loads(json_str)
                    
                    return RemediationSuggestion(
                        issue_id=f"{issue.record_id}_{issue.column}",
                        original_value=issue.original_value,
                        suggested_value=suggestion_data.get("suggested_value"),
                        action=suggestion_data.get("action", "manual_fix"),
                        confidence=suggestion_data.get("confidence", 0.7),
                        reasoning=suggestion_data.get("reasoning", ""),
                        rule_id=issue.rule_id
                    )
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response as JSON: {response_text[:200]}")
        except Exception as e:
            logger.error(f"LLM suggestion generation failed: {e}")
        
        return None
    
    async def _hitl_review_node(self, state: PipelineState) -> PipelineState:
        """Trigger HITL review process."""
        logger.info("Triggering HITL review...")
        state.hitl_pending = True
        state.status = ProcessingState.HITL_PENDING
        
        # In a real scenario, this would integrate with the HITL dashboard
        # For now, auto-approve suggestions above 0.85 confidence
        for suggestion in state.remediation_suggestions:
            if suggestion.confidence >= 0.85:
                state.hitl_approvals[suggestion.issue_id] = True
            else:
                state.hitl_approvals[suggestion.issue_id] = False
        
        logger.info(f"HITL approvals: {sum(1 for v in state.hitl_approvals.values() if v)} approved")
        return state
    
    def _hitl_approved(self, state: PipelineState) -> str:
        """Check if HITL approved remediations."""
        return "approved" if any(state.hitl_approvals.values()) else "rejected"
    
    async def _apply_remediations_node(self, state: PipelineState) -> PipelineState:
        """Apply approved remediation suggestions."""
        logger.info("Applying remediations...")
        try:
            from deterministic_engine.fix_executor import DeterministicFixEngine
            
            state.clean_data = state.current_data.copy()
            
            # Apply each approved suggestion
            for suggestion in state.remediation_suggestions:
                if state.hitl_approvals.get(suggestion.issue_id, False):
                    try:
                        # Apply the fix
                        # This is simplified; actual implementation would be more sophisticated
                        record_id, column = suggestion.issue_id.rsplit('_', 1)
                        state.clean_data.loc[state.clean_data.index == record_id, column] = suggestion.suggested_value
                        
                        state.applied_remediations.append({
                            "issue_id": suggestion.issue_id,
                            "original": suggestion.original_value,
                            "new": suggestion.suggested_value,
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.warning(f"Failed to apply suggestion {suggestion.issue_id}: {e}")
            
            state.status = ProcessingState.REMEDIATION_COMPLETE
            logger.info(f"Applied {len(state.applied_remediations)} remediations")
        except Exception as e:
            state.errors.append(f"Remediation application failed: {str(e)}")
        
        return state
    
    async def _reassess_quality_node(self, state: PipelineState) -> PipelineState:
        """Reassess quality after remediation."""
        logger.info("Reassessing quality after remediation...")
        try:
            from deterministic_engine.rule_executor import DeterministicCheckEngine
            
            engine = DeterministicCheckEngine(self.config)
            assessment = engine.assess(state.clean_data, state.dq_rules)
            state.post_remediation_assessment = assessment
            state.status = ProcessingState.IMPROVEMENT_ASSESSMENT
            
            logger.info(f"Post-remediation assessment: {assessment.issues_found} issues, {assessment.pass_rate:.1%} pass rate")
        except Exception as e:
            state.errors.append(f"Reassessment failed: {str(e)}")
        
        return state
    
    async def _generate_report_node(self, state: PipelineState) -> PipelineState:
        """Generate DQ report and KPIs."""
        logger.info("Generating report...")
        try:
            # Report generation logic
            pass
        except Exception as e:
            state.errors.append(f"Report generation failed: {str(e)}")
        
        return state
    
    async def _persist_results_node(self, state: PipelineState) -> PipelineState:
        """Persist results to NeonDB."""
        logger.info("Persisting results...")
        try:
            from data_io.data_source import get_data_source
            
            source = get_data_source(self.config)
            
            # Persist clean data
            if state.clean_data is not None and not state.clean_data.empty:
                source.persist_data(state.clean_data, table_name="policy_data_clean")
            
            # Persist assessment results
            assessment_data = {
                "pre_assessment": state.pre_remediation_assessment.dict() if state.pre_remediation_assessment else None,
                "post_assessment": state.post_remediation_assessment.dict() if state.post_remediation_assessment else None,
                "applied_remediations": state.applied_remediations,
                "timestamp": datetime.now().isoformat()
            }
            
            source.persist_assessment(assessment_data)
            state.status = ProcessingState.COMPLETED
            logger.info("Results persisted")
        except Exception as e:
            state.errors.append(f"Persistence failed: {str(e)}")
        
        return state
    
    async def execute(self, initial_config: Dict[str, Any]) -> PipelineState:
        """Execute the DQ pipeline."""
        initial_state = PipelineState(config=initial_config)
        final_state = self.state_graph.invoke(initial_state)
        return final_state
