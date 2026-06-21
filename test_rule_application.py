#!/usr/bin/env python
"""Quick test of rule application"""
import pandas as pd
import json
from agents.standardization_rules import CustomCleansingRuleParser

# Create test data
test_data = {
    'Customer Name': ['john doe', 'JANE SMITH', 'bOb jOnes'],
    'Email': ['JOHN@EXAMPLE.COM', 'jane@example.com', 'BOB@TEST.COM'],
    'Phone': ['5551234567', '(555) 234-5678', '5559999888'],
    'Policy Number': ['pol-001', 'POL-002', 'pol-003']
}

df = pd.DataFrame(test_data)
print("Original Data:")
print(df)
print("\n" + "="*80 + "\n")

# Load rules
with open('output/cleansing_rules.json', 'r') as f:
    rules = json.load(f)

# Apply each rule
df_clean = df.copy()
for column, rule_text in rules.items():
    if column not in df_clean.columns:
        print(f"⚠️  Column '{column}' not found in data")
        continue
    
    print(f"Processing column '{column}': {rule_text}")
    parsed_rule = CustomCleansingRuleParser.parse_custom_rule(rule_text)
    print(f"  Parsed operations: {parsed_rule['operations']}")
    
    # Apply rule
    df_clean[column] = df_clean[column].apply(
        lambda x: CustomCleansingRuleParser.apply_custom_rule(x, parsed_rule)
    )
    print(f"  ✓ Applied {len(parsed_rule.get('operations', []))} operations to {column}")

print("\n" + "="*80 + "\n")
print("Cleaned Data:")
print(df_clean)
print("\nChanges applied successfully!")
