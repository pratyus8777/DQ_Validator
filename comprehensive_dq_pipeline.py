"""
Comprehensive Data Quality Pipeline
Detects violations, applies fixes, generates detailed reports and dashboard
Fully dynamic with support for multiple CSV inputs and LLM-based rule interpretation
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple

from dq_real_world_engine import RealWorldRulesEngine
from logging_config import setup_logging, get_logger
from agents.profiling_orchestrator import DataProfiler, DynamicRuleManager, ProfilingOrchestrator
from agents.llm_enhanced_profiler import LLMEnhancedProfiler
from agents.standardization_rules import StandardizationRules
from data_io.data_source import DataSourceFactory
from deterministic_engine.assessment_engine import AssessmentEngine, ReportGenerator
from llm.llm_client import LLMClient

logger = get_logger(__name__)


class ComprehensiveDQPipeline:
    """
    End-to-end data quality pipeline with:
    - Dynamic data profiling
    - Session-based rule management
    - LLM-assisted rule interpretation
    - Comprehensive assessment and reporting
    - Support for multiple CSV inputs
    """
    
    def __init__(self, data_path: str = "data/Sample_Policy_Data.csv", config: Dict = None):
        """Initialize pipeline"""
        logger.info("="*80)
        logger.info("COMPREHENSIVE DATA QUALITY PIPELINE")
        logger.info("="*80)
        
        self.run_id = str(uuid.uuid4())[:8]
        self.data_path = data_path
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Load config
        if config is None:
            import yaml
            try:
                with open("config/local.yaml", "r") as f:
                    config = yaml.safe_load(f)
            except:
                config = {}
        
        self.config = config
        self.engine = RealWorldRulesEngine()
        
        # Initialize components
        self.profiler = DataProfiler()
        self.llm_profiler = LLMEnhancedProfiler(llm_client=None)  # Will set after LLM init
        self.rule_manager = DynamicRuleManager(config.get("llm", {}))
        self.llm_client = LLMClient(config.get("llm", {}))
        self.llm_profiler.llm_client = self.llm_client  # Now set it
        self.standardization_rules = StandardizationRules()
        self.assessment_engine = AssessmentEngine(config)
        
        self.df_original = None
        self.df_clean = None
        self.violations = []
        self.violation_summary = None
        self.data_profile = None
        self.llm_enhanced_analysis = None
        self.assessment_before = None
        self.assessment_after = None
        self.stats = {}
        self.session_id = str(uuid.uuid4())[:12]
        self.custom_cleansing_rules = {}
        self.apply_custom_rules_flag = False
    
    def execute(self, session_rules: Dict[str, str] = None, skip_cleaning: bool = False):
        """
        Execute full pipeline
        
        Args:
            session_rules: Dict mapping column names to rule prompts for this session
            skip_cleaning: If True, skip cleaning phase and only do profiling/assessment
        """
        try:
            logger.info("\nPhase 1: Loading data...")
            self._load_data()
            
            logger.info("\nPhase 2: Profiling data with LLM enhancement...")
            self._profile_data_enhanced()
            
            logger.info("\nPhase 3: Generating detailed analysis report...")
            self._generate_analysis_report()
            
            logger.info("\nPhase 4: Managing rules...")
            self._manage_rules(session_rules)
            
            logger.info("\nPhase 5: Generating assessment...")
            self._generate_pre_assessment()
            
            if not skip_cleaning:
                logger.info("\nPhase 6: Applying fixes...")
                self._apply_fixes()
                
                logger.info("\nPhase 7: Generating post-remediation assessment...")
                self._generate_post_assessment()
                
                logger.info("\nPhase 8: Creating cleaned output...")
                self.df_clean = self.df_original.copy()
            else:
                logger.info("\n⊘ Skipping cleaning phase (assessment-only mode)")
                self.df_clean = self.df_original.copy()
                self.assessment_after = None
            
            logger.info("\nPhase 9: Generating reports...")
            self._generate_reports()
            
            logger.info("\nPhase 10: Creating comprehensive output...")
            self._create_comprehensive_output()
            
            logger.info("\n" + "="*80)
            logger.info("PIPELINE EXECUTION COMPLETE")
            logger.info("="*80)
            self._print_summary()
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            # Clean up session
            self.rule_manager.end_session()
    
    def _load_data(self):
        """Load source data - supports multiple formats"""
        try:
            # Try multiple encodings for CSV compatibility
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                try:
                    self.df_original = pd.read_csv(self.data_path, encoding=encoding)
                    logger.info(f"✓ Loaded {len(self.df_original)} records with {len(self.df_original.columns)} columns from {self.data_path}")
                    logger.info(f"  Columns: {', '.join(self.df_original.columns[:5])}...")
                    return
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise
    
    def _profile_data(self):
        """Profile dataset for steward insights"""
        try:
            self.data_profile = self.profiler.profile_dataset(self.df_original)
            logger.info(f"✓ Profiled {len(self.data_profile['columns'])} columns")
            
            # Log key insights
            null_cols = [col for col, prof in self.data_profile['columns'].items() 
                        if prof['null_percentage'] > 0]
            if null_cols:
                logger.info(f"  Columns with nulls: {', '.join(null_cols[:5])}...")
        except Exception as e:
            logger.error(f"Failed to profile data: {e}")
            # Non-critical, continue
    
    def _profile_data_enhanced(self):
        """Profile dataset with LLM enhancement for deeper violation detection"""
        try:
            self.llm_enhanced_analysis = self.llm_profiler.analyze_comprehensive(self.df_original)
            
            total_violations = len(self.llm_enhanced_analysis["affected_records"])
            logger.info(f"✓ Enhanced Analysis: {total_violations} records with {sum(len(v) for v in self.llm_enhanced_analysis['violations'].values())} violations")
            logger.info(f"  Severity: Critical={self.llm_enhanced_analysis['severity_breakdown']['critical']}, " 
                       f"High={self.llm_enhanced_analysis['severity_breakdown']['high']}, "
                       f"Medium={self.llm_enhanced_analysis['severity_breakdown']['medium']}, "
                       f"Low={self.llm_enhanced_analysis['severity_breakdown']['low']}")
            
            # Also run basic profiling
            self._profile_data()
            
        except Exception as e:
            logger.error(f"Failed to profile data with LLM: {e}")
            # Non-critical, fall back to basic profiling
            self._profile_data()
    
    def _generate_analysis_report(self):
        """Generate detailed analysis report from LLM profiling"""
        try:
            if not self.llm_enhanced_analysis:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save detailed JSON analysis
            analysis_json_path = self.output_dir / f"Detailed_Analysis_{timestamp}.json"
            with open(analysis_json_path, 'w') as f:
                json.dump(self.llm_enhanced_analysis, f, indent=2, default=str)
            logger.info(f"✓ Saved detailed analysis: {analysis_json_path.name}")
            
            # Generate text report
            report_lines = []
            report_lines.append("COMPREHENSIVE DATA QUALITY ANALYSIS REPORT")
            report_lines.append("="*80)
            report_lines.append(f"Timestamp: {self.llm_enhanced_analysis['timestamp']}")
            report_lines.append(f"Total Records Analyzed: {self.llm_enhanced_analysis['total_records']}")
            report_lines.append(f"Total Columns: {self.llm_enhanced_analysis['total_columns']}")
            report_lines.append(f"Records with Issues: {self.llm_enhanced_analysis['violation_count']}")
            report_lines.append(f"Total Violations Found: {sum(len(v) for v in self.llm_enhanced_analysis['violations'].values())}")
            report_lines.append("")
            
            report_lines.append("VIOLATION SUMMARY BY SEVERITY")
            report_lines.append("-"*80)
            for severity in ['critical', 'high', 'medium', 'low']:
                count = self.llm_enhanced_analysis['severity_breakdown'][severity]
                report_lines.append(f"  {severity.upper()}: {count} violations")
            report_lines.append("")
            
            report_lines.append("VIOLATIONS BY DIMENSION")
            report_lines.append("-"*80)
            for dimension, violations in self.llm_enhanced_analysis['violations'].items():
                report_lines.append(f"\n{dimension.upper()}: {len(violations)} violations")
                for v in violations[:20]:  # Show first 20
                    if isinstance(v, dict):
                        report_lines.append(f"  Row {v.get('row', 'N/A')}: {v.get('issue', '')} [{v.get('severity', 'N/A')}]")
                if len(violations) > 20:
                    report_lines.append(f"  ... and {len(violations) - 20} more")
            
            report_lines.append("\n\nCOLUMN QUALITY SCORES")
            report_lines.append("-"*80)
            for col, quality in sorted(self.llm_enhanced_analysis['column_quality'].items(), 
                                      key=lambda x: x[1]['quality_score']):
                report_lines.append(f"  {col}: {quality['quality_score']:.1f}/100 ({quality['violation_count']} violations)")
            
            # Save text report
            report_text = "\n".join(report_lines)
            report_path = self.output_dir / f"Detailed_Analysis_{timestamp}.txt"
            with open(report_path, 'w') as f:
                f.write(report_text)
            logger.info(f"✓ Saved analysis report: {report_path.name}")
            logger.info("\n" + report_text)
            
        except Exception as e:
            logger.error(f"Failed to generate analysis report: {e}")
    
    def _manage_rules(self, session_rules: Dict[str, str] = None):
        """Manage rule overrides for this session"""
        self.rule_manager.start_session(self.session_id)
        logger.info(f"Session ID: {self.session_id}")
        
        if session_rules:
            logger.info(f"Applying {len(session_rules)} session rule overrides...")
            for col, rule_text in session_rules.items():
                try:
                    self.rule_manager.set_column_rule(col, rule_text, self.llm_client)
                    logger.info(f"  ✓ Applied rule override for '{col}'")
                except Exception as e:
                    logger.warning(f"  ✗ Failed to apply rule for '{col}': {e}")
    
    def _detect_violations(self):
        """Detect all DQ violations using effective rules"""
        try:
            # Load base rules
            rules_path = self.config.get("paths", {}).get("dq_rules", "data/DQ_Rule_Repository-Policy.csv")
            for encoding in ['utf-8', 'latin-1']:
                try:
                    base_rules = pd.read_csv(rules_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            # Get effective rules (with session overrides)
            effective_rules = self.rule_manager.get_effective_rules(self.df_original, base_rules)
            
            # Call detect_all_violations with only the dataframe (it uses internal rules)
            self.violations, self.violation_summary = self.engine.detect_all_violations(self.df_original)
            self.stats = self.engine.get_violation_stats(self.violations)
            
            logger.info(f"✓ Found {self.stats['total_violations']} violations in {self.stats['affected_records']} records")
            logger.info(f"  Dimensions: {dict(self.stats['by_dimension'])}")
            
        except Exception as e:
            logger.error(f"Failed to detect violations: {e}")
            raise
    
    def _generate_pre_assessment(self):
        """Generate assessment before remediation"""
        try:
            # Convert DQViolation objects to RuleExecutionResult format for assessment engine
            from deterministic_engine.dynamic_rule_executor import RuleExecutionResult
            
            converted_violations = []
            for v in self.violations:
                converted_violations.append(RuleExecutionResult(
                    record_id=v.row_idx,
                    column=v.column,
                    rule_id=f"{v.dimension}_{v.violation_type}",
                    check_type=v.violation_type,
                    passed=False,
                    issue_type=v.violation_type,
                    original_value=v.original_value,
                    suggested_fix=v.suggested_fix,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
            
            self.assessment_before = self.assessment_engine.generate_assessment(
                self.df_original,
                converted_violations,
                assessment_id=f"PRE_{self.run_id}",
                phase="before"
            )
            logger.info(f"✓ Pre-assessment generated: {self.assessment_before['overall_dq_score']:.1f}/100 DQ score")
        except Exception as e:
            logger.error(f"Failed to generate pre-assessment: {e}")
            self.assessment_before = {}
    
    def _apply_fixes(self):
        """Apply fixes to create clean dataset"""
        try:
            self.df_clean = self.engine.apply_fixes(
                self.df_original.copy(),
                self.violations
            )
            
            # Apply standardization
            self._apply_standardization()
            
            # Apply custom cleansing rules if enabled
            if self.apply_custom_rules_flag:
                self._apply_custom_cleansing_rules_with_llm()
            
            # Count changes safely
            try:
                changes = (self.df_original.astype(str).values != self.df_clean.astype(str).values).sum()
                logger.info(f"✓ Applied fixes: {changes} cell changes")
            except:
                logger.info(f"✓ Applied fixes to dataset")
            
        except Exception as e:
            logger.error(f"Failed to apply fixes: {e}")
            self.df_clean = self.df_original.copy()
    
    def _apply_standardization(self):
        """Apply data standardization rules"""
        try:
            logger.info("Applying standardization rules...")
            
            # Apply default standardization
            self.df_clean = self.standardization_rules.apply_all_standardization(self.df_clean)
            
            logger.info("✓ Applied standardization for dates, phones, emails, names, IDs")
            
        except Exception as e:
            logger.error(f"Failed to apply standardization: {e}")
    
    def _apply_custom_cleansing_rules_with_llm(self):
        """Apply custom cleansing rules with rule parsing"""
        if not self.custom_cleansing_rules:
            logger.info("No custom cleansing rules defined")
            return
        
        try:
            logger.info(f"Applying {len(self.custom_cleansing_rules)} custom cleansing rules...")
            
            from agents.standardization_rules import CustomCleansingRuleParser
            
            for column, rule_config in self.custom_cleansing_rules.items():
                # Handle both string rules and dict rule configs
                if isinstance(rule_config, str):
                    rule_text = rule_config
                elif isinstance(rule_config, dict):
                    rule_text = rule_config.get('rule_text', '')
                else:
                    continue
                
                if not rule_text or rule_text.strip() == '':
                    continue
                
                if column not in self.df_clean.columns:
                    logger.warning(f"Column '{column}' not found in data")
                    continue
                
                logger.info(f"Processing column '{column}': {rule_text[:60]}...")
                
                # Parse and apply the rule
                try:
                    parsed_rule = CustomCleansingRuleParser.parse_custom_rule(rule_text)
                    
                    # Apply parsed rule to column
                    self.df_clean[column] = self.df_clean[column].apply(
                        lambda x: CustomCleansingRuleParser.apply_custom_rule(x, parsed_rule)
                    )
                    logger.info(f"  ✓ Applied {len(parsed_rule.get('operations', []))} operations to {column}")
                except Exception as e:
                    logger.error(f"Failed to apply rule to {column}: {e}")
                
                # Apply basic transformations based on rule text
                try:
                    if 'uppercase' in rule_text.lower() or 'upper' in rule_text.lower():
                        self.df_clean[column] = self.df_clean[column].apply(
                            lambda x: str(x).upper() if pd.notna(x) else x
                        )
                        logger.info(f"  ✓ Applied uppercase transformation to {column}")
                    
                    if 'lowercase' in rule_text.lower() or 'lower' in rule_text.lower():
                        self.df_clean[column] = self.df_clean[column].apply(
                            lambda x: str(x).lower() if pd.notna(x) else x
                        )
                        logger.info(f"  ✓ Applied lowercase transformation to {column}")
                    
                    if 'trim' in rule_text.lower() or 'strip' in rule_text.lower():
                        self.df_clean[column] = self.df_clean[column].apply(
                            lambda x: str(x).strip() if pd.notna(x) else x
                        )
                        logger.info(f"  ✓ Applied trim transformation to {column}")
                    
                    if 'title' in rule_text.lower():
                        self.df_clean[column] = self.df_clean[column].apply(
                            lambda x: str(x).title() if pd.notna(x) else x
                        )
                        logger.info(f"  ✓ Applied title case transformation to {column}")
                    
                    if 'date' in rule_text.lower() or 'yyyy-mm-dd' in rule_text.lower():
                        # Extract desired date format from rule text
                        date_format = '%Y-%m-%d'  # Default
                        if 'yyyy/mm/dd' in rule_text.lower():
                            date_format = '%Y/%m/%d'
                        elif 'dd/mm/yyyy' in rule_text.lower():
                            date_format = '%d/%m/%Y'
                        elif 'mm/dd/yyyy' in rule_text.lower():
                            date_format = '%m/%d/%Y'
                        elif 'yyyy-mm-dd' in rule_text.lower():
                            date_format = '%Y-%m-%d'
                        elif 'dd-mm-yyyy' in rule_text.lower():
                            date_format = '%d-%m-%Y'
                        
                        self.df_clean[column] = self.df_clean[column].apply(
                            lambda x: self.standardization_rules._parse_and_format_date(x, date_format)
                        )
                        logger.info(f"  ✓ Applied date standardization ({date_format}) to {column}")
                    
                    if 'phone' in rule_text.lower() or 'e.164' in rule_text.lower():
                        self.df_clean[column] = self.df_clean[column].apply(
                            lambda x: self.standardization_rules._format_phone(x)
                        )
                        logger.info(f"  ✓ Applied phone standardization to {column}")
                    
                except Exception as e:
                    logger.error(f"Failed to apply rule to column {column}: {e}")
            
            logger.info("✓ Custom cleansing rules applied")
            
        except Exception as e:
            logger.error(f"Failed to apply custom cleansing rules: {e}")
    
    def _generate_post_assessment(self):
        """Generate assessment after remediation"""
        try:
            # Re-detect violations on cleaned data
            violations_after, _ = self.engine.detect_all_violations(self.df_clean)
            
            # Convert DQViolation objects to RuleExecutionResult format
            from deterministic_engine.dynamic_rule_executor import RuleExecutionResult
            
            converted_violations_after = []
            for v in violations_after:
                converted_violations_after.append(RuleExecutionResult(
                    record_id=v.row_idx,
                    column=v.column,
                    rule_id=f"{v.dimension}_{v.violation_type}",
                    check_type=v.violation_type,
                    passed=False,
                    issue_type=v.violation_type,
                    original_value=v.original_value,
                    suggested_fix=v.suggested_fix,
                    confidence=1.0,
                    execution_method="deterministic"
                ))
            
            self.assessment_after = self.assessment_engine.generate_assessment(
                self.df_clean,
                converted_violations_after,
                assessment_id=f"POST_{self.run_id}",
                phase="after"
            )
            logger.info(f"✓ Post-assessment generated: {self.assessment_after['overall_dq_score']:.1f}/100 DQ score")
            
            # Generate improvement report
            improvement = self.assessment_engine.generate_improvement_report(
                self.assessment_before,
                self.assessment_after
            )
            logger.info(f"✓ Improvement: {improvement['improvements']['violations_reduction_pct']:.1f}% violations reduced")
            
        except Exception as e:
            logger.error(f"Failed to generate post-assessment: {e}")
            self.assessment_after = {}
    
    def _generate_reports(self):
        """Generate comprehensive assessment reports"""
        try:
            # Generate profiling report
            if self.data_profile:
                self._generate_profiling_report()
            
            if self.assessment_before:
                # Excel report
                excel_path = self.output_dir / f"DQ_Assessment_{self.run_id}.xlsx"
                ReportGenerator.generate_excel_report(self.assessment_before, str(excel_path))
                
                # Text summary
                summary_text = ReportGenerator.generate_summary_text(self.assessment_before)
                logger.info("\n" + summary_text)
                
                # Save to file
                summary_path = self.output_dir / f"DQ_Assessment_Summary_{self.run_id}.txt"
                with open(summary_path, 'w') as f:
                    f.write(summary_text)
                
                logger.info(f"✓ Reports generated in output/")
                
        except Exception as e:
            logger.error(f"Failed to generate reports: {e}")
    
    def _create_comprehensive_output(self):
        """Create all output files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save original data
            orig_path = self.output_dir / f"Sample_Policy_Data_ORIGINAL_{timestamp}.csv"
            self.df_original.to_csv(orig_path, index=False)
            logger.info(f"✓ Saved original data: {orig_path.name}")
            
            # Save cleaned data
            clean_path = self.output_dir / f"Sample_Policy_Data_CLEANED_{timestamp}.csv"
            self.df_clean.to_csv(clean_path, index=False)
            logger.info(f"✓ Saved cleaned data: {clean_path.name}")
            
            # Save violations
            if self.violation_summary is not None and not self.violation_summary.empty:
                viol_path = self.output_dir / f"Violations_Report_{timestamp}.csv"
                self.violation_summary.to_csv(viol_path, index=False)
                logger.info(f"✓ Saved violations report: {viol_path.name}")
            
            # Save summary
            summary = {
                "run_id": self.run_id,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "total_violations": self.stats.get('total_violations', 0),
                "violations_fixed": max(0, self.stats.get('total_violations', 0) - len(self.violations)),
                "violations_by_column": dict(self.stats.get('by_column', {})),
                "violations_by_dimension": dict(self.stats.get('by_dimension', {})),
                "before_assessment": self.assessment_before,
                "after_assessment": self.assessment_after,
                "data_profile_summary": {
                    "total_records": self.data_profile['shape']['rows'],
                    "total_columns": self.data_profile['shape']['columns'],
                    "null_columns": [col for col, prof in self.data_profile['columns'].items() 
                                    if prof['null_percentage'] > 0]
                } if self.data_profile else {}
            }
            
            summary_path = self.output_dir / f"Cleaning_Summary_{timestamp}.json"
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"✓ Saved summary: {summary_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to create output: {e}")
    
    def _generate_profiling_report(self):
        """Generate and save data profiling report"""
        try:
            if not self.data_profile:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            profile_report = []
            profile_report.append("DATA PROFILING REPORT")
            profile_report.append("="*80)
            profile_report.append(f"Timestamp: {datetime.now().isoformat()}")
            profile_report.append(f"Records: {self.data_profile['shape']['rows']}")
            profile_report.append(f"Columns: {self.data_profile['shape']['columns']}")
            profile_report.append("")
            
            profile_report.append("COLUMN ANALYSIS")
            profile_report.append("-"*80)
            
            for col_name, col_profile in self.data_profile['columns'].items():
                profile_report.append(f"\nColumn: {col_name}")
                profile_report.append(f"  Data Type: {col_profile['dtype']}")
                profile_report.append(f"  Non-Null Count: {col_profile['non_null_count']} ({100-col_profile['null_percentage']:.1f}%)")
                profile_report.append(f"  Null Count: {col_profile['null_count']} ({col_profile['null_percentage']:.1f}%)")
                profile_report.append(f"  Unique Values: {col_profile['unique_count']}")
                
                if col_profile['dtype'] in ['int64', 'float64']:
                    profile_report.append(f"  Mean: {col_profile.get('mean', 'N/A')}")
                    profile_report.append(f"  Median: {col_profile.get('median', 'N/A')}")
                    profile_report.append(f"  Min: {col_profile.get('min', 'N/A')}")
                    profile_report.append(f"  Max: {col_profile.get('max', 'N/A')}")
                    profile_report.append(f"  Std Dev: {col_profile.get('std', 'N/A')}")
            
            # Save text report
            profile_text = "\n".join(profile_report)
            profile_path = self.output_dir / f"Data_Profile_{timestamp}.txt"
            with open(profile_path, 'w') as f:
                f.write(profile_text)
            logger.info(f"✓ Saved profiling report: {profile_path.name}")
            
            # Save JSON report
            profile_json_path = self.output_dir / f"Data_Profile_{timestamp}.json"
            with open(profile_json_path, 'w') as f:
                json.dump(self.data_profile, f, indent=2, default=str)
            logger.info(f"✓ Saved profiling JSON: {profile_json_path.name}")
            
            # Print profiling summary to console
            logger.info("\n" + profile_text)
            
        except Exception as e:
            logger.error(f"Failed to generate profiling report: {e}")
    
    def _print_summary(self):
        """Print execution summary"""
        logger.info("\n" + "="*80)
        logger.info("EXECUTION SUMMARY")
        logger.info("="*80)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Total Records: {len(self.df_original)}")
        logger.info(f"Total Columns: {len(self.df_original.columns)}")
        logger.info(f"Violations Found: {self.stats.get('total_violations', 0)}")
        logger.info(f"Violations Fixed: {max(0, self.stats.get('total_violations', 0) - len(self.violations))}")
        if self.assessment_before:
            logger.info(f"DQ Score Before: {self.assessment_before.get('overall_dq_score', 0):.1f}/100")
        if self.assessment_after:
            logger.info(f"DQ Score After: {self.assessment_after.get('overall_dq_score', 0):.1f}/100")
        logger.info("="*80)


def main():
    """Main entry point"""
    import sys
    
    # Check for flags
    skip_cleaning = "--skip-cleaning" in sys.argv or "--assessment-only" in sys.argv
    apply_custom_rules = "--apply-custom-rules" in sys.argv
    
    # Remove flags from sys.argv before processing
    argv_clean = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    
    # Check for custom CSV input
    csv_path = argv_clean[0] if argv_clean else "data/Sample_Policy_Data.csv"
    
    # Check for session rules (JSON format)
    session_rules = None
    if len(argv_clean) > 1:
        try:
            session_rules = json.loads(argv_clean[1])
        except:
            pass
    
    pipeline = ComprehensiveDQPipeline(data_path=csv_path)
    
    # Load custom cleansing rules if applying them
    if apply_custom_rules:
        # Try loading custom rules from Neon DB
        try:
            from data_io.db_helpers import read_guidewire_cleansing_rules
            rules_df = read_guidewire_cleansing_rules()
            if rules_df is not None and not rules_df.empty:
                # build dict of column -> rule_definition
                name_col = next((c for c in rules_df.columns if 'column' in c.lower() or 'cde' in c.lower()), None)
                rule_col = next((c for c in rules_df.columns if 'rule' in c.lower() or 'remediation' in c.lower() or 'definition' in c.lower()), None)
                custom = {}
                if name_col and rule_col:
                    for _, r in rules_df.iterrows():
                        k = r.get(name_col)
                        v = r.get(rule_col)
                        if k and v and str(v).strip():
                            custom[str(k)] = str(v)
                pipeline.custom_cleansing_rules = custom
                logger.info(f"✓ Loaded {len(pipeline.custom_cleansing_rules)} custom cleansing rules from DB")
        except Exception:
            rules_file = Path("output/cleansing_rules.json")
            if rules_file.exists():
                with open(rules_file, 'r') as f:
                    pipeline.custom_cleansing_rules = json.load(f)
                    logger.info(f"✓ Loaded {len(pipeline.custom_cleansing_rules)} custom cleansing rules (from file)")
        pipeline.apply_custom_rules_flag = True
        skip_cleaning = False  # Force cleaning when using custom rules
    
    pipeline.execute(session_rules=session_rules, skip_cleaning=skip_cleaning)


if __name__ == "__main__":
    main()
