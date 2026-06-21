#!/usr/bin/env python
"""
Main DQ Pipeline - Assessment First, Then Cleansing (ENHANCED with LangChain)
Workflow: Profiling -> Assessment Report -> (Wait for Clean signal) -> Cleansing
Uses LangChain/LangGraph for intelligent rule interpretation with fallback
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
from llm.llm_client import LLMClient
import yaml
import concurrent.futures
import warnings
import os
from data_io.db_helpers import read_sample_policy_data, read_guidewire_cleansing_rules
from data_io.config_loader import get_config

# Suppress LLM deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
logging.getLogger('langchain').setLevel(logging.ERROR)
logging.getLogger('langchain_core').setLevel(logging.ERROR)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DQAssessmentFirst:
    """Data Quality pipeline - Assessment first, cleansing only on demand (ENHANCED)"""
    
    def __init__(self, data_path='data/Sample_Policy_Data.csv', rules_config=None):
        self.data_path = data_path
        self.rules_config = rules_config or {}
        self.df_original = None
        self.assessment_report = None
        self.rules_for_cleaning = {}
        self.fast_mode = False
        
        # Initialize LLM
        with open('config/local.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        llm_config = config.get('llm', {})
        self.llm_client = LLMClient(llm_config)
        
    def load_data(self):
        """Load the data from DB or fallback CSV"""
        logger.info("Loading data from Neon DB or fallback CSV...")
        try:
            self.df_original = read_sample_policy_data(limit=1000)
            if len(self.df_original) > 0:
                logger.info(f"Loaded {self.df_original.shape[0]} records x {self.df_original.shape[1]} columns from database")
                return self.df_original
            else:
                logger.warning("Database returned empty, trying fallback CSV...")
                fallback_path = Path('data/Sample_Policy_Data.csv')
                if fallback_path.exists():
                    self.df_original = pd.read_csv(fallback_path)
                    logger.info(f"Loaded {self.df_original.shape[0]} records from fallback CSV")
                    return self.df_original
                else:
                    raise FileNotFoundError(f"No data available: Database empty and {fallback_path} not found")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            # Try fallback as last resort
            fallback_path = Path('data/Sample_Policy_Data.csv')
            if fallback_path.exists():
                self.df_original = pd.read_csv(fallback_path)
                logger.info(f"Loaded {self.df_original.shape[0]} records from fallback CSV after error")
                return self.df_original
            raise
    
    def load_and_interpret_rules(self, rules_source):
        """
        Load rules from various sources and have LLM interpret them
        rules_source can be:
        - Path to CSV file with rules
        - Dict with custom rules {column: rule_text}
        - None (load from rule repository files)
        
        STRATEGY: Load system rules first, then merge user rules on top
        (User rules for specific columns override system rules for those columns only)
        """
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: LOADING AND INTERPRETING RULES")
        logger.info("="*80)
        logger.info(f"DEBUG: rules_source={rules_source}, type={type(rules_source)}")
        
        # STEP 1: Always load system rules as base
        logger.info("Step 1: Loading BASE system rules from repository...")
        self.rules_for_cleaning = self._load_rules_from_repository()
        logger.info(f"  → Loaded {len(self.rules_for_cleaning)} base system rules")
        
        # STEP 2: Load user rules and merge with system rules
        user_rules = {}
        
        if rules_source is None:
            logger.info("Step 2: No custom rules provided. Using system rules only.")
        
        elif isinstance(rules_source, str) and Path(rules_source).exists():
            logger.info(f"Step 2: Loading user rules from: {rules_source}")
            
            # Check if it's a JSON file
            if rules_source.endswith('.json'):
                logger.info(f"  → Reading JSON format...")
                try:
                    import json
                    with open(rules_source, 'r', encoding='utf-8') as f:
                        user_rules = json.load(f)
                    logger.info(f"  → Loaded {len(user_rules)} user rules from JSON")
                    # DEBUG: Show first few rules
                    for i, (col, rule) in enumerate(list(user_rules.items())[:3]):
                        logger.info(f"    DEBUG: JSON Rule {i+1}: {col} = {rule[:80] if rule else '(empty)'}")
                except Exception as e:
                    logger.error(f"  → Error reading JSON: {e}")
                    logger.info("  → Using system rules only")
            
            # Otherwise treat as CSV
            else:
                logger.info(f"  → Reading CSV format...")
                try:
                    rules_df = pd.read_csv(rules_source, encoding='latin-1')
                    logger.info(f"  → CSV loaded: {len(rules_df)} rows")
                    
                    # Try different column name combinations
                    if 'Column' in rules_df.columns and 'Rule' in rules_df.columns:
                        user_rules = dict(zip(rules_df['Column'], rules_df['Rule']))
                        logger.info(f"  → Loaded {len(user_rules)} user rules from CSV (Column/Rule headers)")
                    elif len(rules_df.columns) >= 2:
                        col_name = rules_df.columns[0]
                        rule_name = rules_df.columns[1]
                        user_rules = dict(zip(rules_df[col_name], rules_df[rule_name]))
                        logger.info(f"  → Using columns: '{col_name}' and '{rule_name}'")
                    else:
                        logger.error("  → CSV must have at least 2 columns (Column, Rule)")
                except Exception as e:
                    logger.error(f"  → Error reading CSV: {e}")
        
        elif isinstance(rules_source, dict):
            logger.info("Step 2: Using custom rules from user input")
            user_rules = {k: v for k, v in rules_source.items() if v and v.strip()}
        
        # STEP 3: Merge user rules with system rules (user rules override for specific columns)
        if user_rules:
            logger.info("Step 3: Merging user rules with system rules...")
            merged_count = 0
            new_count = 0
            for col, rule in user_rules.items():
                if rule and rule.strip():  # Only merge non-empty rules
                    if col in self.rules_for_cleaning:
                        logger.info(f"  → OVERRIDE: {col}: '{self.rules_for_cleaning[col][:60]}...' → '{rule[:60]}...'")
                        merged_count += 1
                    else:
                        logger.info(f"  → NEW: {col}: '{rule[:60]}...'")
                        new_count += 1
                    self.rules_for_cleaning[col] = rule
            logger.info(f"  → Merged {merged_count} user rules (overrides), added {new_count} new rules")
        else:
            logger.info("Step 3: No user rules to merge. Using system rules only.")
        
        logger.info(f"\nFinal rule count: {len(self.rules_for_cleaning)} rule(s) (system + user combined)")
        
        # Use LLM to thoroughly interpret and validate each rule
        # In fast mode we skip LLM to avoid timeouts when Ollama is slow
        if not self.fast_mode and self.llm_client.available:
            try:
                self._interpret_rules_with_llm()
            except Exception as e:
                logger.warning(f"LLM rule interpretation failed: {e}")
        elif self.fast_mode:
            logger.info("Fast mode: skipping LLM rule interpretation for speed")
        else:
            logger.warning("LLM not available, rules will be used as-is")
        
        return self.rules_for_cleaning
    
    def _interpret_rules_with_llm(self, use_concurrent: bool = False, timeout: int | None = None):
        """Use LLM to thoroughly read and interpret each rule"""
        logger.info("\nUsing LLM to interpret rules thoroughly...")

        interpreted_rules: dict = {}

        def interpret(column_rule_tuple):
            column, rule_text = column_rule_tuple
            if not rule_text or not rule_text.strip():
                return column, {
                    'user_rule': rule_text,
                    'llm_interpretation': None
                }
            prompt = f"""You are a data quality expert. Analyze this cleansing rule thoroughly:

Column: {column}
Rule: {rule_text}

Provide:
1. What this rule means exactly
2. What transformations should be applied
3. Any edge cases or special handling needed
4. Validation criteria

Be very specific about the exact transformations needed."""
            try:
                interpretation = self.llm_client.complete(prompt, timeout=timeout)
                return column, {
                    'user_rule': rule_text,
                    'llm_interpretation': interpretation
                }
            except Exception as e:
                logger.warning(f"  Could not interpret rule for {column}: {e}")
                return column, {
                    'user_rule': rule_text,
                    'llm_interpretation': None
                }

        items = list(self.rules_for_cleaning.items())
        if use_concurrent and items:
            max_workers = min(2, len(items))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures_map = {ex.submit(interpret, it): it for it in items}
                for fut in concurrent.futures.as_completed(futures_map):
                    col, res = fut.result()
                    interpreted_rules[col] = res
        else:
            for it in items:
                col, res = interpret(it)
                interpreted_rules[col] = res

        self.rules_for_cleaning = interpreted_rules
    
    def profile_data(self):
        """Profile the data for DQ assessment"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 2: DATA PROFILING")
        logger.info("="*80)
        
        if self.df_original is None:
            self.load_data()
        
        profile = {
            'total_records': len(self.df_original),
            'total_columns': len(self.df_original.columns),
            'columns': {},
            'data_quality_issues': []
        }
        
        # Profile each column
        columns = list(self.df_original.columns)
        for col in columns:
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
            
            # Use LLM to detect issues. In fast mode we'll batch/parallelize these calls.
            if self.llm_client.available:
                # collect profiles, will run detection after building profile map
                pass

        # If LLM available, detect issues for all columns (skip in fast mode to avoid timeouts)
        if not self.fast_mode and self.llm_client.available:
            col_items = [(c, profile['columns'][c]) for c in profile['columns']]
            for c, p in col_items:
                issues = self._detect_issues_with_llm(c, p)
                if issues:
                    profile['data_quality_issues'].extend(issues)
        elif self.fast_mode:
            logger.info("Fast mode: skipping per-column LLM issue detection")
        
        self.assessment_report = profile
        logger.info(f"Profiling complete: {profile['total_records']} records analyzed")
        return profile
    
    def _detect_issues_with_llm(self, column, col_profile, timeout: int | None = None):
        """Use LLM to detect data quality issues in a column"""
        prompt = f"""Analyze this column profile and identify data quality issues:

Column: {column}
Data Type: {col_profile['data_type']}
Non-null: {col_profile['non_null_count']} ({100-col_profile['null_percentage']:.1f}%)
Null: {col_profile['null_count']} ({col_profile['null_percentage']:.1f}%)
Unique Values: {col_profile['unique_values']}
Sample Values: {col_profile['sample_values']}

List specific data quality issues found."""
        
        try:
            response = self.llm_client.complete(prompt, timeout=timeout)
            if not response:
                return []
            # Parse issues from response (simple heuristic)
            return [f"{column}: {response.strip()[:200]}"]
        except Exception as e:
            logger.warning(f"LLM detection failed for {column}: {e}")
            return []
    
    def detect_violations(self):
        """Detect and categorize violations by dimension"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 2B: VIOLATION DETECTION")
        logger.info("="*80)
        
        violations_by_dimension = {
            'Completeness': [],      # Null/missing values
            'Validity': [],           # Format/type issues
            'Uniqueness': [],         # Duplicate issues
            'Consistency': [],        # Cross-field consistency
            'Accuracy': [],           # Value correctness
            'Timeliness': [],         # Date/time issues
        }
        
        violations_by_column = {}
        
        # Check each column for violations
        for col, profile in self.assessment_report['columns'].items():
            violations_by_column[col] = 0
            
            # COMPLETENESS: Check for nulls
            if profile['null_percentage'] > 0:
                violations = int(profile['null_count'])
                violations_by_dimension['Completeness'].append({
                    'column': col,
                    'type': 'Missing Values',
                    'severity': 'HIGH' if profile['null_percentage'] > 10 else 'MEDIUM',
                    'count': violations,
                    'percentage': profile['null_percentage']
                })
                violations_by_column[col] += violations
            
            # VALIDITY: Check for common format issues
            if 'date' in col.lower() or 'dob' in col.lower():
                # Sample check for date format issues
                non_null_vals = self.df_original[col].dropna()
                if len(non_null_vals) > 0:
                    bad_format = 0
                    for val in non_null_vals.sample(min(100, len(non_null_vals))):
                        if not self._is_valid_date(str(val)):
                            bad_format += 1
                    if bad_format > 0:
                        violations_by_dimension['Validity'].append({
                            'column': col,
                            'type': 'Invalid Date Format',
                            'severity': 'HIGH',
                            'count': bad_format,
                            'percentage': (bad_format / len(non_null_vals)) * 100
                        })
                        violations_by_column[col] += bad_format
            
            # VALIDITY: Check for email format issues
            if 'email' in col.lower():
                non_null_vals = self.df_original[col].dropna()
                if len(non_null_vals) > 0:
                    bad_format = sum(1 for v in non_null_vals if '@' not in str(v))
                    if bad_format > 0:
                        violations_by_dimension['Validity'].append({
                            'column': col,
                            'type': 'Invalid Email Format',
                            'severity': 'MEDIUM',
                            'count': bad_format,
                            'percentage': (bad_format / len(non_null_vals)) * 100
                        })
                        violations_by_column[col] += bad_format
            
            # VALIDITY: Check for phone format issues
            if 'phone' in col.lower():
                non_null_vals = self.df_original[col].dropna()
                if len(non_null_vals) > 0:
                    import re
                    bad_format = sum(1 for v in non_null_vals if len(re.sub(r'\D', '', str(v))) < 10)
                    if bad_format > 0:
                        violations_by_dimension['Validity'].append({
                            'column': col,
                            'type': 'Invalid Phone Format',
                            'severity': 'MEDIUM',
                            'count': bad_format,
                            'percentage': (bad_format / len(non_null_vals)) * 100
                        })
                        violations_by_column[col] += bad_format
            
            # UNIQUENESS: Check for duplicates
            if 'id' in col.lower() or 'number' in col.lower():
                non_null_vals = self.df_original[col].dropna()
                duplicates = len(non_null_vals) - non_null_vals.nunique()
                if duplicates > 0:
                    violations_by_dimension['Uniqueness'].append({
                        'column': col,
                        'type': 'Duplicate Values',
                        'severity': 'HIGH',
                        'count': duplicates,
                        'percentage': (duplicates / len(non_null_vals)) * 100
                    })
                    violations_by_column[col] += duplicates
        
        # Store violations in assessment report
        self.assessment_report['violations_by_dimension'] = violations_by_dimension
        self.assessment_report['violations_by_column'] = violations_by_column
        self.assessment_report['total_violations'] = sum(violations_by_column.values())
        
        # Log summary
        logger.info(f"\nViolations detected: {self.assessment_report['total_violations']}")
        for dimension, violations in violations_by_dimension.items():
            if violations:
                logger.info(f"  {dimension}: {len(violations)} issues")
                for v in violations[:3]:  # Show first 3
                    logger.info(f"    • {v['column']}: {v['type']} ({v['count']} records)")
        
        return violations_by_dimension
    
    def _is_valid_date(self, val):
        """Check if value looks like a valid date"""
        from dateutil import parser as date_parser
        try:
            date_parser.parse(str(val))
            return True
        except:
            return False
    
    def merge_custom_rules(self, custom_rules):
        """Merge custom rules with existing rules (with intelligent LLM interpretation using agents)
        FULLY DYNAMIC: Interprets ANY user input for ANY column using LLM"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 2: MERGING CUSTOM RULES (Dynamic LLM Agent Interpretation)")
        logger.info("="*80)
        
        if not custom_rules:
            logger.warning("No custom rules provided")
            return
        
        # CREATE MAPPING FROM RULE COLUMN NAMES TO ACTUAL DATA COLUMN NAMES
        column_name_mapping = {
            'Policy Number': 'policy_number',
            'policy_number': 'policy_number',
            'Policy Effective Date': 'policy_effective_date',
            'policy_effective_date': 'policy_effective_date',
            'Policy Expiry Date': 'policy_expiry_date',
            'policy_expiry_date': 'policy_expiry_date',
            'Policy Status': 'policy_status',
            'policy_status': 'policy_status',
            'Customer ID': 'customer_id',
            'Insured Customer ID': 'customer_id',
            'customer_id': 'customer_id',
            'Customer Name': 'customer_name',
            'Insured Name': 'customer_name',
            'customer_name': 'customer_name',
            'Email': 'email',
            'Contact Email': 'email',
            'email': 'email',
            'Phone': 'phone',
            'Contact Phone': 'phone',
            'phone': 'phone',
            'Date of Birth': 'customer_dob',
            'Customer DOB': 'customer_dob',
            'customer_dob': 'customer_dob',
        }
        
        logger.info(f"Custom rules received: {len(custom_rules)}")
        logger.info("Rules to interpret:")
        for col, rule in custom_rules.items():
            if rule and rule.strip():
                mapped_col = column_name_mapping.get(col, col)
                if col != mapped_col:
                    logger.info(f"  • {col} → {mapped_col}: \"{rule}\"")
                else:
                    logger.info(f"  • {col}: \"{rule}\"")
        
        # Use LLM AGENTS to intelligently interpret EACH custom rule DYNAMICALLY
        for col, custom_rule_text in custom_rules.items():
            if not custom_rule_text or not custom_rule_text.strip():
                logger.debug(f"  Skipping empty rule for '{col}'")
                continue
            
            # MAP column name to actual data column
            actual_col = column_name_mapping.get(col, col)
            
            if actual_col not in self.df_original.columns:
                logger.warning(f"  Column '{col}' (mapped to '{actual_col}') not found in data, skipping")
                continue
            
            logger.info(f"\n  ▶ AGENT TASK: Interpret user requirement for '{actual_col}' (rule: {col})")
            
            # Get sample values and column info for context
            sample_values = self.df_original[actual_col].dropna().head(5).tolist()
            data_type = str(self.df_original[actual_col].dtype)
            null_count = self.df_original[actual_col].isna().sum()
            total_count = len(self.df_original[actual_col])
            
            logger.info(f"    Data context:")
            logger.info(f"      Column type: {data_type}")
            logger.info(f"      Null values: {null_count}/{total_count}")
            logger.info(f"      Sample values: {sample_values[:3]}")
            
            # Ask LLM AGENT to dynamically interpret the user's requirement
            if self.llm_client.available and not self.fast_mode:
                try:
                    # Create comprehensive prompt with FULL CONTEXT for dynamic interpretation
                    prompt = f"""You are a DATA TRANSFORMATION EXPERT AGENT with deep expertise in data quality.

YOUR MISSION: Interpret the user's requirement and CREATE THE EXACT TRANSFORMATION NEEDED.
This must work for ANY column type and ANY user input - be FULLY DYNAMIC.

CRITICAL: Do NOT hardcode solutions. INTERPRET the user input dynamically.

CONTEXT:
  Column Name: {actual_col}
  Data Type: {data_type}
  Null Count: {null_count}/{total_count}
  Sample Values: {sample_values[:3]}
  Total Records: {total_count}

USER REQUIREMENT (Read Carefully - This is what the user wants):
  "{custom_rule_text}"

YOUR TASK - CRITICAL REQUIREMENTS:
  1. READ the user requirement carefully - understand their intent
  2. Consider the current data type and values
  3. Determine WHAT EXACTLY needs to change
  4. Specify the EXACT transformation logic
  5. Handle NULL/NaN values appropriately
  6. Be DYNAMIC - don't assume standard transformations

RESPOND IN THIS EXACT FORMAT (ONE LINE ONLY):
TRANSFORMATION: [type] | PARAMETERS: [exact_details] | LOGIC: [your_interpretation] | NAN_HANDLING: [how_to_handle_nulls]

TRANSFORMATION TYPES (Choose the ONE that matches the user intent):
  • lowercase - Lowercase all text
  • uppercase - Uppercase all text
  • title_case - Title Case (First Letter Capitalized)
  • capitalize_first - Capitalize only first character
  • trim - Remove leading/trailing whitespace
  • standardize_phone - Format phone numbers
  • standardize_email - Clean email addresses
  • standardize_date - Parse and format dates (specify target format)
  • remove_special - Remove special characters
  • parse_number - Extract numeric values
  • replace - Replace specific text patterns
  • custom_format - Apply custom pattern/format
  • split_merge - Combine/split fields
  • encode_decode - Encoding transformations
  • conditional - Apply different logic based on conditions
  • custom_logic - Custom transformation (explain clearly)

NAN_HANDLING OPTIONS:
  • keep_null - Keep null values as-is
  • replace_with:[value] - Replace nulls with specific value
  • skip_if_null - Don't transform null values
  • remove_rows - Remove rows with nulls

CRITICAL EXAMPLES (showing DYNAMIC interpretation):
  User: "make it all uppercase"
    → TRANSFORMATION: uppercase | PARAMETERS: all_text | LOGIC: User wants all uppercase | NAN_HANDLING: keep_null

  User: "capitalize the first letter"
    → TRANSFORMATION: capitalize_first | PARAMETERS: first_char_only | LOGIC: Capitalize first character only | NAN_HANDLING: keep_null

  User: "convert to date format YYYY-MM-DD"
    → TRANSFORMATION: standardize_date | PARAMETERS: target_format=YYYY-MM-DD,auto_detect=true | LOGIC: Parse dates flexibly to ISO format | NAN_HANDLING: keep_null

  User: "format as +91-XXXXX-XXXXX"
    → TRANSFORMATION: custom_format | PARAMETERS: format_pattern=+91-XXXXX-XXXXX,extract_digits=true | LOGIC: Extract digits and apply Indian phone format | NAN_HANDLING: keep_null

  User: "remove special characters and make lowercase"
    → TRANSFORMATION: remove_special | PARAMETERS: keep_alphanumeric_and_spaces=true,then=lowercase | LOGIC: Remove special chars then lowercase | NAN_HANDLING: keep_null

  User: "clean email - lowercase and trim"
    → TRANSFORMATION: standardize_email | PARAMETERS: lowercase=true,trim=true,validate=false | LOGIC: Standardize email format | NAN_HANDLING: keep_null

  User: "replace missing values with 'Unknown'"
    → TRANSFORMATION: custom_logic | PARAMETERS: fill_nulls_with=Unknown | LOGIC: Replace null values with 'Unknown' string | NAN_HANDLING: replace_with:Unknown

Now interpret this user requirement for column "{actual_col}":
"{custom_rule_text}"

Your response (ONE LINE ONLY):"""
                    
                    # FAST PATH: Only call LLM if rule is complex, otherwise skip to heuristics
                    interpretation = None
                    if self.llm_client.is_complex_rule(custom_rule_text):
                        logger.info(f"    Complex rule detected - consulting LLM...")
                        # Use smart timeout: 3s for simple rules, 5s for complex
                        interpretation = self.llm_client.complete(prompt, force_llm=True)
                    else:
                        logger.info(f"    Simple rule - using fast heuristic...")
                    
                    if interpretation:
                        logger.info(f"    ✓ Agent Response:")
                        logger.info(f"      {interpretation[:150]}...")
                    else:
                        logger.info(f"    Using rule text directly for transformation")
                    
                    # Store the complete rule interpretation
                    self.rules_for_cleaning[actual_col] = {
                        'user_rule': custom_rule_text,
                        'llm_interpretation': interpretation,
                        'is_custom': True,
                        'sample_context': sample_values[:3],
                        'data_type': data_type,
                        'null_count': null_count
                    }
                    
                    logger.info(f"    ✓ Rule ready for dynamic transformation")
                except Exception as e:
                    logger.warning(f"    ✗ Agent failed: {e}")
                    logger.warning(f"    Storing rule for heuristic interpretation...")
                    self.rules_for_cleaning[actual_col] = {
                        'user_rule': custom_rule_text,
                        'llm_interpretation': None,
                        'is_custom': True,
                        'sample_context': sample_values[:3],
                        'data_type': data_type,
                        'null_count': null_count
                    }
            else:
                # No LLM available - store for heuristic interpretation
                logger.info(f"    LLM unavailable - storing for heuristic interpretation")
                self.rules_for_cleaning[actual_col] = {
                    'user_rule': custom_rule_text,
                    'llm_interpretation': None,
                    'is_custom': True,
                    'sample_context': sample_values[:3],
                    'data_type': data_type,
                    'null_count': null_count
                }
        
        logger.info("\n" + "="*80)
        custom_rule_count = len([r for r in self.rules_for_cleaning.values() if isinstance(r, dict) and r.get('is_custom')])
        logger.info(f"Custom rules merged: {custom_rule_count} rules ready for cleansing")
        logger.info("="*80)
    
    def generate_assessment_report(self):
        """Generate detailed assessment report"""
        logger.info("\n" + "="*80)
        logger.info("PHASE 3: GENERATING ASSESSMENT REPORT")
        logger.info("="*80)
        
        if self.assessment_report is None:
            self.profile_data()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'output/Assessment_Report_{timestamp}.json'
        
        total_violations = self.assessment_report.get('total_violations', 0)
        
        report = {
            'timestamp': timestamp,
            'data_file': self.data_path,
            'summary': {
                'total_records': self.assessment_report['total_records'],
                'total_columns': self.assessment_report['total_columns'],
                'columns_with_issues': len([c for c in self.assessment_report['columns'].values() 
                                           if c['null_percentage'] > 10]),
                'total_violations': total_violations
            },
            'column_profiles': self.assessment_report['columns'],
            'data_quality_issues': self.assessment_report.get('data_quality_issues', []),
            'violations_by_dimension': self.assessment_report.get('violations_by_dimension', {}),
            'violations_by_column': self.assessment_report.get('violations_by_column', {}),
            'rules_for_cleaning': self.rules_for_cleaning
        }
        
        # Save report
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Assessment report saved: {report_file}")
        
        # Create human-readable version
        text_report = f"""
DATA QUALITY ASSESSMENT REPORT
Generated: {timestamp}
Data File: {self.data_path}

SUMMARY
-------
Total Records: {report['summary']['total_records']}
Total Columns: {report['summary']['total_columns']}
Columns with Issues (>10% null): {report['summary']['columns_with_issues']}
Total Violations Found: {report['summary']['total_violations']}

COLUMN PROFILES
---------------
"""
        for col, profile in report['column_profiles'].items():
            text_report += f"\n{col}:"
            text_report += f"\n  Type: {profile['data_type']}"
            text_report += f"\n  Non-null: {profile['non_null_count']} ({100-profile['null_percentage']:.1f}%)"
            text_report += f"\n  Null: {profile['null_count']} ({profile['null_percentage']:.1f}%)"
            text_report += f"\n  Unique: {profile['unique_values']}"
            text_report += f"\n  Sample: {profile['sample_values']}\n"
        
        # Add violations by dimension
        text_report += "\nVIOLATIONS BY DIMENSION\n"
        text_report += "----------------------\n"
        for dimension, violations in report.get('violations_by_dimension', {}).items():
            if violations:
                text_report += f"\n{dimension}:\n"
                for v in violations:
                    text_report += f"  • {v['column']}: {v['type']} ({v['count']} records, {v['percentage']:.1f}%)\n"
        
        # Add violations by column
        text_report += "\nVIOLATIONS BY COLUMN\n"
        text_report += "-------------------\n"
        for col, count in sorted(report.get('violations_by_column', {}).items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                text_report += f"  {col}: {count} violations\n"
        
        text_report += "\nRULES FOR CLEANING\n"
        text_report += "------------------\n"
        for col, rule in self.rules_for_cleaning.items():
            if isinstance(rule, dict):
                is_custom = " [CUSTOM - OVERRIDE]" if rule.get('is_custom') else ""
                text_report += f"{col}: {rule.get('user_rule', 'N/A')}{is_custom}\n"
            else:
                text_report += f"{col}: {rule}\n"
        
        text_file = f'output/Assessment_Report_{timestamp}.txt'
        with open(text_file, 'w') as f:
            f.write(text_report)
        
        logger.info(f"Text report saved: {text_file}")
        logger.info("\n" + "="*80)
        logger.info("ASSESSMENT COMPLETE - NO CLEANSING YET")
        logger.info(f"Total Violations Found: {report['summary']['total_violations']}")
        logger.info("Awaiting user signal to begin cleansing phase")
        logger.info("="*80)
        
        return report
    
    def _load_rules_from_repository(self):
        """Load ALL rules from multiple sources in dq_validator schema"""
        rules = {}
        
        # Column name mapping from rules to data
        # First map DB rule names to standardized names, then to actual data columns
        column_mapping_to_standard = {
            'Insured Customer ID': 'customer_id',
            'Insured Name': 'customer_name',
            'Date of Birth / Incorporation Date': 'customer_dob',
            'National ID (PAN/SSN/Aadhaar)': 'national_id',
            'Address (Risk/Insured)': 'address',
            'Contact Email': 'email',
            'Contact Phone': 'phone',
            'Product / Line of Business Code': 'line_of_business',
            'Coverage Limit Amount': 'coverage_limit',
            'Coverage Deductible Amount': 'deductible',
            'Agent / Producer ID': 'agent_id',
            'Risk Object ID (Vehicle/Property)': 'risk_object',
            'Vehicle VIN / Property ID': 'vin_property_id',
            'Risk Location GeoCode': 'geo_code',
            'Policy Number': 'policy_number',
            'Policy Effective Date': 'policy_effective_date',
            'Policy Expiry Date': 'policy_expiry_date',
            'Policy Term Type': 'policy_term',
            'Policy Status': 'policy_status',
            'Coverage ID': 'coverage_code',
            'Coverage Name': 'coverage_name',
            'Premium Amount': 'premium',
            'Payment Plan': 'payment_frequency',
            'Agent Commission %': 'agent_commission',
            'Underwriter ID': 'underwriting_score',
            'Endorsement ID': 'endorsement',
            'Endorsement Effective Date': 'endorsement_date',
            'Cancellation Effective Date': 'cancellation_date',
            'Renewal Indicator': 'renewal_flag',
            'Reinsurance Contract ID': 'reinsurance_flag',
            'Regulatory Reporting Flag': 'regulatory_reporting_flag',
        }
        
        # Load from Guidewire cleansing rules (primary source) in NeonDB
        try:
            from data_io.db_helpers import read_guidewire_cleansing_rules
            rules_df = read_guidewire_cleansing_rules()
            if rules_df is not None and not rules_df.empty:
                # Use CDE (Column Data Element) or cde/cde-like column
                cde_col = None
                for c in rules_df.columns:
                    if c.lower() in ('cde', 'column', 'column_name', 'cde_name'):
                        cde_col = c
                        break

                remediation_cols = [c for c in rules_df.columns if 'remediation' in c.lower() or 'remed' in c.lower()]
                if not remediation_cols:
                    # fallback: use all text columns except index-like fields
                    remediation_cols = [c for c in rules_df.columns if c not in (cde_col, 's_no')]

                for idx, row in rules_df.iterrows():
                    col_name = row[cde_col] if cde_col and pd.notna(row.get(cde_col)) else None
                    if not col_name:
                        continue
                    actual_col = column_mapping_to_standard.get(str(col_name), str(col_name))
                    rules_text = ' '.join([str(row[rc]) for rc in remediation_cols if pd.notna(row.get(rc))])
                    if rules_text.strip():
                        rules[actual_col] = rules_text
                logger.info(f"Loaded {len(rules)} rules from guidewire_policy_data_cleansing_rules (DB)")
        except Exception as e:
            logger.error(f"Error loading cleansing rules from DB: {e}")
        
        # Load from DQ Rule Repository Policy table in dq_validator schema
        try:
            import psycopg2
            conn = psycopg2.connect(os.environ.get('NEON_DB_URL') or "postgresql://neondb_owner:npg_RH4tS6KTciYv@ep-cool-bread-a4sb2gq8-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require", connect_timeout=5)
            conn.set_session(autocommit=True)
            cursor = conn.cursor()
            
            # Try loading from DQ_Rule_Repository-Policy table
            try:
                cursor.execute("SELECT * FROM dq_validator.\"DQ_Rule_Repository-Policy\" LIMIT 1000")
                dq_rule_repo = cursor.fetchall()
                if dq_rule_repo:
                    # Get column names
                    col_names = [desc[0] for desc in cursor.description]
                    cde_col = next((c for c in col_names if c.lower() in ('cde', 'column', 'column_name')), None)
                    if cde_col:
                        for row in dq_rule_repo:
                            row_dict = dict(zip(col_names, row))
                            col_name = row_dict.get(cde_col)
                            if col_name:
                                actual_col = column_mapping.get(str(col_name), str(col_name))
                                # Combine all non-CDE columns as rule text
                                rule_parts = [f"{k}: {v}" for k, v in row_dict.items() if k != cde_col and v]
                                if rule_parts:
                                    rules[actual_col] = ' | '.join(rule_parts)
                        logger.info(f"Loaded additional rules from DQ_Rule_Repository-Policy table")
            except Exception as e:
                logger.debug(f"Could not load DQ_Rule_Repository-Policy: {e}")
            
            # Try loading from other rule tables in the schema
            rule_tables = [
                'dq_validator."DQ_Dashboard_KPIs"',
                'dq_validator."DQ_Rule_Repository-Policy"',
                'dq_validator."Guidewire_Policy_DataCleansing_Rules"'
            ]
            
            for table_name in rule_tables:
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
                    result = cursor.fetchall()
                    if result:
                        col_names = [desc[0] for desc in cursor.description]
                        logger.debug(f"Found {len(result)} rows in {table_name}")
                except Exception as e:
                    logger.debug(f"Table {table_name} not accessible: {e}")
            
            cursor.close()
            conn.close()
        except Exception as e:
            logger.debug(f"Could not load additional rules from DB: {e}")
        
        # Fallback to DQ rule repository CSV file if needed
        if not rules:
            dq_file = 'data/DQ_Rule_Repository-Policy.csv'
            if Path(dq_file).exists():
                try:
                    rules_df = pd.read_csv(dq_file, encoding='latin-1')
                    if 'CDE' in rules_df.columns:
                        dq_cols = [c for c in rules_df.columns if c not in ['S No', 'CDE']]
                        for idx, row in rules_df.iterrows():
                            col_name = row['CDE']
                            # Map rule column name to data column name if needed
                            actual_col = column_mapping.get(col_name, col_name)
                            
                            rules_text = ' '.join([f"{dq}: {str(row[dq])}" for dq in dq_cols if pd.notna(row[dq])])
                            if rules_text.strip():
                                rules[actual_col] = rules_text
                        logger.info(f"Loaded {len(rules)} rules from {dq_file}")
                except Exception as e:
                    logger.error(f"Error loading DQ rules from CSV: {e}")
        
        logger.info(f"Total rules loaded from repository: {len(rules)}")
        return rules
    
    def _apply_standard_cleansing(self, df):
        """Apply standard repository cleansing rules to ALL records"""
        violations = {}
        
        # 1. STANDARDIZE DATES
        date_cols = ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB',
                     'Endorsement Effective Date', 'Cancellation Effective Date']
        
        for col in date_cols:
            if col not in df.columns:
                continue
            violations[col] = 0
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                try:
                    parsed = pd.to_datetime(val_str, infer_datetime_format=True)
                    standardized = parsed.strftime('%Y-%m-%d')
                    if val_str != standardized:
                        df.at[idx, col] = standardized
                        violations[col] += 1
                except:
                    pass  # Keep original if can't parse
        
        # 2. CLEAN EMAILS - lowercase and trim
        if 'Email' in df.columns:
            violations['Email'] = 0
            for idx, val in df['Email'].items():
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                cleaned = val_str.lower().strip()
                if val_str != cleaned:
                    df.at[idx, 'Email'] = cleaned
                    violations['Email'] += 1
        
        # 3. CLEAN PHONE - basic validation
        if 'Phone' in df.columns:
            violations['Phone'] = 0
            for idx, val in df['Phone'].items():
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                numeric = ''.join(c for c in val_str if c.isdigit())
                if len(numeric) < 7 or len(numeric) > 15:
                    df.at[idx, 'Phone'] = np.nan
                    violations['Phone'] += 1
        
        # 4. CLEAN TEXT FIELDS - trim whitespace
        text_cols = ['Customer Name', 'Address', 'Agent ID', 'Underwriter ID', 'Policy Status']
        for col in text_cols:
            if col not in df.columns:
                continue
            violations[col] = 0
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                cleaned = ' '.join(val_str.split())  # Remove extra spaces
                if val_str != cleaned:
                    df.at[idx, col] = cleaned
                    violations[col] += 1
        
        # 5. CLEAN NUMERIC FIELDS
        numeric_cols = ['Coverage Limit', 'Coverage Deductible', 'Premium Amount', 'Agent Commission %']
        for col in numeric_cols:
            if col not in df.columns:
                continue
            violations[col] = 0
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                try:
                    numeric_val = float(val)
                    if numeric_val < 0:
                        df.at[idx, col] = abs(numeric_val)
                        violations[col] += 1
                except:
                    df.at[idx, col] = np.nan
                    violations[col] += 1
        
        # 6. VALIDATE POLICY NUMBERS
        if 'Policy Number' in df.columns:
            violations['Policy Number'] = 0
            for idx, val in df['Policy Number'].items():
                if pd.isna(val):
                    violations['Policy Number'] += 1
                    continue
                val_str = str(val).strip()
                if not val_str.startswith('POL-'):
                    violations['Policy Number'] += 1
        
        # Log results
        for col, count in violations.items():
            if count > 0:
                logger.info(f"  ✓ {col}: {count} records standardized")
        
        return df, violations
    
    def perform_cleansing(self, skip_llm_guidance: bool = False, dedup_method: str = 'keep-first'):
        """
        Perform cleansing in 2 phases:
        1. STANDARD REPOSITORY RULES (always apply)
        2. CUSTOM RULES from user dashboard
        """
        logger.info("\n" + "="*80)
        logger.info("PHASE 4: CLEANSING DATA (User-initiated)")
        logger.info("="*80)
        
        df_clean = self.df_original.copy()
        violations_count = {}
        
        # PHASE 4A: Apply STANDARD REPOSITORY RULES
        logger.info("\nPHASE 4A: Applying Standard Repository Cleansing Rules")
        logger.info("-" * 80)
        df_clean, repo_violations = self._apply_standard_cleansing(df_clean)
        violations_count.update(repo_violations)
        
        # PHASE 4B: Apply CUSTOM RULES from dashboard
        if self.rules_for_cleaning:
            logger.info("\nPHASE 4B: Applying Custom User-Defined Rules")
            logger.info("-" * 80)
            logger.info(f"Applying {len(self.rules_for_cleaning)} custom rule(s)...")
            
            # DEBUG: Show what rules are loaded
            sample_col = list(self.rules_for_cleaning.keys())[0] if self.rules_for_cleaning else None
            if sample_col:
                sample_rule = self.rules_for_cleaning[sample_col]
                logger.info(f"DEBUG: Sample rule for '{sample_col}': {type(sample_rule)} = {str(sample_rule)[:100]}")
            
            # Prepare tasks for parallel processing
            columns_to_process = []
            for column, rule_info in self.rules_for_cleaning.items():
                if column not in df_clean.columns:
                    logger.warning(f"Column '{column}' not found")
                    continue
                
                if isinstance(rule_info, dict):
                    rule_text = rule_info.get('user_rule', '')
                else:
                    rule_text = rule_info
                
                if rule_text and rule_text.strip():
                    columns_to_process.append((column, rule_text))
            
            # Apply custom transformations to each column
            for column, rule_text in columns_to_process:
                logger.info(f"\n  ▶ Processing custom rule for '{column}'...")
                logger.info(f"    Rule: '{rule_text}'")
                
                # Track original values
                original_values = df_clean[column].copy()
                
                # DEBUG: For numeric columns, show sample original values
                if column in ['agent_commission', 'premium', 'coverage_limit']:
                    max_val = original_values.max()
                    min_val = original_values.min()
                    logger.info(f"    DEBUG: Original range [{min_val}, {max_val}]")
                
                # Get heuristic transformation (fast)
                transformation = self._get_heuristic_transformation(column, rule_text)
                
                if transformation is None:
                    logger.warning(f"    ✗ Could not determine transformation")
                    continue
                
                # Apply transformation
                try:
                    df_clean[column] = df_clean[column].apply(
                        lambda x: transformation(x) if pd.notna(x) else x
                    )
                    
                    # Count changes
                    changed = (original_values != df_clean[column]) & (original_values.notna())
                    count_changed = changed.sum()
                    
                    if count_changed > 0:
                        violations_count[column] = violations_count.get(column, 0) + count_changed
                        logger.info(f"    ✓ {count_changed} records transformed")
                        # Show sample
                        if len(original_values[changed]) > 0:
                            sample_orig = original_values[changed].iloc[0]
                            sample_new = df_clean[column][changed].iloc[0]
                            logger.info(f"      Sample: '{sample_orig}' → '{sample_new}' (type: {type(sample_new)})")
                    else:
                        # DEBUG: No changes detected - maybe all values are already in range?
                        if column in ['agent_commission', 'premium', 'coverage_limit', 'underwriting_score']:
                            sample_vals = df_clean[column].head(3).values
                            logger.info(f"    ℹ No changes (sample values: {sample_vals})")
                except Exception as e:
                    logger.warning(f"    ✗ Error applying transformation: {e}")
        
        else:
            logger.debug("(No custom rules defined)")
        
        # Apply deduplication based on dedup_method
        logger.info(f"\nPhase 4B: DEDUPLICATION (Method: {dedup_method})")
        original_row_count = len(df_clean)
        duplicates_before = df_clean.duplicated().sum()
        
        if dedup_method == 'keep-first':
            df_clean = df_clean.drop_duplicates(keep='first')
            logger.info(f"  Keeping first occurrence of duplicates")
        elif dedup_method == 'keep-last':
            df_clean = df_clean.drop_duplicates(keep='last')
            logger.info(f"  Keeping last occurrence of duplicates")
        elif dedup_method == 'remove-all':
            df_clean = df_clean.drop_duplicates(keep=False)
            logger.info(f"  Removing all duplicate records (keeping unique only)")
        else:
            logger.warning(f"  Unknown dedup method '{dedup_method}', keeping all records")
        
        rows_removed = original_row_count - len(df_clean)
        if rows_removed > 0:
            logger.info(f"  Duplicates found: {duplicates_before}")
            logger.info(f"  Records removed: {rows_removed}")
        else:
            logger.info(f"  No duplicates removed")
        
        logger.info(f"  Final row count: {len(df_clean)}")
        
        # Save cleaned data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'output/Sample_Policy_Data_CLEANED_{timestamp}.csv'
        df_clean.to_csv(output_file, index=False)
        
        logger.info(f"\n" + "="*80)
        logger.info(f"CLEANSING & DEDUPLICATION SUMMARY:")
        logger.info(f"="*80)
        total_violations = sum(violations_count.values())
        logger.info(f"  Total transformations applied: {total_violations}")
        logger.info(f"  Columns processed: {len(violations_count)}")
        logger.info(f"  Deduplication method: {dedup_method}")
        logger.info(f"  Records removed (duplicates): {rows_removed}")
        logger.info(f"  Original row count: {original_row_count}")
        logger.info(f"  Final row count: {len(df_clean)}")
        
        # Log violation breakdown
        if violations_count:
            logger.info(f"\n  Transformations by column:")
            for col, count in violations_count.items():
                if count > 0:
                    logger.info(f"    • {col}: {count} records cleaned")
        
        logger.info(f"\nCleaned data saved: {output_file}")
        logger.info("="*80)
        
        return df_clean
    
    def _get_transformation_task(self, column, rule_text, series):
        """Task wrapper for parallel LLM calls - COMPLETELY DYNAMIC
        LLM returns Python transformation code that we execute"""
        sample_values = series.dropna().head(5).tolist()
        
        prompt = f"""You are a Python transformation expert. Generate a transformation function.

COLUMN: {column}
SAMPLES: {sample_values}
REQUIREMENT: {rule_text}

Return ONLY a Python lambda function that transforms values.
Handle NaN: check if pd.notna(x) first
Keep format: lambda x: ... if pd.notna(x) else x

Examples:
  lambda x: x.upper() if pd.notna(x) else x
  lambda x: x.strip() if pd.notna(x) else x
  lambda x: int(x) if pd.notna(x) else x
  lambda x: '+91-' + str(x)[-10:] if pd.notna(x) else x

Generate transformation for: {rule_text}
Return ONLY the lambda function:"""
        
        try:
            # Use smart timeout: force_llm if rule is complex, quick fail otherwise
            response = self.llm_client.complete(prompt, force_llm=False)
            if response:
                logger.info(f"  LLM: {column} → {response[:80].strip()}")
                return self._eval_transformation(response.strip())
        except Exception as e:
            logger.warning(f"  LLM failed for {column}: {e}")
        
        return None
    
    def _eval_transformation(self, code_str):
        """Safely evaluate LLM-provided transformation code"""
        try:
            import pandas as pd
            import re
            import math
            from dateutil import parser as date_parser
            
            # Execute LLM-provided code
            local_vars = {
                'pd': pd,
                're': re,
                'math': math,
                'date_parser': date_parser,
                'datetime': __import__('datetime').datetime,
            }
            
            exec(f"transformation = {code_str}", {"__builtins__": {}}, local_vars)
            func = local_vars.get('transformation')
            
            if callable(func):
                logger.debug(f"    ✓ Transformation created: {code_str[:60]}")
                return func
            else:
                logger.warning(f"    Code did not create callable: {code_str}")
                return None
        except Exception as e:
            logger.warning(f"    Failed to evaluate: {e}")
            return None
    
    def _get_heuristic_transformation(self, column, rule_text):
        """Fallback heuristic if LLM fails"""
        logger.info(f"    Using heuristic fallback for '{column}'")
        col_lower = column.lower()
        rule_lower = rule_text.lower()
        
        # Simple heuristic - detect common patterns
        if any(x in col_lower for x in ['date', 'dob', 'birth']):
            logger.info(f"      → Detected date column")
            return lambda x: self._parse_and_standardize_date(x, '%Y-%m-%d') if pd.notna(x) else x
        
        if 'email' in col_lower:
            logger.info(f"      → Detected email column")
            return lambda x: str(x).lower().strip() if pd.notna(x) else x
        
        if 'phone' in col_lower or ('phone' in rule_lower or 'format' in rule_lower):
            logger.info(f"      → Detected phone column")
            return lambda x: self._standardize_phone_india(x) if pd.notna(x) else x
        
        logger.warning(f"      No heuristic match")
        return None
    
    def _standardize_phone(self, val):
        """Standardize phone to basic format"""
        import re
        # Remove all non-digits
        digits = re.sub(r'\D', '', str(val))
        # Format as (XXX) XXX-XXXX if 10 digits
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return val
    
    def _standardize_phone_india(self, val):
        """Standardize phone to format: +CC-XXXXX-XXXXX
        Default: +91 (India), but can handle any country code
        User test rule: format as +91-XXXXX-XXXXX or convert into +52-XXXXX-XXXXX"""
        import re
        if pd.isna(val):
            return val
        
        # Convert to string
        val_str = str(val).strip()
        
        # Remove all non-digits
        digits = re.sub(r'\D', '', val_str)
        
        # Default country code
        country_code = '91'  # India by default
        
        # Standard format: 10-digit Indian phone (most common case)
        if len(digits) == 10:
            return f"+{country_code}-{digits[:5]}-{digits[5:]}"
        # With country code prefix: 912345678901 → +91-23456-78901
        elif len(digits) == 12 and digits.startswith('91'):
            return f"+91-{digits[2:7]}-{digits[7:]}"
        # Already has country code but different format
        elif len(digits) >= 11:
            # Take last 10 digits and apply format
            last_10 = digits[-10:]
            return f"+{country_code}-{last_10[:5]}-{last_10[5:]}"
        # Less than 10 digits - try to pad or return as is
        elif len(digits) > 0:
            # If we have some digits but not 10, try to work with what we have
            if len(digits) >= 5:
                split_point = len(digits) - 5
                return f"+{country_code}-{digits[:split_point]}-{digits[split_point:]}"
        
        # If we can't parse, return original
        logger.debug(f"  Could not standardize phone: {val} (digits={digits})")
        return val
    
    def _standardize_phone_dynamic(self, val, country_code):
        """Standardize phone to format: +CC-XXXXX-XXXXX with DYNAMIC country code"""
        import re
        if pd.isna(val):
            return val
        
        val_str = str(val).strip()
        digits = re.sub(r'\D', '', val_str)
        
        # Format with extracted country code
        if len(digits) == 10:
            return f"+{country_code}-{digits[:5]}-{digits[5:]}"
        elif len(digits) >= 10:
            # Take last 10 digits
            last_10 = digits[-10:]
            return f"+{country_code}-{last_10[:5]}-{last_10[5:]}"
        elif len(digits) >= 5:
            split_point = len(digits) - 5
            return f"+{country_code}-{digits[:split_point]}-{digits[split_point:]}"
        
        return val
    
    def _parse_and_standardize_date(self, val, target_fmt):
        """Parse date in any format and standardize to target format"""
        from dateutil import parser as date_parser
        try:
            parsed = date_parser.parse(str(val))
            return parsed.strftime(target_fmt)
        except:
            return val
    
    def _get_heuristic_transformation(self, column, rule_text):
        """Fallback heuristic transformation when LLM is unavailable
        DYNAMIC: Attempts to interpret rule text without LLM"""
        import re
        
        rule_lower = rule_text.lower()
        col_lower = column.lower()
        
        logger.info(f"      Heuristic fallback: column='{col_lower}', rule='{rule_text[:50]}'")
        
        # PRIORITY 1: Column-name-driven detection (MOST SPECIFIC)
        # This should take priority over rule text because column names are reliable
        
        # Date columns - MUST check before generic format checking
        if any(kw in col_lower for kw in ['date', 'effective', 'expiry', 'endorse', 'cancel', 'birth', 'dob']):
            logger.info(f"      → Detected: Date Standardization (from column name)")
            format_str = '%Y-%m-%d'
            if 'yyyy-mm-dd' in rule_lower or 'yyyy/mm/dd' in rule_lower:
                format_str = '%Y-%m-%d'
            elif 'dd-mm-yyyy' in rule_lower or 'dd/mm/yyyy' in rule_lower:
                format_str = '%d-%m-%Y'
            elif 'mm-dd-yyyy' in rule_lower or 'mm/dd/yyyy' in rule_lower:
                format_str = '%m-%d-%Y'
            return lambda x: apply_nan_handling_default(x, lambda v: self._parse_and_standardize_date(v, format_str))
        
        # Policy/Contract numbers - MUST check before phone format
        if any(kw in col_lower for kw in ['policy', 'contract', 'policy_number', 'contract_id']):
            logger.info(f"      → Detected: Policy/Contract Number (from column name - preserving format)")
            return lambda x: apply_nan_handling_default(x, lambda v: str(v).strip().upper() if str(v).strip() else v)
        
        # Phone - check column name first
        if 'phone' in col_lower or 'mobile' in col_lower:
            country_match = re.search(r'\+(\d{1,3})', rule_text)
            if country_match:
                country_code = country_match.group(1)
                logger.info(f"      → Detected: Phone format +{country_code}-XXXXX-XXXXX (column-based)")
                return lambda x: self._standardize_phone_dynamic(x, country_code)
            else:
                logger.info(f"      → Detected: Phone format (column-based)")
                return lambda x: self._standardize_phone(x)
        
        # Email columns
        if 'email' in col_lower:
            # Check if rule asks for uppercase
            if 'uppercase' in rule_lower or 'upper case' in rule_lower:
                logger.info(f"      → Detected: Email as UPPERCASE (column-based + rule)")
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).upper().strip())
            else:
                logger.info(f"      → Detected: Email Standardization (column-based)")
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).lower().strip())
        
        # Customer/Name columns
        if any(kw in col_lower for kw in ['name', 'customer', 'insured']):
            if 'uppercase' in rule_lower or 'upper case' in rule_lower:
                logger.info(f"      → Detected: Name as UPPERCASE (column-based)")
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).upper())
            else:
                logger.info(f"      → Detected: Name Standardization (column-based)")
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).strip().title())
        
        # PRIORITY 2: Rule-text-driven detection
        
        # Uppercase detection
        if 'uppercase' in rule_lower or 'upper case' in rule_lower or 'make upper' in rule_lower:
            logger.info(f"      → Detected: UPPERCASE transformation")
            return lambda x: apply_nan_handling_default(x, lambda v: str(v).upper())
        
        # Lowercase detection
        if 'lowercase' in rule_lower or 'lower case' in rule_lower or 'make lower' in rule_lower:
            logger.info(f"      → Detected: lowercase transformation")
            return lambda x: apply_nan_handling_default(x, lambda v: str(v).lower())
        
        # Title case detection
        if 'title' in rule_lower or 'capitalize each' in rule_lower:
            logger.info(f"      → Detected: Title Case transformation")
            return lambda x: apply_nan_handling_default(x, lambda v: str(v).title())
        
        # Trim/whitespace
        if 'trim' in rule_lower or 'remove whitespace' in rule_lower or 'clean whitespace' in rule_lower:
            logger.info(f"      → Detected: Trim/Whitespace transformation")
            return lambda x: apply_nan_handling_default(x, lambda v: str(v).strip())
        
        # Remove special characters
        if 'remove special' in rule_lower or 'special char' in rule_lower or 'alphanumeric' in rule_lower:
            logger.info(f"      → Detected: Remove Special Characters")
            return lambda x: apply_nan_handling_default(x, lambda v: ''.join(c for c in str(v) if c.isalnum() or c.isspace()))
        
        # Email
        if 'email' in col_lower or 'email' in rule_lower:
            logger.info(f"      → Detected: Email Standardization")
            return lambda x: apply_nan_handling_default(x, lambda v: str(v).lower().strip())
        
        # Handle negative values and out-of-range checks
        # ONLY for EXPLICITLY NUMERIC columns - ignore generic DB rule text that mentions "out-of-range"
        # for text columns like policy numbers, IDs, etc.
        numeric_keywords = ['amount', 'limit', 'deductible', 'premium', 'commission', 'price', 'cost', 'score', 'percent', 'rate', 'ratio', 'coverage_limit', 'agent_commission', 'underwriting']
        is_numeric_column = any(kw in col_lower for kw in numeric_keywords)
        
        # Only check rule text for bounds keywords if column is ALREADY identified as numeric
        # This prevents matching generic "out-of-range" text in DB rules for ID/text columns
        bounds_keywords = ['negative', 'bounds', 'threshold', 'business range', 'reasonableness', 'constrain', 'valid range']
        has_bounds_rule = is_numeric_column and any(kw in rule_lower for kw in bounds_keywords)
        
        # Apply bounds/range handling ONLY if column is explicitly numeric AND has bounds keywords
        if is_numeric_column and has_bounds_rule:
            logger.info(f"      → Detected: Bounds/Range/Negative Handling (from rule)")
            
            # PRIORITY 1: For score/percentage columns - constrain to 0-100 (check FIRST because agent_commission contains both keywords)
            if any(kw in col_lower for kw in ['score', 'percent', 'underwriting']):
                logger.info(f"        → Score/Percentage column: constraining to 0-100 range")
                def constrain_percentage(v):
                    try:
                        val = float(v)
                        return max(0, min(100, val))
                    except:
                        return v
                return lambda x: apply_nan_handling_default(x, constrain_percentage)
            
            # PRIORITY 2: For agent commission specifically - constrain to 0-100 (percentage commission)
            elif col_lower == 'agent_commission' or col_lower == 'commission_percent':
                logger.info(f"        → Agent Commission (percentage): constraining to 0-100 range")
                def constrain_percentage(v):
                    try:
                        val = float(v)
                        result = max(0, min(100, val))
                        if val != result:
                            logger.debug(f"          Clamping {val} → {result}")
                        return result
                    except Exception as e:
                        logger.debug(f"          Error converting {v}: {e}")
                        return v
                return lambda x: apply_nan_handling_default(x, constrain_percentage)
            
            # PRIORITY 3: For other financial amounts - remove negatives
            elif any(kw in col_lower for kw in ['amount', 'limit', 'deductible', 'premium', 'price', 'cost']):
                logger.info(f"        → Financial column: removing negative values via absolute value")
                return lambda x: apply_nan_handling_default(x, lambda v: abs(float(v)) if pd.notna(v) and str(v).strip() else v)
            
            # PRIORITY 4: Generic numeric - ensure >= 0
            else:
                logger.info(f"        → Generic numeric: ensuring non-negative values")
                try:
                    return lambda x: apply_nan_handling_default(x, lambda v: v if (pd.notna(v) and float(v) >= 0) else 'OUT_OF_RANGE')
                except:
                    pass
        
        # Date
        if 'date' in col_lower or 'date' in rule_lower or any(d in rule_lower for d in ['yyyy', 'mm', 'dd', 'yyyy-mm', 'mm-dd']):
            # Try to extract format from rule
            format_str = '%Y-%m-%d'
            if 'yyyy' in rule_lower or 'dd-mm' in rule_lower or 'mm-dd' in rule_lower:
                if 'yyyy-mm-dd' in rule_lower or 'yyyy/mm/dd' in rule_lower:
                    format_str = '%Y-%m-%d'
                elif 'dd-mm-yyyy' in rule_lower or 'dd/mm/yyyy' in rule_lower:
                    format_str = '%d-%m-%Y'
                elif 'mm-dd-yyyy' in rule_lower or 'mm/dd/yyyy' in rule_lower:
                    format_str = '%m-%d-%Y'
            logger.info(f"      → Detected: Date Standardization (format: {format_str})")
            return lambda x: apply_nan_handling_default(x, lambda v: self._parse_and_standardize_date(v, format_str))
        
        # IMPORTANT: Handle Policy/Contract numbers BEFORE generic "extract numbers" rule
        # These should preserve prefixes like "POL-" or "CONT-"
        if any(kw in col_lower for kw in ['policy', 'contract', 'policy_number', 'contract_id']):
            logger.info(f"      → Detected: Policy/Contract Number (preserving format)")
            # For policy numbers: trim, uppercase, but keep the prefix (POL-, CONT-, etc.)
            return lambda x: apply_nan_handling_default(x, lambda v: str(v).strip().upper() if str(v).strip() else v)
        
        # Extract numbers - ONLY for actual numeric columns, NOT for ID columns
        if ('number' in rule_lower or 'numeric' in rule_lower or 'digits' in rule_lower) and not any(kw in col_lower for kw in ['id', 'policy', 'contract', 'code', 'reference']):
            logger.info(f"      → Detected: Extract Numbers/Digits")
            return lambda x: apply_nan_handling_default(x, lambda v: ''.join(c for c in str(v) if c.isdigit() or c == '.'))
        
        # Fill nulls
        if 'null' in rule_lower or 'missing' in rule_lower or 'empty' in rule_lower or 'na' in rule_lower:
            if 'fill' in rule_lower or 'replace' in rule_lower:
                logger.info(f"      → Detected: Fill NULL values")
                fill_val = 'NA'
                if 'fill' in rule_lower and ':' in rule_text:
                    parts = rule_text.split(':')
                    if len(parts) > 1:
                        fill_val = parts[1].strip()
                return lambda x: fill_val if pd.isna(x) else x
        
        # Replace text
        if 'replace' in rule_lower and ':' in rule_text:
            logger.info(f"      → Detected: Text Replacement")
            parts = rule_text.split(':')
            if len(parts) >= 2:
                old_val = parts[0].replace('replace', '').strip()
                new_val = parts[1].strip()
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).replace(old_val, new_val))
        
        # Generic rule: trigger/workflow/exception logic - apply cleanup transformations
        if any(kw in rule_lower for kw in ['trigger', 'workflow', 'steward', 'exception', 'auto-fill', 'auto fill']):
            logger.info(f"      → Detected: Generic workflow rule - applying column-specific cleanup")
            # For text columns (name, address, status, etc)
            if any(kw in col_lower for kw in ['name', 'address', 'status', 'customer', 'insured', 'agent', 'description']):
                logger.info(f"        → Text column detected: applying trim + title case")
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).strip().title() if str(v).strip() else v)
            # For ID columns (id, number, code, etc)
            elif any(kw in col_lower for kw in ['id', 'number', 'code', 'contract', 'policy']):
                logger.info(f"        → ID column detected: applying trim + uppercase")
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).strip().upper() if str(v).strip() else v)
            # For phone
            elif 'phone' in col_lower:
                logger.info(f"        → Phone column detected: applying phone standardization")
                return lambda x: self._standardize_phone_india(x) if pd.notna(x) else x
            # For email
            elif 'email' in col_lower:
                logger.info(f"        → Email column detected: applying lowercase + trim")
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).lower().strip())
            # Default for numeric columns
            else:
                logger.info(f"        → Applying default cleanup (trim whitespace)")
                return lambda x: apply_nan_handling_default(x, lambda v: str(v).strip() if isinstance(v, str) else v)
        
        logger.info(f"      → No heuristic match found, applying default cleanup (trim + normalize spaces)")
        # Default fallback: trim and normalize whitespace
        return lambda x: apply_nan_handling_default(x, lambda v: ' '.join(str(v).split()) if isinstance(v, str) and str(v).strip() else v)


def apply_nan_handling_default(val, fn):
    """Default NaN handling: skip nulls"""
    if pd.isna(val):
        return val
    return fn(val)

def main():
    """Main entry point"""
    import sys
    
    # Check for command line arguments
    data_file = 'data/Sample_Policy_Data.csv'
    rules_file = None
    custom_rules = None
    run_cleansing = False
    dedup_method = 'keep-first'
    
    if '--clean' in sys.argv:
        run_cleansing = True
    
    # Handle both --rules and --rules-file
    if '--rules' in sys.argv:
        idx = sys.argv.index('--rules')
        if idx + 1 < len(sys.argv):
            rules_file = sys.argv[idx + 1]
    elif '--rules-file' in sys.argv:
        idx = sys.argv.index('--rules-file')
        if idx + 1 < len(sys.argv):
            rules_file = sys.argv[idx + 1]
    
    # DEFAULT: Auto-detect user rules if no explicit rules provided
    if not rules_file:
        # Check for user-defined rules in common locations (JSON first, then CSV)
        potential_paths = [
            Path('output/cleansing_rules.json'),
            Path('cleansing_rules.json'),
            Path('./cleansing_rules.json'),
            Path('output/cleansing_rules.csv'),
            Path('cleansing_rules.csv'),
            Path('./cleansing_rules.csv'),
        ]
        for path in potential_paths:
            if path.exists():
                rules_file = str(path)
                logger.info(f"Auto-detected user rules: {path}")
                break
    
    if '--dedup-method' in sys.argv:
        idx = sys.argv.index('--dedup-method')
        if idx + 1 < len(sys.argv):
            dedup_method = sys.argv[idx + 1]
    
    # Initialize pipeline
    logger.info("Starting DQ Pipeline - Assessment First")
    pipeline = DQAssessmentFirst(data_path=data_file)
    
    # Fast mode: skip expensive LLM calls for faster profiling
    if '--fast' in sys.argv:
        pipeline.fast_mode = True
        try:
            pipeline.llm_client.enabled = True
            pipeline.llm_client.timeout = 45
        except Exception:
            pass
    
    # Load data
    pipeline.load_data()
    
    # Determine rules source
    # Priority: explicit rules file > standard rules (with dashboard overrides only)
    # The standard rules load process handles all the mapping correctly
    rules_source = None
    
    if rules_file and Path(rules_file).exists():
        rules_source = rules_file
        logger.info(f"Using rules file: {rules_file}")
    else:
        # Load rules through standard process (handles column mapping correctly)
        # If dashboard_rules exist, they will be loaded and merged by load_and_interpret_rules
        rules_source = None  # None will trigger _load_rules_from_repository() with proper mapping
    
    # Load rules (None will trigger standard rules)
    pipeline.load_and_interpret_rules(rules_source)

    
    # Profile and assess with violation detection
    pipeline.profile_data()
    pipeline.detect_violations()
    pipeline.generate_assessment_report()
    
    # Cleanse only if requested
    if run_cleansing:
        # Merge rules: standard rules + custom rules (custom overrides)
        # Use intelligent LLM interpretation with agents
        if custom_rules:
            logger.info("\n" + "="*80)
            logger.info("USING LLM AGENTS TO READ AND INTERPRET USER INPUTS")
            logger.info("="*80)
            pipeline.merge_custom_rules(custom_rules)
        
        # Apply cleansing with deduplication
        pipeline.perform_cleansing(skip_llm_guidance=False, dedup_method=dedup_method)
    else:
        logger.info("\nTo perform cleansing, call with --clean flag or click 'Clean My Data' in dashboard")


if __name__ == '__main__':
    main()
