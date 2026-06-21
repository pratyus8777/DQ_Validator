"""
Semantic Rule Interpreter
Converts natural language rules into normalized rule representations using LLMs.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for communicating with Ollama local LLM service."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama client."""
        self.base_url = base_url
        self.model = "llama2"
        self._available = None
    
    @property
    def available(self) -> bool:
        """Check if Ollama service is available."""
        if self._available is None:
            self._available = self.is_available()
        return self._available
    
    def generate(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate text using Ollama."""
        try:
            model = model or self.model
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama: {e}")
            return ""
    
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False


class MockOllamaClient:
    """A lightweight mock Ollama client used when the real service is unavailable.

    It provides the same interface but returns safe defaults so the semantic
    pipeline can run in environments without a local Ollama installation.
    """
    def __init__(self):
        self.base_url = "mock://local"
        self.model = "mock"
        self._available = True

    @property
    def available(self) -> bool:
        return True

    def generate(self, prompt: str, model: Optional[str] = None) -> str:
        # Return an empty string which signals the interpreter to use deterministic
        # heuristics rather than a model response.
        return ""

    def is_available(self) -> bool:
        return True


class RuleCompiler:
    """Compiles semantic rules into deterministic execution plans."""
    
    def __init__(self):
        """Initialize rule compiler."""
        self.compiled_rules = {}
    
    def compile(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Compile a semantic rule into deterministic form."""
        return {
            "rule_id": rule.get("rule_id"),
            "checks": rule.get("checks", []),
            "fixes": rule.get("fixes", []),
            "metadata": rule.get("metadata", {})
        }
    
    def compile_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compile multiple semantic rules into deterministic form."""
        compiled = {}
        for rule in rules:
            compiled_rule = self.compile(rule)
            rule_id = rule.get("rule_id", "unknown")
            compiled[rule_id] = compiled_rule
        return compiled


class SemanticRuleInterpreter:
    """Interprets natural language rules using LLMs."""
    
    def __init__(self, llm_client: OllamaClient):
        """Initialize semantic rule interpreter."""
        self.llm_client = llm_client
        self.rules = {}
    
    def interpret_rule(self, rule_text: str) -> Dict[str, Any]:
        """Interpret natural language rule into structured format."""
        logger.info(f"Interpreting rule: {rule_text[:100]}...")
        
        # For now, return a basic structure
        return {
            "rule_id": "rule_001",
            "dimension": "accuracy",
            "description": rule_text,
            "checks": [],
            "fixes": []
        }
    
    def interpret_rules_from_csv(self, csv_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Interpret rules from CSV data."""
        rules = []
        for row in csv_data:
            rule = self.interpret_rule(str(row))
            rules.append(rule)
        return rules

    # Backwards-compatible wrapper expected by higher-level code
    def interpret_rule_csv(self, df) -> List[Dict[str, Any]]:
        """Interpret rules provided as a pandas DataFrame or list of dicts."""
        try:
            import pandas as pd
            if isinstance(df, pd.DataFrame):
                records = df.to_dict(orient="records")
            else:
                records = list(df)
        except Exception:
            records = list(df)
        return self.interpret_rules_from_csv(records)

    def interpret_kpi_csv(self, df, available_dimensions: List[str] = None) -> List[Dict[str, Any]]:
        """Interpret KPI definitions from a DataFrame or list.

        This is a lightweight implementation that returns simple KPI placeholders
        when no detailed semantic parsing is available.
        """
        kpis = []
        try:
            import pandas as pd
            if isinstance(df, pd.DataFrame):
                records = df.to_dict(orient="records")
            else:
                records = list(df)
        except Exception:
            records = list(df)

        for i, r in enumerate(records):
            kpis.append({
                "kpi_id": f"kpi_{i+1}",
                "name": r.get("KPI", f"kpi_{i+1}") if isinstance(r, dict) else str(r),
                "dimensions": available_dimensions or []
            })
        return kpis
