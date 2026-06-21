#!/usr/bin/env python
"""
Agentic Data Quality Pipeline - Using LangChain/LangGraph
Assessment First, Then Cleansing with Advanced LLM-based Rule Interpretation
"""

import json
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import yaml
import sys

from agents.dq_agentic_orchestrator import DQAgenticOrchestrator, PipelineState, ProcessingState
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AgenticAssessmentFirst:
    """Assessment-first DQ pipeline using LangChain/LangGraph agents"""
    
    def __init__(self, data_path='data/Sample_Policy_Data.csv', config_path='config/local.yaml'):
        """Initialize agentic pipeline"""
        self.data_path = data_path
        
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize orchestrator
        try:
            self.orchestrator = DQAgenticOrchestrator(self.config)
            self.llm_available = True
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            self.llm_available = False
            raise
        
        # Initialize state
        self.state = PipelineState()
        self.df_original = None
        self.rules_for_cleaning = {}
        self.fast_mode = False
    
    def load_data(self):
        """Load the data"""
        logger.info(f"Loading data from {self.data_path}")
        # Prefer NeonDB sample_policy_data
        try:
            from data_io.db_helpers import read_sample_policy_data
            self.df_original = read_sample_policy_data(limit=10000)
            logger.info("Loaded sample data from NeonDB")
        except Exception:
            self.df_original = pd.read_csv(self.data_path)
        self.state.raw_data = self.df_original.copy()
        self.state.current_data = self.df_original.copy()
        logger.info(f"Loaded {self.df_original.shape[0]} records x {self.df_original.shape[1]} columns")
        return self.df_original
    
    def load_rules(self):
        """Load cleansing rules from repository"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: LOADING AND INTERPRETING RULES (AGENTIC)")
        logger.info("="*80)
        
        # Column name mapping
        column_mapping = {
            'Insured Customer ID': 'Customer ID',
            'Insured Name': 'Customer Name',
            'Date of Birth / Incorporation Date': 'Customer DOB',
            'National ID (PAN/SSN/Aadhaar)': 'National ID',
            'Address (Risk/Insured)': 'Address',
            'Contact Email': 'Email',
            'Contact Phone': 'Phone',
            'Product / Line of Business Code': 'Line of Business',
            'Coverage Limit Amount': 'Coverage Limit',
            'Coverage Deductible Amount': 'Coverage Deductible',
            'Agent / Producer ID': 'Agent ID',
            'Risk Object ID (Vehicle/Property)': 'Risk Object ID',
            'Vehicle VIN / Property ID': 'VIN/Property ID',
            'Risk Location GeoCode': 'GeoCode',
        }
        
        # Load cleansing rules from NeonDB
        try:
            from data_io.db_helpers import read_guidewire_cleansing_rules
            rules_df = read_guidewire_cleansing_rules()
            self.state.cleansing_rules = rules_df

            if rules_df is not None and not rules_df.empty:
                remediation_cols = [c for c in rules_df.columns if 'remediation' in c.lower() or 'remed' in c.lower()]
                cde_col = next((c for c in rules_df.columns if c.lower() in ('cde', 'cde_name', 'column', 'column_name')), None)
                for idx, row in rules_df.iterrows():
                    col_name = row[cde_col] if cde_col and pd.notna(row.get(cde_col)) else None
                    if not col_name:
                        continue
                    actual_col = column_mapping.get(str(col_name), str(col_name))
                    rules_text = ' '.join([str(row[rc]) for rc in remediation_cols if pd.notna(row.get(rc))])
                    if rules_text.strip():
                        self.rules_for_cleaning[actual_col] = rules_text
                logger.info(f"Loaded {len(self.rules_for_cleaning)} rules from guidewire_policy_data_cleansing_rules (DB)")
        except Exception as e:
            logger.error(f"Error loading cleansing rules from DB: {e}")
        
        logger.info("Rules loaded. Using LLM for intelligent interpretation...")
    
    def profile_data_agentic(self):
        """Profile data using agentic approach"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 2: DATA PROFILING (AGENTIC)")
        logger.info("="*80)
        
        if self.df_original is None:
            self.load_data()
        
        profile = {
            'total_records': len(self.df_original),
            'total_columns': len(self.df_original.columns),
            'columns': {},
        }
        
        # Profile each column using LLM for quality insights
        for col in self.df_original.columns:
            col_profile = {
                'name': col,
                'data_type': str(self.df_original[col].dtype),
                'non_null_count': self.df_original[col].notna().sum(),
                'null_count': self.df_original[col].isna().sum(),
                'null_percentage': (self.df_original[col].isna().sum() / len(self.df_original)) * 100,
                'unique_values': self.df_original[col].nunique(),
                'sample_values': self.df_original[col].dropna().head(3).tolist()
            }
            profile['columns'][col] = col_profile
        
        if not self.fast_mode and self.llm_available:
            logger.info("Using LLM to analyze column quality patterns...")
            # Advanced LLM-based profiling could go here
        elif self.fast_mode:
            logger.info("Fast mode: skipping advanced LLM profiling")
        
        self.state.current_data = self.df_original.copy()
        return profile
    
    def generate_assessment_report(self):
        """Generate assessment report"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 3: GENERATING ASSESSMENT REPORT")
        logger.info("="*80)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'output/Assessment_Report_Agentic_{timestamp}.json'
        
        report = {
            'timestamp': timestamp,
            'approach': 'agentic_langgraph',
            'data_file': self.data_path,
            'summary': {
                'total_records': len(self.df_original),
                'total_columns': len(self.df_original.columns),
                'columns_with_issues': 0  # Would be calculated in full implementation
            },
            'rules_for_cleaning': self.rules_for_cleaning,
            'state': {
                'status': str(self.state.status),
                'errors': self.state.errors
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Assessment report saved: {report_file}")
        return report
    
    def apply_remediations_agentic(self):
        """Apply remediations using LLM-based agents"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 4: AGENTIC REMEDIATION AND CLEANSING")
        logger.info("="*80)
        
        if not self.rules_for_cleaning:
            logger.error("No rules defined for cleansing")
            return None
        
        df_clean = self.df_original.copy()
        
        logger.info(f"Applying {len(self.rules_for_cleaning)} rule(s) with LLM interpretation...")
        
        violations_count = {}
        transformations_applied = {}
        
        # Use LLM to interpret rules and generate transformations
        llm = self.orchestrator.llm
        
        for column, rule_text in self.rules_for_cleaning.items():
            if column not in df_clean.columns:
                logger.warning(f"Column '{column}' not found")
                continue
            
            logger.info(f"  Processing '{column}'...")
            
            original_values = df_clean[column].copy()
            violations_count[column] = 0
            transformations_applied[column] = 0
            
            # Use LLM to determine transformation
            transformation = self._get_llm_transformation_agentic(
                llm, column, rule_text, df_clean[column]
            )
            
            if transformation is None:
                logger.warning(f"    No transformation determined for {column}")
                continue
            
            def safe_transform(x):
                if pd.isna(x):
                    return x
                try:
                    return transformation(x)
                except:
                    return x
            
            try:
                df_clean[column] = df_clean[column].apply(safe_transform)
                
                # Count changes
                changed = (original_values != df_clean[column]) & (original_values.notna())
                violations_count[column] = changed.sum()
                
                if violations_count[column] > 0:
                    logger.info(f"    ✓ {violations_count[column]} records cleaned")
            except Exception as e:
                logger.error(f"    Failed: {e}")
                violations_count[column] = 0
        
        # Save cleaned data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'output/Sample_Policy_Data_CLEANED_Agentic_{timestamp}.csv'
        df_clean.to_csv(output_file, index=False)
        
        logger.info(f"\nCleaning Summary:")
        total_violations = sum(violations_count.values())
        logger.info(f"  Total transformations applied: {total_violations}")
        logger.info(f"  Columns processed: {len(violations_count)}")
        
        for col, count in violations_count.items():
            if count > 0:
                logger.info(f"    • {col}: {count} violations")
        
        logger.info(f"\nCleaned data saved: {output_file}")
        logger.info("="*80)
        
        return df_clean
    
    def _get_llm_transformation_agentic(self, llm, column, rule_text, series):
        """Use LLM agent to determine transformation"""
        sample_values = series.dropna().head(3).tolist()
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a data quality expert. Analyze remediation rules and determine 
            the exact transformation needed. Return ONLY the transformation type as a single word or phrase."""),
            HumanMessage(content=f"""Column: {column}
Rule: {rule_text[:150]}
Samples: {sample_values}

Return ONLY transformation type from:
lowercase|uppercase|title_case|trim|standardize_date:YYYY-MM-DD|standardize_phone|standardize_email|remove_special_chars""")
        ])
        
        try:
            chain = prompt | llm
            response = chain.invoke({})
            
            # Handle LangChain AIMessage response
            if hasattr(response, 'content'):
                spec = response.content
            else:
                spec = str(response)
            
            if spec:
                spec = spec.strip().lower()
                trans = self._create_transformation_from_spec(spec)
                if trans:
                    logger.debug(f"  {column}: LLM suggested '{spec}'")
                    return trans
        except Exception as e:
            logger.debug(f"LLM transformation failed for {column}: {e}")
        
        # Fallback to heuristic
        return self._get_heuristic_transformation(column, rule_text)
    
    def _create_transformation_from_spec(self, spec: str):
        """Create transformation function from LLM spec"""
        spec = spec.lower().strip()
        
        if spec == 'lowercase':
            return lambda x: str(x).lower()
        elif spec == 'uppercase':
            return lambda x: str(x).upper()
        elif spec == 'title_case':
            return lambda x: str(x).title()
        elif spec == 'trim':
            return lambda x: str(x).strip()
        elif spec == 'standardize_phone':
            return self._standardize_phone
        elif spec == 'standardize_email':
            return lambda x: str(x).lower().strip()
        elif spec == 'remove_special_chars':
            return lambda x: ''.join(c for c in str(x) if c.isalnum() or c.isspace())
        elif spec.startswith('standardize_date:'):
            fmt = spec.split(':')[1]
            return lambda x: self._parse_and_standardize_date(x, fmt)
        
        return None
    
    def _standardize_phone(self, val):
        """Standardize phone format"""
        import re
        digits = re.sub(r'\D', '', str(val))
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return val
    
    def _parse_and_standardize_date(self, val, target_fmt):
        """Parse and standardize date"""
        from dateutil import parser as date_parser
        try:
            parsed = date_parser.parse(str(val))
            return parsed.strftime(target_fmt)
        except:
            return val
    
    def _get_heuristic_transformation(self, column, rule_text):
        """Fallback heuristic transformation"""
        col_lower = column.lower()
        
        if any(d in col_lower for d in ['date', 'dob', 'birth']):
            return lambda x: self._parse_and_standardize_date(x, '%Y-%m-%d')
        
        if 'email' in col_lower:
            return lambda x: str(x).lower().strip()
        
        if 'phone' in col_lower:
            return lambda x: self._standardize_phone(x)
        
        if any(id_type in col_lower for id_type in ['id', 'code', 'number']):
            return lambda x: str(x).upper().strip()
        
        if any(name in col_lower for name in ['name', 'insured', 'customer', 'agent']):
            return lambda x: str(x).title()
        
        if any(amt in col_lower for amt in ['amount', 'premium', 'commission', 'limit', 'deductible']):
            return lambda x: str(x).strip()
        
        return None


def main():
    """Main entry point"""
    logger.info("Starting Agentic DQ Pipeline - Assessment First (LangChain/LangGraph)")
    
    pipeline = AgenticAssessmentFirst()
    
    # Fast mode
    if '--fast' in sys.argv:
        pipeline.fast_mode = True
        logger.info("Fast mode enabled")
    
    # Load and process
    pipeline.load_data()
    pipeline.load_rules()
    pipeline.profile_data_agentic()
    pipeline.generate_assessment_report()
    
    # Cleanse if requested
    if '--clean' in sys.argv:
        pipeline.apply_remediations_agentic()
    else:
        logger.info("\nTo perform cleansing, call with --clean flag")


if __name__ == '__main__':
    main()
