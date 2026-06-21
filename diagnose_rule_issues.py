"""
DIAGNOSIS: Why 15 Columns Have Rules But Are NOT Being Applied
"""

import pandas as pd
from agents.cleansing_rule_parser import CleansingRuleParser

print('\n' + '='*100)
print('🔍 DEEP DIVE: WHY RULES ARE NOT MODIFYING DATA IN 15 COLUMNS')
print('='*100)

# Load data and rules
data = pd.read_csv('data/Sample_Policy_Data.csv')
from data_io.db_helpers import read_guidewire_cleansing_rules

rules_raw = read_guidewire_cleansing_rules()

# Parse rules
parser = CleansingRuleParser()
rules_parsed = parser.parse_cleansing_rules(rules_raw)

# Columns with rules but NO changes
cols_with_no_changes = [
    'Address', 'Agent Commission %', 'Agent ID', 'GeoCode', 
    'Line of Business', 'National ID', 'Payment Plan', 'Policy Status', 
    'Policy Term Type', 'Premium Amount', 'Regulatory Reporting Flag', 
    'Renewal Indicator', 'Risk Object ID', 'Underwriter ID', 'VIN/Property ID'
]

print(f'\n🔴 PROBLEM COLUMNS (Rules defined but NO changes detected):')
print('-'*100)

for col in sorted(cols_with_no_changes):
    col_rules = rules_parsed[rules_parsed['cde'] == col]
    
    print(f'\n📌 {col}:')
    print(f'   Data type: {data[col].dtype}')
    print(f'   Null count: {data[col].isnull().sum()}/{len(data)}')
    print(f'   Sample values: {list(data[col].dropna().head(2).values)}')
    print(f'\n   Rules for this column ({len(col_rules)} rules):')
    
    for _, rule in col_rules.iterrows():
        action = rule['fix_action']
        params = rule.get('fix_parameters', 'N/A')
        print(f'     - {action} (params: {params})')
    
    print(f'\n   Analysis:')
    
    # Analyze each rule type
    if_null_rules = col_rules[col_rules['fix_action'] == 'if_null_fill']
    if len(if_null_rules) > 0:
        null_count = data[col].isnull().sum()
        print(f'     • if_null_fill: {null_count} nulls to fill')
        if null_count == 0:
            print(f'       ⚠️  NO NULLS in data → No action taken')
    
    flag_rules = col_rules[col_rules['fix_action'] == 'flag_for_review']
    if len(flag_rules) > 0:
        print(f'     • flag_for_review: Only adds flag columns, doesn\'t modify data values')
    
    validate_rules = col_rules[col_rules['fix_action'].isin(['validate_referential', 'validate_range'])]
    if len(validate_rules) > 0:
        print(f'     • validate_*: Only checks/logs, doesn\'t modify data')
    
    standardize_rules = col_rules[col_rules['fix_action'].isin(['standardize', 'numeric_standardize'])]
    if len(standardize_rules) > 0:
        print(f'     • standardize: Logic may not be activated (check implementation)')

print('\n' + '='*100)
print('ROOT CAUSE ANALYSIS')
print('='*100)

print('''
The issue is that several rule types are defined but DON'T MODIFY DATA:

1. ❌ flag_for_review
   - Creates NEW columns with flags (_REVIEW_FLAG_*)
   - Does NOT change the actual column values
   - Example: Phone column gets flagged but phone number unchanged
   
2. ❌ validate_referential
   - Only logs validation results
   - Does NOT change data
   - Placeholder for future HITL review
   
3. ❌ validate_range
   - Only logs out-of-range values
   - Does NOT change data
   - Placeholder for future HITL review

4. ✓ if_null_fill
   - WOULD modify data IF there were nulls
   - But most columns have NO nulls → No changes
   
5. ✓ standardize / numeric_standardize
   - Defined but has limited implementation
   - May not be triggered properly
   
6. ✓ parse_date
   - Works great! (All date columns standardized)
   - validate_email/validate_phone also working

SOLUTION NEEDED:
================================
For these 15 columns to be truly "cleaned", we need to:

1. For Status/Flag/Indicator columns:
   • Implement standardize() to convert to standard values
   • Example: 'active' → 'Active', 'Y' → 'N'
   
2. For ID columns:
   • Add format validation (length, pattern checks)
   • Trim whitespace, uppercase conversion
   
3. For Numeric columns:
   • Add rounding/precision standardization
   • Fix out-of-range values (currently only logged)
   
4. For Text columns:
   • Add trimming, proper casing
   • Remove special characters if needed

The flag_for_review is good for HITL workflows, but needs actual fix actions
to clean the data before/in parallel.
''')

print('\n' + '='*100)
