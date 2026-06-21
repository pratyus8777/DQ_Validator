import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataProfiler:
    """
    Comprehensive data profiling engine.
    Analyzes data structure, types, distributions for each column.
    """
    
    def __init__(self):
        self.profiles = {}
    
    def profile_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Profile entire dataset."""
        profile = {
            "timestamp": datetime.now().isoformat(),
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": {}
        }
        
        for col in df.columns:
            profile["columns"][col] = self._profile_column(df, col)
        
        self.profiles[id(df)] = profile
        return profile
    
    def _profile_column(self, df: pd.DataFrame, col: str) -> Dict[str, Any]:
        """Profile a single column."""
        series = df[col]
        
        profile = {
            "name": col,
            "dtype": str(series.dtype),
            "non_null_count": series.notna().sum(),
            "null_count": series.isna().sum(),
            "null_percentage": (series.isna().sum() / len(series) * 100) if len(series) > 0 else 0,
            "unique_count": series.nunique(),
            "unique_percentage": (series.nunique() / len(series) * 100) if len(series) > 0 else 0,
            "sample_values": series.dropna().head(5).tolist()
        }
        
        # Type-specific profiling
        if pd.api.types.is_numeric_dtype(series):
            profile.update({
                "min": float(series.min()) if series.notna().any() else None,
                "max": float(series.max()) if series.notna().any() else None,
                "mean": float(series.mean()) if series.notna().any() else None,
                "median": float(series.median()) if series.notna().any() else None,
                "std": float(series.std()) if series.notna().any() else None
            })
        
        elif pd.api.types.is_string_dtype(series):
            non_null = series.dropna()
            if len(non_null) > 0:
                profile.update({
                    "min_length": int(non_null.str.len().min()),
                    "max_length": int(non_null.str.len().max()),
                    "avg_length": float(non_null.str.len().mean())
                })
        
        return profile


class DynamicRuleManager:
    """
    Manages rule execution with session-based overrides.
    Session rules override defaults but reset on termination.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_rules = None
        self.session_rules = {}  # column -> custom rule
        self.session_id = None
    
    def start_session(self, session_id: str):
        """Start a new rule session."""
        self.session_id = session_id
        self.session_rules = {}
        logger.info(f"Rule session started: {session_id}")
    
    def end_session(self):
        """End rule session and clear overrides."""
        logger.info(f"Rule session ended: {self.session_id}. Clearing {len(self.session_rules)} overrides.")
        self.session_id = None
        self.session_rules = {}
    
    def set_column_rule(self, column: str, rule_text: str, llm_client=None):
        """
        Set custom rule for column (LLM-interpreted).
        If LLM provided, interpret the rule text into structured format.
        """
        if llm_client and llm_client.available:
            # Use LLM to interpret rule
            interpreted = self._interpret_rule_with_llm(rule_text, column, llm_client)
            self.session_rules[column] = interpreted
            logger.info(f"Column '{column}' rule updated (LLM interpreted): {interpreted}")
        else:
            # Store as-is for later interpretation or heuristic application
            self.session_rules[column] = {
                "original_text": rule_text,
                "column": column,
                "created_at": datetime.now().isoformat(),
                "interpreted": False
            }
            logger.warning(f"Column '{column}' rule stored without LLM interpretation")
    
    def _interpret_rule_with_llm(self, rule_text: str, column: str, llm_client) -> Dict[str, Any]:
        """Use LLM to interpret natural language rule."""
        prompt = f"""
Interpret this data quality rule for column '{column}' and return a JSON structure:
Rule: {rule_text}

Response format (JSON):
{{
  "column": "{column}",
  "rule_type": "not_null|regex|date_format|range|in_set|custom",
  "parameters": "rule-specific parameters",
  "description": "human readable description",
  "check_type": "deterministic|semantic",
  "confidence": 0.0 to 1.0
}}

Return ONLY valid JSON.
"""
        try:
            response = llm_client.complete(prompt)
            if response:
                import json
                result = json.loads(response)
                result["column"] = column
                result["interpreted"] = True
                return result
        except Exception as e:
            logger.error(f"LLM rule interpretation failed: {e}")
        
        return {
            "column": column,
            "original_text": rule_text,
            "interpreted": False,
            "error": "Interpretation failed"
        }
    
    def get_effective_rules(self, df: pd.DataFrame, base_rules_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get effective rules for session.
        Applies session overrides on top of base rules.
        """
        effective = base_rules_df.copy()
        
        # Normalize column name (handle both 'cde' and 'CDE')
        col_name = 'CDE' if 'CDE' in effective.columns else 'cde' if 'cde' in effective.columns else None
        
        if not col_name:
            logger.warning("Could not find column name field in rules (expected 'cde' or 'CDE')")
            return effective
        
        # Apply session overrides
        for col, session_rule in self.session_rules.items():
            if session_rule.get("interpreted"):
                # Find and replace rule for this column
                col_mask = effective[col_name].astype(str) == col
                if col_mask.any():
                    # Update matching rules
                    if "parameters" in session_rule:
                        effective.loc[col_mask, "parameters"] = session_rule.get("parameters", "")
                    if "rule_type" in session_rule:
                        effective.loc[col_mask, "check_type"] = session_rule.get("rule_type", "")
                    logger.debug(f"Applied session override for column '{col}'")
                else:
                    # Add new rule
                    new_rule = {
                        "rule_id": f"session_{col}_{self.session_id}",
                        col_name: col,
                        "check_type": session_rule.get("rule_type", "custom"),
                        "parameters": session_rule.get("parameters", ""),
                        "dimension": "accuracy",
                        "description": session_rule.get("description", "Session rule")
                    }
                    effective = pd.concat([effective, pd.DataFrame([new_rule])], ignore_index=True)
                    logger.debug(f"Added new session rule for column '{col}'")
        
        return effective


class ProfilingOrchestrator:
    """
    AI-driven execution planner + aggregator.
    Coordinates profiling, rule management, and assessment.
    """

    def __init__(self, agents, llm_client=None):
        self.agents = agents
        self.llm = llm_client
        self.profiler = DataProfiler()
        self.rule_manager = DynamicRuleManager({})

    def run(self, context: dict) -> dict:
        """Execute profiling and rule orchestration."""
        # Start session
        session_id = context.get("session_id", "default")
        self.rule_manager.start_session(session_id)
        
        try:
            # Profile data
            data_profile = self.profiler.profile_dataset(context.get("data"))
            
            # Get effective rules (with session overrides)
            base_rules = context.get("dq_rules")
            effective_rules = self.rule_manager.get_effective_rules(
                context.get("data"),
                base_rules
            )
            
            # Execute agents with effective rules
            ordered_agents = self._plan_execution(context)
            context["dq_rules"] = effective_rules
            context["data_profile"] = data_profile
            
            results = []
            for agent in ordered_agents:
                results.append(agent.run(context))
            
            return {
                "profiling_results": results,
                "data_profile": data_profile,
                "effective_rules": effective_rules,
                "session_rules_applied": len(self.rule_manager.session_rules)
            }
        finally:
            # End session
            self.rule_manager.end_session()

    def _plan_execution(self, context):
        """Plan agent execution order."""
        if not self.llm or not self.llm.available:
            return self.agents

        prompt = """
        Given data quality dimensions, prioritize execution order
        for fastest risk detection and optimal performance.
        """
        _ = self.llm.complete(prompt)

        # Deterministic fallback
        return self.agents
    
    def set_session_rule(self, column: str, rule_text: str):
        """Allow external setting of session rules."""
        self.rule_manager.set_column_rule(column, rule_text, self.llm)
