#!/usr/bin/env python
"""Diagnose cleansing rules application issue"""
import json
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if cleansing_rules.json exists
rules_file = Path('output/cleansing_rules.json')
print(f"\n{'='*80}")
print(f"CLEANSING RULES DIAGNOSTIC")
print(f"{'='*80}\n")

if rules_file.exists():
    print(f"✓ Rules file found: {rules_file}")
    print(f"  File size: {rules_file.stat().st_size} bytes")
    print(f"  Last modified: {pd.Timestamp(rules_file.stat().st_mtime, unit='s')}")
    
    with open(rules_file, 'r') as f:
        rules = json.load(f)
    
    print(f"\n✓ Loaded {len(rules)} rules from JSON:")
    for col, rule in rules.items():
        if rule and rule.strip():
            print(f"  • {col}: '{rule}'")
    
    # Check if rules match actual data columns
    print(f"\n{'─'*80}")
    print(f"CHECKING COLUMN MAPPING")
    print(f"{'─'*80}\n")
    
    data_file = Path('data/Sample_Policy_Data.csv')
    if data_file.exists():
        df = pd.read_csv(data_file, nrows=1)
        actual_cols = set(df.columns)
        
        print(f"Actual data columns ({len(actual_cols)}):")
        for col in sorted(actual_cols):
            print(f"  • {col}")
        
        print(f"\nRule columns ({len(rules)}):")
        for col in rules.keys():
            print(f"  • {col}")
        
        print(f"\nMATCH ANALYSIS:")
        matched = 0
        unmatched = []
        for rule_col in rules.keys():
            if rule_col in actual_cols:
                matched += 1
                print(f"  ✓ {rule_col} - FOUND in data")
            else:
                unmatched.append(rule_col)
                print(f"  ✗ {rule_col} - NOT FOUND in data")
        
        print(f"\n  Summary: {matched}/{len(rules)} rules match data columns")
        
        if unmatched:
            print(f"\n  Unmatched rules (need mapping):")
            for col in unmatched:
                print(f"    • {col}")
    
    # Check the most recent cleaned output
    print(f"\n{'─'*80}")
    print(f"CHECKING RECENT CLEANED OUTPUT")
    print(f"{'─'*80}\n")
    
    cleaned_files = sorted(Path('output').glob('Sample_Policy_Data_CLEANED_*.csv'))
    if cleaned_files:
        latest = cleaned_files[-1]
        print(f"Latest cleaned file: {latest.name}")
        print(f"  Size: {latest.stat().st_size} bytes")
        print(f"  Modified: {pd.Timestamp(latest.stat().st_mtime, unit='s')}")
        
        # Read first few rows
        df_cleaned = pd.read_csv(latest, nrows=3)
        print(f"\n  Sample data (first 3 rows):")
        print(f"    policy_number samples:")
        if 'policy_number' in df_cleaned.columns:
            for val in df_cleaned['policy_number'].head():
                print(f"      • {val}")
        
        # Compare with original
        df_original = pd.read_csv(data_file, nrows=3)
        if 'policy_number' in df_original.columns and 'policy_number' in df_cleaned.columns:
            print(f"\n  COMPARISON:")
            print(f"    Original[0]: {df_original['policy_number'].iloc[0]}")
            print(f"    Cleaned[0]:  {df_cleaned['policy_number'].iloc[0]}")
            if df_original['policy_number'].iloc[0] != df_cleaned['policy_number'].iloc[0]:
                print(f"    Status: ✓ TRANSFORMED")
            else:
                print(f"    Status: ✗ NOT TRANSFORMED")

else:
    print(f"✗ Rules file NOT found: {rules_file}")
    print(f"  This means no custom rules were saved from the dashboard")

print(f"\n{'='*80}\n")
