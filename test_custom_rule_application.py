#!/usr/bin/env python3
"""
Test script to verify custom rule loading and LLM-based interpretation
Tests the user's test rule: "format as +91-XXXXX-XXXXX" for Phone column
"""

import json
import sys
import pandas as pd
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

def test_rule_loading():
    """Test that custom rules are properly loaded from cleansing_rules.json"""
    logger.info("="*80)
    logger.info("TEST 1: Rule Loading from Dashboard Saved File")
    logger.info("="*80)
    
    # Load rules from Neon DB guidewire table
    try:
        from data_io.db_helpers import read_guidewire_cleansing_rules
        rules_df = read_guidewire_cleansing_rules()
        if rules_df is None or rules_df.empty:
            logger.error("❌ No rules found in guidewire_policy_data_cleansing_rules (DB)")
            return False
        # Heuristic mapping to column_name and rule_definition
        name_col = next((c for c in rules_df.columns if 'column' in c.lower() or 'cde' in c.lower()), None)
        rule_col = next((c for c in rules_df.columns if 'rule' in c.lower() or 'remediation' in c.lower() or 'definition' in c.lower()), None)
        rules = {}
        if name_col and rule_col:
            for _, r in rules_df.iterrows():
                k = r.get(name_col)
                v = r.get(rule_col)
                if k and v and str(v).strip():
                    rules[str(k)] = str(v)
    except Exception as e:
        logger.error(f"❌ Failed to load rules from DB: {e}")
        return False
        
        logger.info(f"✓ Successfully loaded {len(rules)} rules")
        
        # Check for Phone rule
        if 'Phone' in rules and rules['Phone']:
            logger.info(f"✓ Phone rule found: '{rules['Phone']}'")
            if 'format as +91-XXXXX-XXXXX' in rules['Phone']:
                logger.info(f"✓ Test rule detected: Indian phone format")
                return True
        else:
            logger.error(f"❌ Phone rule not found in {rules_file}")
            logger.error(f"   Available rules: {list(rules.keys())}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Failed to load rules: {e}")
        return False

def test_rule_filtering():
    """Test that empty rules are filtered out"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Rule Filtering (Empty Rules)")
    logger.info("="*80)
    
    try:
        with open('output/cleansing_rules.json', 'r') as f:
            rules = json.load(f)
        
        # Filter out empty rules (as done in pipeline)
        filtered_rules = {k: v for k, v in rules.items() if v and v.strip()}
        
        logger.info(f"  Original rules: {len(rules)}")
        logger.info(f"  Filtered rules: {len(filtered_rules)}")
        
        non_empty = [f"{k}='{v}'" for k, v in filtered_rules.items()]
        if non_empty:
            logger.info(f"  Non-empty rules: {', '.join(non_empty[:3])}")
        
        if 'Phone' in filtered_rules:
            logger.info(f"✓ Phone rule passed filter: '{filtered_rules['Phone']}'")
            return True
        else:
            logger.error(f"❌ Phone rule was filtered out!")
            return False
    
    except Exception as e:
        logger.error(f"❌ Failed to filter rules: {e}")
        return False

def test_phone_standardization():
    """Test the Indian phone standardization function"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Phone Standardization (+91-XXXXX-XXXXX Format)")
    logger.info("="*80)
    
    # Import the pipeline to access the standardization method
    try:
        sys.path.insert(0, str(Path.cwd()))
        from assessment_first_pipeline import DQAssessmentFirst
        
        # Create a minimal pipeline instance for testing
        logger.info("  Creating pipeline instance...")
        pipeline = DQAssessmentFirst()
        
        # Test cases for Indian phone format
        test_cases = [
            ("9876543210", "+91-98765-43210"),      # 10 digits
            ("919876543210", "+91-98765-43210"),     # 12 digits with 91
            ("9876543210", "+91-98765-43210"),       # Basic case
            ("+91 9876543210", "+91-98765-43210"),   # With country code
            ("(98) 76543210", "+91-98765-43210"),    # With formatting
        ]
        
        logger.info("  Testing phone format conversions:")
        all_passed = True
        for input_val, expected in test_cases:
            result = pipeline._standardize_phone_india(input_val)
            status = "✓" if result == expected else "❌"
            logger.info(f"    {status} '{input_val}' → '{result}' (expected: '{expected}')")
            if result != expected:
                all_passed = False
        
        return all_passed
    
    except Exception as e:
        logger.error(f"❌ Phone standardization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transformation_parsing():
    """Test LLM response parsing for transformation creation"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: LLM Response Parsing")
    logger.info("="*80)
    
    try:
        from assessment_first_pipeline import DQAssessmentFirst
        pipeline = DQAssessmentFirst()
        
        # Test LLM response parsing
        test_responses = [
            "TRANSFORMATION: standardize_phone | PARAMETERS: format=+91-XXXXX-XXXXX | LOGIC: User wants Indian phone format",
            "TRANSFORMATION: custom_format | PARAMETERS: format_pattern=+91-XXXXX-XXXXX,regex_extract=digits | LOGIC: Apply custom phone format",
        ]
        
        logger.info("  Testing LLM response parsing:")
        for response in test_responses:
            logger.info(f"    Response: {response[:60]}...")
            transformation = pipeline._parse_and_create_transformation(
                response, 
                "Phone", 
                "format as +91-XXXXX-XXXXX"
            )
            if transformation:
                logger.info(f"    ✓ Successfully created transformation function")
                # Test the transformation
                test_result = transformation("9876543210")
                logger.info(f"    ✓ Transformation result: '9876543210' → '{test_result}'")
            else:
                logger.error(f"    ❌ Failed to create transformation")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Transformation parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_pipeline():
    """Test the full pipeline with custom rules"""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Full Pipeline with Custom Rules")
    logger.info("="*80)
    
    try:
        from assessment_first_pipeline import DQAssessmentFirst
        
        # Check if data exists
        # Load data from Neon DB
        try:
            from data_io.db_helpers import read_sample_policy_data
            df = read_sample_policy_data(limit=1000)
            logger.info(f"  Data loaded from DB: {len(df)} rows, {len(df.columns)} columns")
        except Exception as e:
            logger.error(f"❌ Data load failed: {e}")
            return False
        
        logger.info("  Creating and initializing pipeline...")
        pipeline = DQAssessmentFirst()
        pipeline.df_original = df  # Initialize with data
        pipeline.df = df.copy()
        
        # Check if rules were loaded
        with open('output/cleansing_rules.json', 'r') as f:
            custom_rules = json.load(f)
        
        # Filter empty rules
        custom_rules = {k: v for k, v in custom_rules.items() if v and v.strip()}
        
        if custom_rules:
            logger.info(f"✓ Custom rules loaded: {len(custom_rules)} rules")
            logger.info(f"  Rules: {list(custom_rules.keys())}")
            
            # Merge custom rules with pipeline
            logger.info("  Merging custom rules with pipeline...")
            pipeline.merge_custom_rules(custom_rules)
            
            logger.info(f"✓ Custom rules merged")
            logger.info(f"  Rules for cleaning: {len(pipeline.rules_for_cleaning)}")
            
            # Check if Phone rule is in rules_for_cleaning
            if 'Phone' in pipeline.rules_for_cleaning:
                logger.info(f"✓ Phone rule is ready for cleansing")
                rule_info = pipeline.rules_for_cleaning['Phone']
                if isinstance(rule_info, dict):
                    logger.info(f"  User rule: {rule_info.get('user_rule')}")
                    llm_interp = rule_info.get('llm_interpretation', 'N/A')
                    if llm_interp:
                        logger.info(f"  LLM interpretation: {str(llm_interp)[:80]}")
                    else:
                        logger.info(f"  LLM interpretation: (Not available - using heuristic)")
            
            return True
        else:
            logger.error("❌ No custom rules found after filtering")
            return False
    
    except Exception as e:
        logger.error(f"❌ Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("\n" + "="*80)
    logger.info("CUSTOM RULE APPLICATION TEST SUITE")
    logger.info("Testing: User rule 'format as +91-XXXXX-XXXXX' for Phone column")
    logger.info("="*80 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Rule Loading", test_rule_loading()))
    results.append(("Rule Filtering", test_rule_filtering()))
    results.append(("Phone Standardization", test_phone_standardization()))
    results.append(("Transformation Parsing", test_transformation_parsing()))
    results.append(("Full Pipeline", test_full_pipeline()))
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "❌ FAILED"
        logger.info(f"  {status}: {test_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    logger.info(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        logger.info("\n✓ All tests passed! Custom rules are ready to be applied.")
        logger.info("\nNext step: Run Tab 4 in dashboard to clean data with custom rules")
        return 0
    else:
        logger.error(f"\n❌ {total_count - passed_count} tests failed. Check logs above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
