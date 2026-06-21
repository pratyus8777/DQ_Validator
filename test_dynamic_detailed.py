#!/usr/bin/env python3
"""
Test the DYNAMIC transformation system with detailed logs
"""

import json
import pandas as pd
from pathlib import Path
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,  # Show debug logs
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from assessment_first_pipeline import DQAssessmentFirst
    
    # Load data
    df = pd.read_csv('data/Sample_Policy_Data.csv')
    
    # Load rules
    with open('output/cleansing_rules.json', 'r') as f:
        rules = json.load(f)
    
    # Filter rules
    custom_rules = {k: v for k, v in rules.items() if v and v.strip()}
    
    # Create pipeline
    pipeline = DQAssessmentFirst()
    pipeline.df_original = df
    pipeline.df = df.copy()
    
    logger.info("="*80)
    logger.info("DYNAMIC TRANSFORMATION TEST")
    logger.info("="*80)
    logger.info(f"\nRules to apply: {custom_rules}")
    logger.info(f"\nMerging rules with LLM interpretation...\n")
    
    # Merge rules (this calls LLM)
    pipeline.merge_custom_rules(custom_rules)
    
    logger.info(f"\nRules ready for cleansing: {pipeline.rules_for_cleaning}")
    
    logger.info("\n" + "="*80)
    logger.info("APPLYING TRANSFORMATIONS")
    logger.info("="*80 + "\n")
    
    # Perform cleansing
    df_cleaned = pipeline.perform_cleansing(skip_llm_guidance=False, dedup_method='keep-first')
    
    if df_cleaned is not None:
        logger.info("\n✓ SUCCESS")
        logger.info(f"  Before: {df['Phone'].iloc[0]}")
        logger.info(f"  After:  {df_cleaned['Phone'].iloc[0]}")

except Exception as e:
    logger.error(f"Error: {e}")
    import traceback
    traceback.print_exc()
