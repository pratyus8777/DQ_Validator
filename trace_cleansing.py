#!/usr/bin/env python
"""Trace through cleansing to find where rules are lost"""

import pandas as pd
from assessment_first_pipeline import DQAssessmentFirst
import logging

# Set up logging to see everything
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

print("=" * 70)
print("TRACING RULE APPLICATION")
print("=" * 70)

# Create pipeline
pipeline = DQAssessmentFirst()
pipeline.fast_mode = True
pipeline.load_data()

print("\n1. Loading rules...")
pipeline.load_and_interpret_rules(rules_source=None)
print("   Loaded {} rules".format(len(pipeline.rules_for_cleaning)))

# Show which rules loaded
print("\n   Rules loaded for columns:")
for col in list(pipeline.rules_for_cleaning.keys())[:5]:
    rule = pipeline.rules_for_cleaning[col]
    rule_text = rule if isinstance(rule, str) else rule.get('user_rule', '')
    print("   - {}: {}...".format(col, rule_text[:50]))

# Check if rules match actual columns
print("\n2. Checking column matching...")
data_cols = set(pipeline.df_original.columns)
rule_cols = set(pipeline.rules_for_cleaning.keys())
matched = rule_cols & data_cols
missing = rule_cols - data_cols

print("   Data has {} columns".format(len(data_cols)))
print("   Rules have {} columns".format(len(rule_cols)))
print("   Matched: {}".format(len(matched)))
print("   Missing in data: {} (should be 0)".format(len(missing)))
if missing:
    print("   Missing columns:", missing)

# Check transformation creation
print("\n3. Creating transformations for first 3 rules...")
for col, rule_text in list(pipeline.rules_for_cleaning.items())[:3]:
    if col not in pipeline.df_original.columns:
        print("   - SKIP {}: not in data".format(col))
        continue
    
    trans = pipeline._get_heuristic_transformation(col, rule_text if isinstance(rule_text, str) else rule_text.get('user_rule', ''))
    if trans is None:
        print("   - FAIL {}: no transformation created".format(col))
    else:
        print("   - OK {}: transformation created".format(col))
        # Test it
        test_val = pipeline.df_original[col].dropna().iloc[0] if len(pipeline.df_original[col].dropna()) > 0 else "test"
        try:
            result = trans(test_val)
            print("      Sample: '{}' -> '{}'".format(test_val, result))
        except Exception as e:
            print("      ERROR applying: {}".format(e))

print("\n4. Attempting cleansing (with debug)...")
df_clean = pipeline.perform_cleansing()

if df_clean is not None:
    print("\n5. Checking results...")
    # Check if any data changed
    orig = pipeline.df_original
    changed_cols = []
    for col in orig.columns:
        if col in df_clean.columns:
            if not orig[col].equals(df_clean[col]):
                changed_cols.append(col)
    
    print("   Columns with changes: {}".format(len(changed_cols)))
    if changed_cols:
        print("   Changed columns: {}".format(changed_cols[:5]))
    else:
        print("   ERROR: NO COLUMNS CHANGED!")
else:
    print("\n5. Cleansing failed!")

print("\n" + "=" * 70)
