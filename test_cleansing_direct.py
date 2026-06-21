#!/usr/bin/env python3
"""
Quick test to verify custom rule is being applied during cleansing
"""

import json
import pandas as pd
from pathlib import Path
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

def test_cleansing():
    """Test cleansing with custom phone rule"""
    logger.info("="*80)
    logger.info("TESTING CUSTOM RULE CLEANSING")
    logger.info("="*80)
    
    try:
        from assessment_first_pipeline import DQAssessmentFirst
        
        # Load data
        logger.info("\n1. Loading data...")
        df = pd.read_csv('data/Sample_Policy_Data.csv')
        logger.info(f"   ✓ Data loaded: {len(df)} rows, {len(df.columns)} columns")
        logger.info(f"   Phone column sample (before): {df['Phone'].head(3).tolist()}")
        
        # Load rules
        logger.info("\n2. Loading custom rules...")
        with open('output/cleansing_rules.json', 'r') as f:
            rules = json.load(f)
        logger.info(f"   ✓ Rules loaded: {len(rules)} total")
        if 'Phone' in rules:
            logger.info(f"   ✓ Phone rule: '{rules['Phone']}'")
        
        # Create pipeline
        logger.info("\n3. Creating pipeline...")
        pipeline = DQAssessmentFirst()
        pipeline.df_original = df
        pipeline.df = df.copy()
        logger.info(f"   ✓ Pipeline created")
        
        # Filter rules
        logger.info("\n4. Filtering rules...")
        custom_rules = {k: v for k, v in rules.items() if v and v.strip()}
        logger.info(f"   ✓ Filtered to {len(custom_rules)} non-empty rules")
        logger.info(f"   Rules: {list(custom_rules.keys())}")
        
        # Merge rules
        logger.info("\n5. Merging custom rules...")
        pipeline.merge_custom_rules(custom_rules)
        logger.info(f"   ✓ Rules merged, {len(pipeline.rules_for_cleaning)} in rules_for_cleaning")
        
        # Perform cleansing
        logger.info("\n6. Performing cleansing (this is where transformation is applied)...")
        df_cleaned = pipeline.perform_cleansing(skip_llm_guidance=False, dedup_method='keep-first')
        
        if df_cleaned is not None:
            logger.info(f"\n7. Results:")
            logger.info(f"   ✓ Cleansed data returned: {len(df_cleaned)} rows")
            logger.info(f"   Phone column sample (after): {df_cleaned['Phone'].head(3).tolist()}")
            
            # Check if values changed
            changed = (df['Phone'] != df_cleaned['Phone']) & (df['Phone'].notna())
            logger.info(f"\n8. Validation:")
            logger.info(f"   Total phone values: {len(df)}")
            logger.info(f"   Values changed: {changed.sum()}")
            
            if changed.sum() > 0:
                logger.info(f"   ✓ TRANSFORMATION APPLIED!")
                # Show samples
                idx = changed[changed].index[0]
                logger.info(f"     Sample 1: '{df.loc[idx, 'Phone']}' → '{df_cleaned.loc[idx, 'Phone']}'")
                if changed.sum() > 1:
                    idx2 = changed[changed].index[1]
                    logger.info(f"     Sample 2: '{df.loc[idx2, 'Phone']}' → '{df_cleaned.loc[idx2, 'Phone']}'")
                return True
            else:
                logger.warning(f"   ❌ NO TRANSFORMATION APPLIED!")
                logger.warning(f"   Phone values are unchanged")
                return False
        else:
            logger.error(f"   ❌ perform_cleansing() returned None")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_cleansing()
    sys.exit(0 if success else 1)
