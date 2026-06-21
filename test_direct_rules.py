#!/usr/bin/env python
"""Test custom rule application"""
import pandas as pd
import json
from pathlib import Path
from agents.standardization_rules import CustomCleansingRuleParser, StandardizationRules

# Load original data
df_orig = pd.read_csv('data/Sample_Policy_Data.csv')
df_clean = df_orig.copy()

print("="*80)
print("TESTING CUSTOM RULE APPLICATION")
print("="*80)

# Load rules
with open('output/cleansing_rules.json', 'r') as f:
    rules = json.load(f)

print(f"\nLoaded {len(rules)} rules")
non_empty = {k: v for k, v in rules.items() if v and v.strip()}
print(f"Rules to apply: {len(non_empty)}")

for col, rule_text in non_empty.items():
    print(f"\nProcessing '{col}': {rule_text}")
    
    if col not in df_clean.columns:
        print(f"  ⚠️  Column not found")
        continue
    
    print(f"  Before: {df_clean[col].head(3).tolist()}")
    
    # Parse rule
    parsed_rule = CustomCleansingRuleParser.parse_custom_rule(rule_text)
    print(f"  Parsed operations: {parsed_rule['operations']}")
    
    # Apply rule directly via CustomCleansingRuleParser
    df_clean[col] = df_clean[col].apply(
        lambda x: CustomCleansingRuleParser.apply_custom_rule(x, parsed_rule)
    )
    
    # Apply fallback transformations
    sr = StandardizationRules()
    rule_lower = rule_text.lower()
    
    if 'date' in rule_lower:
        # Extract date format from rule
        date_format = '%Y-%m-%d'
        if 'yyyy/mm/dd' in rule_lower:
            date_format = '%Y/%m/%d'
        elif 'dd/mm/yyyy' in rule_lower:
            date_format = '%d/%m/%Y'
        
        df_clean[col] = df_clean[col].apply(
            lambda x: sr._parse_and_format_date(x, date_format) if pd.notna(x) else x
        )
        print(f"  Applied date formatting: {date_format}")
    
    print(f"  After: {df_clean[col].head(3).tolist()}")
    print(f"  ✓ Applied")

# Save cleaned data
output_file = 'output/Sample_Policy_Data_CLEANED_TEST.csv'
df_clean.to_csv(output_file, index=False)
print(f"\n✅ Cleaned data saved to {output_file}")

# Show comparison
print("\n" + "="*80)
print("COMPARISON")
print("="*80)
for col in non_empty.keys():
    if col in df_clean.columns:
        print(f"\n{col}:")
        print(f"  Original: {df_orig[col].head(3).tolist()}")
        print(f"  Cleaned:  {df_clean[col].head(3).tolist()}")
