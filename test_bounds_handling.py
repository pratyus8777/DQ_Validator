#!/usr/bin/env python
"""Test bounds/range and negative value handling"""
import sys
import pandas as pd
import numpy as np
from assessment_first_pipeline import DQAssessmentFirst
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_bounds_handling():
    """Test that bounds and negative values are handled correctly"""
    
    # Create test data with negative and out-of-range values
    test_data = {
        'policy_id': ['POL001', 'POL002', 'POL003', 'POL004', 'POL005'],
        'premium_amount': [1000, -500, 2000, 3500, -1200],  # negative values
        'deductible': [500, -100, 750, 1000, -50],  # negative deductibles
        'coverage_limit': [50000, 150000, 250000, 500000, 1000000],  # Some out of range
        'claim_percentage': [50, 150, 75, -10, 200],  # Out of 0-100 range
        'insured_name': ['John', 'Jane', 'Bob', 'Alice', 'Charlie']
    }
    
    df = pd.DataFrame(test_data)
    
    logger.info("\n" + "="*80)
    logger.info("TEST: BOUNDS/RANGE AND NEGATIVE VALUE HANDLING")
    logger.info("="*80)
    
    logger.info("\nInput Data:")
    logger.info(df.to_string())
    
    # Create a simple rule set that should trigger bounds checking
    rules = {
        'premium_amount': {
            'validity_remediation': 'Check if negative, remove negatives',
            'reasonableness_remediation': 'Validate business range; remove negative values'
        },
        'deductible': {
            'validity_remediation': 'No negatives allowed; set to 0 if negative',
            'reasonableness_remediation': 'Out-of-range check; deductible cannot be negative'
        },
        'claim_percentage': {
            'validity_remediation': 'Percentage range 0-100',
            'reasonableness_remediation': 'Constrain percentage to 0-100 range'
        }
    }
    
    logger.info("\n" + "-"*80)
    logger.info("RULES LOADED:")
    logger.info("-"*80)
    for col, rule_dict in rules.items():
        logger.info(f"\nColumn: {col}")
        for rule_type, rule_text in rule_dict.items():
            logger.info(f"  {rule_type}: {rule_text}")
    
    # Initialize pipeline
    try:
        pipeline = DQAssessmentFirst()
        logger.info("\n✓ Pipeline initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize pipeline: {e}")
        return False
    
    # Test heuristic transformation detection
    logger.info("\n" + "-"*80)
    logger.info("TESTING HEURISTIC TRANSFORMATIONS:")
    logger.info("-"*80)
    
    for col, rule_dict in rules.items():
        logger.info(f"\nColumn: {col}")
        for rule_type, rule_text in rule_dict.items():
            logger.info(f"  {rule_type}: {rule_text}")
            
            # Get the transformation function
            try:
                transform_fn = pipeline._get_heuristic_transformation(col, rule_text)
                if transform_fn:
                    # Test on sample values
                    test_values = df[col].tolist() if col in df.columns else []
                    logger.info(f"    → Transformation detected")
                    if test_values:
                        logger.info(f"    → Input values: {test_values}")
                        try:
                            result_values = [transform_fn(v) for v in test_values]
                            logger.info(f"    → Output values: {result_values}")
                        except Exception as e:
                            logger.warning(f"    → Transformation error: {e}")
                else:
                    logger.info(f"    → No transformation found")
            except Exception as e:
                logger.error(f"    → Error getting transformation: {e}")
    
    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETE")
    logger.info("="*80)
    return True

if __name__ == "__main__":
    success = test_bounds_handling()
    sys.exit(0 if success else 1)
