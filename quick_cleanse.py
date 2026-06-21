#!/usr/bin/env python
"""
Quick cleansing script - applies custom rules without profiling
"""
import json
import pandas as pd
from pathlib import Path
from agents.standardization_rules import CustomCleansingRuleParser
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_custom_rules():
    """Load data, apply custom rules, save cleaned data"""
    
    logger.info("="*80)
    logger.info("QUICK CLEANSING - Applying Custom Rules")
    logger.info("="*80)
    
    # Load original data
    logger.info("\n1. Loading data...")
    df_original = pd.read_csv('data/Sample_Policy_Data.csv')
    logger.info(f"   Loaded {df_original.shape[0]} records x {df_original.shape[1]} columns")
    
    # Load rules
    logger.info("\n2. Loading cleansing rules...")
    # Prefer DB-based guidewire rules
    try:
        from data_io.db_helpers import read_guidewire_cleansing_rules
        rules_df = read_guidewire_cleansing_rules()
    except Exception:
        rules_file = Path('output/cleansing_rules.json')
        rules_df = None
    if not rules_file.exists():
        logger.error("   Rules file not found!")
        return False
    
    with open(rules_file, 'r') as f:
        rules = json.load(f)
    
    non_empty_rules = {k: v for k, v in rules.items() if v and v.strip()}
    logger.info(f"   Loaded {len(non_empty_rules)} non-empty rules:")
    for col, rule in non_empty_rules.items():
        logger.info(f"      - {col}: {rule}")
    
    # Apply rules
    logger.info("\n3. Applying rules...")
    df_clean = df_original.copy()
    
    for column, rule_text in non_empty_rules.items():
        if column not in df_clean.columns:
            logger.warning(f"   Column '{column}' not found")
            continue
        
        logger.info(f"   Processing '{column}': {rule_text[:50]}")
        
        try:
            # Parse rule
            parsed_rule = CustomCleansingRuleParser.parse_custom_rule(rule_text)
            
            # Apply rule
            df_clean[column] = df_clean[column].apply(
                lambda x: CustomCleansingRuleParser.apply_custom_rule(x, parsed_rule)
            )
            
            num_ops = len(parsed_rule.get('operations', []))
            logger.info(f"      Applied {num_ops} transformation(s)")
            
        except Exception as e:
            logger.error(f"      Failed: {e}")
    
    # Save cleaned data
    logger.info("\n4. Saving cleaned data...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'output/Sample_Policy_Data_CLEANED_{timestamp}.csv'
    df_clean.to_csv(output_file, index=False)
    logger.info(f"   Saved to {output_file}")
    
    # Show sample
    logger.info("\n5. Sample results:")
    for column in non_empty_rules.keys():
        if column in df_clean.columns:
            logger.info(f"\n   {column}:")
            logger.info(f"      Before: {df_original[column].iloc[0]}")
            logger.info(f"      After:  {df_clean[column].iloc[0]}")
    
    logger.info("\n" + "="*80)
    logger.info("CLEANSING COMPLETE")
    logger.info("="*80)
    
    return True

if __name__ == '__main__':
    success = apply_custom_rules()
    exit(0 if success else 1)
