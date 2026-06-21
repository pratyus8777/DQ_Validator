"""
AI-Agent-Driven Data Quality Platform
Semantic Rule Understanding · Deterministic Enforcement · HITL · Free LLMs
Main orchestration and pipeline execution using LanGraph
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import uuid

from agents.dq_agentic_orchestrator import DQAgenticOrchestrator, PipelineState
from deterministic_engine.dynamic_rule_executor import DynamicRuleExecutor
from deterministic_engine.assessment_engine import AssessmentEngine, ReportGenerator
from agents.hitl_agent import HITLAgent, InteractiveHITLInterface
from data_io.neondb_store import NeonDBLearningStore
from hybrid_runtime import load_hybrid_runtime
from logging_config import setup_logging, get_logger
from rules_parser import RulesParser

import pandas as pd

logger = get_logger(__name__)


class AgenticDQPipeline:
    """
    End-to-end agentic DQ pipeline using LanGraph.
    Orchestrates profiling, assessment, remediation, and HITL.
    """
    
    def __init__(self, config_path: str):
        """Initialize pipeline."""
        logger.info("="*80)
        logger.info("AI-Agent-Driven Data Quality Platform (Agentic)")
        logger.info("="*80)
        
        self.config = self._load_config(config_path)
        self.run_id = str(uuid.uuid4())[:8]
        
        # Initialize components
        self.orchestrator = DQAgenticOrchestrator(self.config)
        self.rule_executor = DynamicRuleExecutor(self.config)
        self.assessment_engine = AssessmentEngine(self.config)
        self.hitl_agent = HITLAgent(self.config)
        
        # Storage
        self.storage = None
        self._init_storage()
        
        logger.info(f"Pipeline initialized with run_id: {self.run_id}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML."""
        try:
            if not os.path.exists(config_path):
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return self._get_default_config()
            
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"Config loaded from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "mode": "hybrid",
            "llm": {
                "ollama_url": "http://localhost:11434",
                "model": "mistral",
                "temperature": 0.3
            },
            "input": {
                "sample_data": "data/Sample_Policy_Data.csv",
                "dq_rules_path": "data/DQ_Rule_Repository-Policy.csv",
                "cleansing_rules_path": "data/Guidewire_Policy_DataCleansing_Rules.csv",
                "kpis_path": "data/DQ_Dashboard_KPIs.csv"
            },
            "output": {
                "type": "local",
                "location": "output/"
            },
            "thresholds": {
                "remediation_trigger_pct": 0.05
            },
            "processing": {
                "hitl_enabled": True,
                "batch_size": 100,
                "min_confidence": 0.5
            }
        }
    
    def _init_storage(self):
        """Initialize storage (NeonDB or local)."""
        try:
            if self.config.get("output", {}).get("type") == "neondb":
                conn_str = self.config.get("neondb", {}).get("connection_string")
                if conn_str:
                    self.storage = NeonDBLearningStore(conn_str)
                    logger.info("NeonDB storage initialized")
            else:
                logger.info("Using local storage")
        except Exception as e:
            logger.warning(f"Storage initialization failed: {e}, using local only")
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the full DQ pipeline."""
        logger.info("Starting DQ pipeline execution...")
        
        try:
            # Load data
            data = self._load_data()
            if data is None or data.empty:
                logger.error("Failed to load data")
                return {"status": "failed", "error": "No data loaded"}
            
            logger.info(f"Loaded {len(data)} records")
            
            # Load rules
            rules = self._load_rules()
            if rules is None:
                logger.error("Failed to load rules")
                return {"status": "failed", "error": "No rules loaded"}
            
            logger.info(f"Loaded {len(rules)} DQ rules")
            
            # Phase 1: Profiling & Assessment
            logger.info("\n" + "="*60)
            logger.info("PHASE 1: DATA PROFILING & ASSESSMENT")
            logger.info("="*60)
            
            violations, issues_df = self.rule_executor.execute_all_rules(data, rules)
            logger.info(f"Found {len(violations)} violations")
            
            # Generate assessment
            assessment_id = f"assessment_pre_{self.run_id}"
            pre_assessment = self.assessment_engine.generate_assessment(
                data, violations, assessment_id, phase="before"
            )
            
            self._print_assessment_summary(pre_assessment)
            
            # Check if remediation needed
            issue_rate = len(violations) / len(data) if len(data) > 0 else 0
            threshold = self.config.get("thresholds", {}).get("remediation_trigger_pct", 0.05)
            remediation_needed = issue_rate >= threshold
            
            logger.info(f"Issue rate: {issue_rate:.1%}, Threshold: {threshold:.1%}")
            logger.info(f"Remediation {'REQUIRED' if remediation_needed else 'NOT REQUIRED'}")
            
            if not remediation_needed:
                logger.info("Data quality exceeds threshold - no remediation needed")
                return self._finalize_results(data, pre_assessment, None, None)
            
            # Phase 2: Generate Remediation Suggestions
            logger.info("\n" + "="*60)
            logger.info("PHASE 2: REMEDIATION SUGGESTION GENERATION")
            logger.info("="*60)
            
            suggestions = await self._generate_suggestions(violations)
            logger.info(f"Generated {len(suggestions)} remediation suggestions")
            
            # Phase 3: HITL Review
            logger.info("\n" + "="*60)
            logger.info("PHASE 3: HUMAN-IN-THE-LOOP REVIEW")
            logger.info("="*60)
            
            approved_changes = await self._conduct_hitl_review(violations)
            logger.info(f"HITL approved {len(approved_changes)} changes")
            
            # Phase 4: Apply Remediations
            logger.info("\n" + "="*60)
            logger.info("PHASE 4: APPLY APPROVED REMEDIATIONS")
            logger.info("="*60)
            
            clean_data = self._apply_remediations(data, approved_changes)
            logger.info(f"Applied remediations to {len(approved_changes)} issues")
            
            # Phase 5: Reassessment
            logger.info("\n" + "="*60)
            logger.info("PHASE 5: POST-REMEDIATION ASSESSMENT")
            logger.info("="*60)
            
            post_violations, _ = self.rule_executor.execute_all_rules(clean_data, rules)
            assessment_id = f"assessment_post_{self.run_id}"
            post_assessment = self.assessment_engine.generate_assessment(
                clean_data, post_violations, assessment_id, phase="after"
            )
            
            self._print_assessment_summary(post_assessment)
            
            # Generate improvement report
            improvement_report = self.assessment_engine.generate_improvement_report(
                pre_assessment, post_assessment
            )
            
            self._print_improvement_summary(improvement_report)
            
            # Persist results
            logger.info("\n" + "="*60)
            logger.info("PHASE 6: PERSIST RESULTS")
            logger.info("="*60)
            
            await self._persist_results(clean_data, pre_assessment, post_assessment, approved_changes)
            
            logger.info("Pipeline execution completed successfully")
            
            return {
                "status": "success",
                "run_id": self.run_id,
                "pre_assessment": pre_assessment,
                "post_assessment": post_assessment,
                "improvement_report": improvement_report,
                "approved_changes": len(approved_changes),
                "clean_data_records": len(clean_data)
            }
        
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}
    
    def _load_data(self) -> Optional[pd.DataFrame]:
        """Load input data."""
        try:
            data_path = self.config.get("input", {}).get("sample_data")
            
            if data_path and os.path.exists(data_path):
                if data_path.endswith('.csv'):
                    return pd.read_csv(data_path)
                elif data_path.endswith('.xlsx'):
                    return pd.read_excel(data_path)
            
            logger.error(f"Data file not found: {data_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return None
    
    def _load_rules(self) -> Optional[pd.DataFrame]:
        """Load DQ rules using smart parser for descriptive rules."""
        try:
            rules_path = self.config.get("input", {}).get("dq_rules_path")
            
            if rules_path and os.path.exists(rules_path):
                # Use smart parser to convert descriptive rules to executable
                executable_rules = RulesParser.parse_descriptive_rules(rules_path)
                
                if not executable_rules.empty:
                    logger.info(f"Parsed {len(executable_rules)} executable rules from {rules_path}")
                    return executable_rules
            
            logger.error(f"Rules file not found or empty: {rules_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def _generate_suggestions(self, violations) -> list:
        """Generate LLM-assisted remediation suggestions."""
        # TODO: Implement LLM suggestion generation
        return []
    
    async def _conduct_hitl_review(self, violations) -> list:
        """Conduct human-in-the-loop review."""
        # Prepare review batch
        review_items = self.hitl_agent.prepare_review_batch(
            [v.__dict__ if hasattr(v, '__dict__') else v for v in violations[:100]]
        )
        
        logger.info(f"Prepared {len(review_items)} items for HITL review")
        
        # For automation: auto-approve high-confidence items
        approved_changes = []
        for item in review_items:
            if item.confidence >= 0.85:
                self.hitl_agent.submit_review(item.item_id, True)
                approved_changes.append({
                    "record_id": item.record_id,
                    "column": item.column,
                    "original_value": item.original_value,
                    "suggested_value": item.suggested_value
                })
        
        return approved_changes
    
    def _apply_remediations(self, data: pd.DataFrame, approved_changes: list) -> pd.DataFrame:
        """Apply approved remediation changes."""
        clean_data = data.copy()
        
        for change in approved_changes:
            try:
                record_id = change.get("record_id")
                column = change.get("column")
                new_value = change.get("suggested_value")
                
                if record_id in clean_data.index:
                    clean_data.loc[record_id, column] = new_value
            except Exception as e:
                logger.warning(f"Failed to apply change: {e}")
        
        return clean_data
    
    async def _persist_results(
        self,
        clean_data: pd.DataFrame,
        pre_assessment: Dict,
        post_assessment: Dict,
        approved_changes: list
    ):
        """Persist results to storage."""
        try:
            # Generate output directory
            output_dir = self.config.get("output", {}).get("location", "output/")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Save clean data
            clean_path = os.path.join(output_dir, f"Sample_Policy_Data_clean_{self.run_id}.csv")
            clean_data.to_csv(clean_path, index=False)
            logger.info(f"Clean data saved: {clean_path}")
            
            # Generate assessment report
            report_path = os.path.join(output_dir, f"DQ_Assessment_{self.run_id}.xlsx")
            ReportGenerator.generate_excel_report(pre_assessment, report_path)
            logger.info(f"Assessment report saved: {report_path}")
            
            # Persist to NeonDB if available
            if self.storage:
                self.storage.persist_assessment(pre_assessment["assessment_id"], pre_assessment)
                self.storage.persist_assessment(post_assessment["assessment_id"], post_assessment)
                self.storage.persist_clean_data(self.run_id, clean_data)
                logger.info("Results persisted to NeonDB")
        
        except Exception as e:
            logger.error(f"Failed to persist results: {e}")
    
    def _finalize_results(self, data, pre_assessment, post_assessment, approved_changes):
        """Finalize results when no remediation is needed."""
        return {
            "status": "success",
            "run_id": self.run_id,
            "pre_assessment": pre_assessment,
            "post_assessment": post_assessment,
            "message": "Data quality acceptable - no remediation needed"
        }
    
    def _print_assessment_summary(self, assessment: Dict):
        """Print assessment summary to console."""
        print(f"\n{'='*60}")
        print("ASSESSMENT SUMMARY")
        print(f"{'='*60}")
        print(f"Total Records: {assessment['total_records']}")
        print(f"Total Violations: {assessment['total_violations']}")
        print(f"Records with Issues: {assessment['records_with_issues']} ({assessment['records_with_issues_pct']:.1f}%)")
        print(f"Pass Rate: {assessment['pass_rate']:.1f}%")
        print(f"Overall DQ Score: {assessment['overall_dq_score']:.1f}/100")
        
        print(f"\nTop Issues:")
        for issue in assessment.get("top_issues", [])[:5]:
            print(f"  - {issue['issue_type']} in {issue['column']}: {issue['count']} occurrences")
    
    def _print_improvement_summary(self, report: Dict):
        """Print improvement summary to console."""
        improvements = report.get("improvements", {})
        print(f"\n{'='*60}")
        print("IMPROVEMENT SUMMARY")
        print(f"{'='*60}")
        print(f"Violations Fixed: {improvements.get('violations_fixed', 0)}")
        print(f"Violations Reduction: {improvements.get('violations_reduction_pct', 0):.1f}%")
        print(f"Pass Rate Improvement: {improvements.get('pass_rate_improvement', 0):.1f}%")
        print(f"DQ Score Improvement: {improvements.get('dq_score_improvement', 0):.1f}")
        print(f"Records Improved: {improvements.get('records_improved', 0)}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI-Agent-Driven Data Quality Platform")
    parser.add_argument(
        "--config",
        type=str,
        default="config/hybrid.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["local", "hybrid", "cloud"],
        default="hybrid",
        help="Deployment mode"
    )
    
    args = parser.parse_args()

    # Setup logging
    setup_logging()

    # If UI is desired (default), launch Streamlit dashboard and exit
    if not getattr(args, 'mode', None) == 'local':
        # Launch Streamlit dashboard
        import subprocess, os
        print("Starting Streamlit dashboard (dashboard_final.py). Close the dashboard process to exit CLI.")
        cmd = [os.sys.executable, '-m', 'streamlit', 'run', 'dashboard_final.py']
        try:
            proc = subprocess.Popen(cmd, cwd=os.getcwd())
            proc.wait()
        except KeyboardInterrupt:
            print('Dashboard interrupted by user')
        return

    # Otherwise run the pipeline headless
    pipeline = AgenticDQPipeline(args.config)
    result = await pipeline.execute()

    # Print final result
    print("\n" + "="*60)
    print("PIPELINE EXECUTION COMPLETE")
    print("="*60)
    print(json.dumps({
        "status": result.get("status"),
        "run_id": result.get("run_id"),
        "violations_fixed": result.get("improvement_report", {}).get("improvements", {}).get("violations_fixed")
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
