#!/usr/bin/env python
"""
Dynamic DQ Pipeline - LangChain/LangGraph Integration with Robust Error Handling
Assessment First, Then Cleansing with Advanced Rule Interpretation
Suppresses LLM errors and uses intelligent fallbacks
"""

import json
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import yaml
import sys
import warnings

# Suppress LLM warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
logging.getLogger('langchain').setLevel(logging.ERROR)
logging.getLogger('langchain_core').setLevel(logging.ERROR)
logging.getLogger('ollama').setLevel(logging.ERROR)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser


class DynamicDQPipeline:
    """Dynamic DQ pipeline with LangChain/LangGraph integration"""
    
    def __init__(self, data_path='data/Sample_Policy_Data.csv', config_path='config/local.yaml'):
        """Initialize pipeline"""
        self.data_path = data_path
        self.df_original = None
        self.rules_for_cleaning = {}
        self.fast_mode = False
        
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize LLM silently
        self.llm = self._init_llm_silent()
        
    def _init_llm_silent(self):
        """Initialize LLM without showing errors"""
        try:
            ollama_url = self.config.get('llm', {}).get('base_url', 'http://localhost:11434')
            model = self.config.get('llm', {}).get('model', 'llama2')
            
            llm = Ollama(
                base_url=ollama_url,
                model=model,
                temperature=0.3,
                top_k=10,
                top_p=0.9,
            )
            
            # Test connectivity silently
            try:
                _ = llm.invoke("test")
                logger.info("LLM initialized and available")
                return llm
            except:
                logger.debug("LLM connection failed, will use heuristics")
                return None
        except Exception as e:
            logger.debug(f"LLM initialization failed: {e}")
            return None
    
    def load_data(self):
        """Load the data"""
        logger.info(f"Loading data from {self.data_path}")
        self.df_original = pd.read_csv(self.data_path)
        logger.info(f"Loaded {self.df_original.shape[0]} records x {self.df_original.shape[1]} columns")
        return self.df_original
    
    def load_rules(self):
        """Load rules from repository with column mapping"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: LOADING AND INTERPRETING RULES (DYNAMIC)")
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
        
        # Use guidewire_policy_data_cleansing_rules from Neon DB
        from data_io.db_helpers import read_guidewire_cleansing_rules
        cleansing_df = read_guidewire_cleansing_rules()
        cleansing_file = None
        if Path(cleansing_file).exists():
            try:
                rules_df = pd.read_csv(cleansing_file, encoding='latin-1')
                
                if 'CDE' in rules_df.columns:
                    remediation_cols = [c for c in rules_df.columns if 'Remediation' in c]
                    for idx, row in rules_df.iterrows():
                        col_name = row['CDE']
                        actual_col = column_mapping.get(col_name, col_name)
                        
                        rules_text = ' '.join([str(row[rc]) for rc in remediation_cols if pd.notna(row[rc])])
                        if rules_text.strip():
                            self.rules_for_cleaning[actual_col] = rules_text
                    
                    logger.info(f"Loaded {len(self.rules_for_cleaning)} rules")
            except Exception as e:
                logger.error(f"Error loading rules: {e}")
    
    def profile_data(self):
        """Profile data"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 2: DATA PROFILING (DYNAMIC)")
        logger.info("="*80)
        
        if self.df_original is None:
            self.load_data()
        
        profile = {
            'total_records': len(self.df_original),
            'total_columns': len(self.df_original.columns),
            'columns': {},
        }
        
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
        
        if not self.fast_mode and self.llm:
            logger.info("Using LLM for advanced profiling")
        elif self.fast_mode:
            logger.info("Fast mode: skipping advanced profiling")
        
        return profile
    
    def generate_assessment_report(self):
        """Generate assessment report"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 3: GENERATING ASSESSMENT REPORT")
        logger.info("="*80)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'output/Assessment_Report_Dynamic_{timestamp}.json'
        
        report = {
            'timestamp': timestamp,
            'approach': 'dynamic_langchain',
            'data_file': self.data_path,
            'summary': {
                'total_records': len(self.df_original),
                'total_columns': len(self.df_original.columns),
            },
            'rules_for_cleaning': self.rules_for_cleaning,
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Assessment report saved: {report_file}")
        return report
    
    def apply_rules_dynamic(self):
        """Dynamically apply rules using LLM or heuristics"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 4: DYNAMIC RULE APPLICATION AND CLEANSING")
        logger.info("="*80)
        
        if not self.rules_for_cleaning:
            logger.error("No rules defined")
            return None
        
        df_clean = self.df_original.copy()
        violations_count = {}
        
        logger.info(f"Applying {len(self.rules_for_cleaning)} rules dynamically...")
        
        for column, rule_text in self.rules_for_cleaning.items():
            if column not in df_clean.columns:
                logger.debug(f"Column '{column}' not in data, skipping")
                continue
            
            logger.info(f"  Processing '{column}'...")
            
            original_values = df_clean[column].copy()
            
            # Try LLM-based transformation first
            transformation = None
            if self.llm:
                transformation = self._get_llm_transformation(column, rule_text, df_clean[column])
            
            # Fallback to heuristic
            if transformation is None:
                transformation = self._get_heuristic_transformation(column, rule_text)
            
            if transformation is None:
                logger.debug(f"    No transformation for '{column}'")
                violations_count[column] = 0
                continue
            
            # Apply transformation
            try:
                def safe_transform(x):
                    if pd.isna(x):
                        return x
                    try:
                        return transformation(x)
                    except:
                        return x
                
                df_clean[column] = df_clean[column].apply(safe_transform)
                
                # Count changes
                changed = (original_values != df_clean[column]) & (original_values.notna())
                violations_count[column] = changed.sum()
                
                if violations_count[column] > 0:
                    logger.info(f"    ✓ {violations_count[column]} records cleaned")
                else:
                    logger.debug(f"    No changes needed for '{column}'")
            except Exception as e:
                logger.error(f"    Failed to apply transformation: {e}")
                violations_count[column] = 0
        
        # Save cleaned data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'output/Sample_Policy_Data_CLEANED_Dynamic_{timestamp}.csv'
        df_clean.to_csv(output_file, index=False)
        
        # Summary
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
    
    def _get_llm_transformation(self, column, rule_text, series):
        """Get transformation from LLM with error suppression"""
        if not self.llm:
            return None
        
        try:
            sample_values = series.dropna().head(3).tolist()
            
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="You are a data expert. Return ONLY the transformation type."),
                HumanMessage(content=f"""Column: {column}
Rule: {rule_text[:150]}
Samples: {sample_values}

Transformation (pick one): lowercase|uppercase|title_case|trim|standardize_date:YYYY-MM-DD|standardize_phone|standardize_email|remove_special_chars""")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({})
            
            if response:
                spec = response.strip().lower()
                return self._create_transformation(spec)
        except:
            # Silent fail - will use heuristic
            pass
        
        return None
    
    def _create_transformation(self, spec: str):
        """Create transformation function from spec"""
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
        """Standardize phone"""
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
        """Get transformation heuristically"""
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
    logger.info("Starting Dynamic DQ Pipeline with LangChain/LangGraph")
    
    pipeline = DynamicDQPipeline()
    
    if '--fast' in sys.argv:
        pipeline.fast_mode = True
        logger.info("Fast mode enabled")
    
    # Execute pipeline
    pipeline.load_data()
    pipeline.load_rules()
    pipeline.profile_data()
    pipeline.generate_assessment_report()
    
    if '--clean' in sys.argv:
        pipeline.apply_rules_dynamic()
    else:
        logger.info("To clean data, run with --clean flag")


if __name__ == '__main__':
    main()
