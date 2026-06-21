"""
COMPREHENSIVE RULES IMPLEMENTATION CHECK
Verifies that ALL columns have rules applied, not just dates
"""

import pandas as pd
import logging
from agents.cleansing_rule_parser import CleansingRuleParser
from rules_engine.dispatcher import run_fix

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

print('\n' + '='*100)
print('📊 COMPLETE RULES IMPLEMENTATION ANALYSIS')
print('='*100)

# Load data and rules
try:
    data = pd.read_csv('data/Sample_Policy_Data.csv')
    from data_io.db_helpers import read_guidewire_cleansing_rules
    rules_raw = read_guidewire_cleansing_rules()
    print(f'\n✓ Loaded {len(data)} records × {len(data.columns)} columns')
    print(f'✓ Loaded {len(rules_raw)} cleansing rules')
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)

# Parse rules
parser = CleansingRuleParser()
rules_parsed = parser.parse_cleansing_rules(rules_raw)

print(f'✓ Parsed {len(rules_parsed)} actionable rules')
print(f'\nRule action distribution:')
for action in rules_parsed['fix_action'].unique():
    count = len(rules_parsed[rules_parsed['fix_action'] == action])
    print(f'  - {action}: {count} rules')

# ============================================================
# PHASE 1: Check which columns have rules
# ============================================================
print('\n' + '-'*100)
print('PHASE 1: RULE COVERAGE BY COLUMN')
print('-'*100)

columns_in_data = set(data.columns)
columns_with_rules = set(rules_parsed['cde'].unique())
columns_without_rules = columns_in_data - columns_with_rules

print(f'\n📋 Column Coverage:')
print(f'  Total columns in data: {len(columns_in_data)}')
print(f'  Columns with rules: {len(columns_with_rules)}')
print(f'  Columns WITHOUT rules: {len(columns_without_rules)}')

if columns_without_rules:
    print(f'\n⚠️  COLUMNS WITHOUT ANY RULES:')
    for col in sorted(columns_without_rules):
        print(f'    - {col}')

# ============================================================
# PHASE 2: Analyze rule types by column category
# ============================================================
print('\n' + '-'*100)
print('PHASE 2: RULE TYPES BY COLUMN CATEGORY')
print('-'*100)

date_cols = [c for c in columns_in_data if any(d in c.lower() for d in ['date', 'effective', 'expiry', 'dob', 'incorporation'])]
numeric_cols = [c for c in columns_in_data if any(n in c.lower() for n in ['amount', 'limit', 'deductible', 'premium', 'commission', '%'])]
contact_cols = [c for c in columns_in_data if c.lower() in ['phone', 'email', 'contact email', 'contact phone']]
id_cols = [c for c in columns_in_data if 'id' in c.lower()]
status_cols = [c for c in columns_in_data if any(s in c.lower() for s in ['status', 'indicator', 'flag'])]
text_cols = [c for c in columns_in_data if c not in date_cols + numeric_cols + contact_cols + id_cols + status_cols]

def show_rules_for_columns(col_list, category_name):
    print(f'\n🏷️  {category_name} ({len(col_list)} columns):')
    for col in sorted(col_list):
        col_rules = rules_parsed[rules_parsed['cde'] == col]
        if len(col_rules) > 0:
            actions = ', '.join(col_rules['fix_action'].unique())
            print(f'    ✓ {col}: {actions}')
        else:
            print(f'    ✗ {col}: NO RULES')

show_rules_for_columns(date_cols, '📅 DATE COLUMNS')
show_rules_for_columns(numeric_cols, '🔢 NUMERIC COLUMNS')
show_rules_for_columns(contact_cols, '📧 CONTACT COLUMNS')
show_rules_for_columns(id_cols, '🏷️  ID COLUMNS')
show_rules_for_columns(status_cols, '📌 STATUS/FLAG COLUMNS')
show_rules_for_columns(text_cols, '📝 TEXT COLUMNS')

# ============================================================
# PHASE 3: Apply ALL rules and measure impact
# ============================================================
print('\n' + '-'*100)
print('PHASE 3: TESTING RULE APPLICATION - ACTUAL IMPACT')
print('-'*100)

data_before = data.copy()
data_after = data.copy()

# Sort rules by priority and apply
rules_sorted = rules_parsed.sort_values('priority', ascending=True)
applied_count = 0
skipped_count = 0

for _, rule in rules_sorted.iterrows():
    try:
        rule_dict = rule.to_dict()
        data_after = run_fix(data_after, rule_dict)
        applied_count += 1
    except Exception as e:
        logger.warning(f"Failed to apply rule for {rule['cde']}: {e}")
        skipped_count += 1

print(f'\n✓ Applied {applied_count} rules')
if skipped_count > 0:
    print(f'⚠️  Skipped {skipped_count} rules (errors)')

# ============================================================
# PHASE 4: Compare before/after and show changes by column
# ============================================================
print('\n' + '-'*100)
print('PHASE 4: CHANGES BY COLUMN')
print('-'*100)

changes_by_col = {}
for col in data.columns:
    if col not in data_after.columns:
        continue
    
    # Count value changes
    before_str = data_before[col].astype(str)
    after_str = data_after[col].astype(str)
    value_changes = (before_str != after_str).sum()
    
    # Count null reductions
    before_nulls = data_before[col].isnull().sum()
    after_nulls = data_after[col].isnull().sum()
    null_reduction = before_nulls - after_nulls
    
    if value_changes > 0 or null_reduction > 0:
        changes_by_col[col] = {
            'value_changes': value_changes,
            'null_reduction': null_reduction,
            'total_impact': value_changes + null_reduction,
            'before_nulls': before_nulls,
            'after_nulls': after_nulls
        }

# Display by category
print(f'\n🔍 CHANGES DETECTED:')
print(f'  Total columns affected: {len(changes_by_col)}/{len(data.columns)}')
print(f'  Coverage: {100*len(changes_by_col)/len(data.columns):.1f}%')

print(f'\n📅 DATE COLUMNS CHANGES:')
has_date_changes = False
for col in sorted(date_cols):
    if col in changes_by_col:
        c = changes_by_col[col]
        print(f'  ✓ {col}:')
        print(f'      {c["value_changes"]} value changes, {c["null_reduction"]} nulls filled → Total: {c["total_impact"]} records')
        has_date_changes = True
if not has_date_changes:
    print(f'  ✗ NO CHANGES IN DATE COLUMNS (unexpected!)')

print(f'\n🔢 NUMERIC COLUMNS CHANGES:')
has_numeric_changes = False
for col in sorted(numeric_cols):
    if col in changes_by_col:
        c = changes_by_col[col]
        print(f'  ✓ {col}:')
        print(f'      {c["value_changes"]} value changes, {c["null_reduction"]} nulls filled → Total: {c["total_impact"]} records')
        has_numeric_changes = True
if not has_numeric_changes:
    print(f'  ✗ NO CHANGES IN NUMERIC COLUMNS')

print(f'\n📧 CONTACT COLUMNS CHANGES:')
has_contact_changes = False
for col in sorted(contact_cols):
    if col in changes_by_col:
        c = changes_by_col[col]
        print(f'  ✓ {col}:')
        print(f'      {c["value_changes"]} value changes, {c["null_reduction"]} nulls filled → Total: {c["total_impact"]} records')
        has_contact_changes = True
if not has_contact_changes:
    print(f'  ✗ NO CHANGES IN CONTACT COLUMNS')

print(f'\n🏷️  ID COLUMNS CHANGES:')
has_id_changes = False
for col in sorted(id_cols):
    if col in changes_by_col:
        c = changes_by_col[col]
        print(f'  ✓ {col}:')
        print(f'      {c["value_changes"]} value changes, {c["null_reduction"]} nulls filled → Total: {c["total_impact"]} records')
        has_id_changes = True
if not has_id_changes:
    print(f'  ✗ NO CHANGES IN ID COLUMNS')

print(f'\n📌 STATUS/FLAG COLUMNS CHANGES:')
has_status_changes = False
for col in sorted(status_cols):
    if col in changes_by_col:
        c = changes_by_col[col]
        print(f'  ✓ {col}:')
        print(f'      {c["value_changes"]} value changes, {c["null_reduction"]} nulls filled → Total: {c["total_impact"]} records')
        has_status_changes = True
if not has_status_changes:
    print(f'  ✗ NO CHANGES IN STATUS/FLAG COLUMNS')

print(f'\n📝 TEXT COLUMNS CHANGES:')
has_text_changes = False
for col in sorted(text_cols):
    if col in changes_by_col:
        c = changes_by_col[col]
        print(f'  ✓ {col}:')
        print(f'      {c["value_changes"]} value changes, {c["null_reduction"]} nulls filled → Total: {c["total_impact"]} records')
        has_text_changes = True
if not has_text_changes:
    print(f'  ✗ NO CHANGES IN TEXT COLUMNS')

# ============================================================
# PHASE 5: SUMMARY
# ============================================================
print('\n' + '='*100)
print('📋 FINAL SUMMARY')
print('='*100)

total_changes = sum(c['total_impact'] for c in changes_by_col.values())
total_value_changes = sum(c['value_changes'] for c in changes_by_col.values())
total_nulls_filled = sum(c['null_reduction'] for c in changes_by_col.values())
total_cells = len(data) * len(data.columns)

print(f'\n📊 STATISTICS:')
print(f'  Data shape: {len(data)} records × {len(data.columns)} columns = {total_cells} cells')
print(f'  Columns with rules: {len(columns_with_rules)}/{len(columns_in_data)} ({100*len(columns_with_rules)/len(columns_in_data):.1f}%)')
print(f'  Columns affected by changes: {len(changes_by_col)}/{len(columns_in_data)} ({100*len(changes_by_col)/len(columns_in_data):.1f}%)')
print(f'\n  Value changes applied: {total_value_changes} cells')
print(f'  Nulls filled: {total_nulls_filled} cells')
print(f'  Total improvements: {total_changes} cells ({100*total_changes/total_cells:.2f}% of all cells)')

print(f'\n🎯 RULES IMPLEMENTATION STATUS:')
if len(columns_without_rules) > 0:
    print(f'  ⚠️  {len(columns_without_rules)} columns have NO RULES defined')
if len(changes_by_col) == len(columns_with_rules):
    print(f'  ✓ All columns with rules are being modified')
elif len(changes_by_col) < len(columns_with_rules):
    cols_no_changes = columns_with_rules - set(changes_by_col.keys())
    print(f'  ⚠️  {len(cols_no_changes)} columns have rules but NO CHANGES: {sorted(cols_no_changes)}')
else:
    print(f'  ✓ More columns changed than have explicit rules (good!)')

print('\n' + '='*100 + '\n')

# Save results
output_file = 'output/rules_implementation_report.txt'
with open(output_file, 'w') as f:
    f.write('RULES IMPLEMENTATION REPORT\n')
    f.write('='*100 + '\n\n')
    f.write(f'SUMMARY:\n')
    f.write(f'  Total rules parsed: {len(rules_parsed)}\n')
    f.write(f'  Columns with rules: {len(columns_with_rules)}/{len(columns_in_data)}\n')
    f.write(f'  Columns affected: {len(changes_by_col)}/{len(columns_in_data)}\n')
    f.write(f'  Value changes: {total_value_changes}\n')
    f.write(f'  Nulls filled: {total_nulls_filled}\n')
    f.write(f'  Coverage: {100*total_changes/total_cells:.2f}%\n')
    f.write(f'\nCOLUMNS WITHOUT RULES:\n')
    for col in sorted(columns_without_rules):
        f.write(f'  - {col}\n')
    f.write(f'\nCOLUMNS WITH RULES BUT NO CHANGES:\n')
    for col in sorted(columns_with_rules - set(changes_by_col.keys())):
        f.write(f'  - {col}\n')
    f.write(f'\nCOLUMNS WITH CHANGES:\n')
    for col in sorted(changes_by_col.keys()):
        c = changes_by_col[col]
        f.write(f'  - {col}: {c["total_impact"]} records affected\n')

print(f'✓ Report saved to {output_file}')
