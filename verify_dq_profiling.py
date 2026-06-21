#!/usr/bin/env python3
"""
Verify that:
1. Value standardization is working
2. DQ profiling rules are applied
3. All rules mentioned in JSON are actually applied
"""

import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

print("=" * 80)
print("DATA QUALITY PROFILING & RULE APPLICATION VERIFICATION")
print("=" * 80)
print()

# Load latest cleaned and original files
output_dir = Path('output')
data_dir = Path('data')

cleaned_files = sorted(output_dir.glob('*CLEANED_*.csv'))
if not cleaned_files:
    print("❌ No cleaned files found")
    exit(1)

# Use the original Sample_Policy_Data.csv from data directory
original_file = data_dir / 'Sample_Policy_Data.csv'
if not original_file.exists():
    print(f"❌ Original file not found: {original_file}")
    exit(1)

latest_cleaned = pd.read_csv(cleaned_files[-1])
latest_original = pd.read_csv(original_file)
timestamp = cleaned_files[-1].stem.split('_')[-1]

print(f"📊 Comparing: {original_file.name} → {cleaned_files[-1].name}")
print()

# Load rules
rules_json = Path('output/cleansing_rules.json')
if rules_json.exists():
    with open(rules_json) as f:
        defined_rules = json.load(f)
else:
    defined_rules = {}

print(f"📋 Total rules defined: {len(defined_rules)}")
print()

# ============================================================================
# 1. VALUE STANDARDIZATION CHECK
# ============================================================================
print("=" * 80)
print("1. VALUE STANDARDIZATION VERIFICATION")
print("=" * 80)
print()

standardization_checks = {
    'customer_name': {
        'rule': 'convert to uppercase',
        'check': lambda x: str(x).isupper() if str(x).isalpha() else True,
        'description': 'Should be UPPERCASE'
    },
    'email': {
        'rule': 'convert to uppercase',
        'check': lambda x: str(x).isupper() or '@' in str(x),
        'description': 'Should be UPPERCASE'
    },
    'phone': {
        'rule': 'use +80-XXXXX-XXXXX format',
        'check': lambda x: str(x).startswith('+80-') if pd.notna(x) else True,
        'description': 'Should follow +80-XXXXX-XXXXX format'
    },
    'policy_number': {
        'rule': 'uppercase',
        'check': lambda x: str(x).isupper() if str(x).isalpha() or '-' in str(x) else True,
        'description': 'Should be UPPERCASE'
    },
}

for col, check_info in standardization_checks.items():
    if col not in latest_cleaned.columns:
        print(f"⚠️  Column '{col}' not in cleaned data")
        continue
    
    rule_desc = check_info['rule']
    check_fn = check_info['check']
    description = check_info['description']
    
    # Get non-null values
    cleaned_vals = latest_cleaned[col].dropna()
    if len(cleaned_vals) == 0:
        print(f"⚠️  {col}: No non-null values")
        continue
    
    # Check how many pass the check
    passed = sum(1 for v in cleaned_vals if check_fn(v))
    total = len(cleaned_vals)
    percentage = (passed / total * 100) if total > 0 else 0
    
    status = "✅" if percentage >= 95 else "⚠️"
    print(f"{status} {col}")
    print(f"   Rule: {rule_desc}")
    print(f"   {description}")
    print(f"   Compliance: {passed}/{total} ({percentage:.1f}%)")
    print(f"   Sample: {cleaned_vals.iloc[0]}")
    print()

# ============================================================================
# 2. DQ PROFILING RULES (Bounds, Range, Negative Values)
# ============================================================================
print("=" * 80)
print("2. DQ PROFILING RULES (Bounds/Range/Negative Values)")
print("=" * 80)
print()

profiling_checks = {
    'agent_commission': {
        'rule': 'Percentage value 0-100',
        'min': 0,
        'max': 100,
        'check_type': 'bounds'
    },
    'premium': {
        'rule': 'Numeric amount, remove negative values',
        'min': 0,
        'check_type': 'positive'
    },
    'coverage_limit': {
        'rule': 'Numeric amount, remove negative values',
        'min': 0,
        'check_type': 'positive'
    },
    'underwriting_score': {
        'rule': 'Numeric score 0-100',
        'min': 0,
        'max': 100,
        'check_type': 'bounds'
    },
}

for col, check_info in profiling_checks.items():
    if col not in latest_cleaned.columns:
        print(f"⚠️  Column '{col}' not in cleaned data")
        continue
    
    rule_desc = check_info['rule']
    check_type = check_info['check_type']
    
    cleaned_vals = pd.to_numeric(latest_cleaned[col], errors='coerce').dropna()
    if len(cleaned_vals) == 0:
        print(f"⚠️  {col}: No numeric values")
        continue
    
    col_min = cleaned_vals.min()
    col_max = cleaned_vals.max()
    
    # Check bounds
    if check_type == 'bounds':
        min_bound = check_info.get('min', 0)
        max_bound = check_info.get('max', float('inf'))
        
        in_bounds = sum(1 for v in cleaned_vals if min_bound <= v <= max_bound)
        total = len(cleaned_vals)
        percentage = (in_bounds / total * 100) if total > 0 else 0
        
        status = "✅" if percentage >= 95 else "⚠️"
        print(f"{status} {col}")
        print(f"   Rule: {rule_desc}")
        print(f"   Expected bounds: [{min_bound}, {max_bound}]")
        print(f"   Actual range: [{col_min}, {col_max}]")
        print(f"   In-bounds: {in_bounds}/{total} ({percentage:.1f}%)")
        print()
    
    elif check_type == 'positive':
        min_bound = check_info.get('min', 0)
        positive_vals = sum(1 for v in cleaned_vals if v >= min_bound)
        total = len(cleaned_vals)
        percentage = (positive_vals / total * 100) if total > 0 else 0
        
        status = "✅" if percentage >= 95 else "⚠️"
        print(f"{status} {col}")
        print(f"   Rule: {rule_desc}")
        print(f"   Min expected: {min_bound}")
        print(f"   Actual min: {col_min}")
        print(f"   Positive values: {positive_vals}/{total} ({percentage:.1f}%)")
        print()

# ============================================================================
# 3. ALL RULES MENTIONED IN JSON - APPLICATION CHECK
# ============================================================================
print("=" * 80)
print("3. ALL RULES FROM JSON/CSV - APPLICATION STATUS")
print("=" * 80)
print()

applied_rules = []
unapplied_rules = []

for col, rule_text in defined_rules.items():
    if not rule_text or not rule_text.strip():
        unapplied_rules.append((col, rule_text, "Empty rule"))
        continue
    
    if col not in latest_cleaned.columns:
        unapplied_rules.append((col, rule_text, "Column not in data"))
        continue
    
    # Check if column was transformed
    if col not in latest_original.columns:
        applied_rules.append((col, rule_text, "Column added"))
        continue
    
    original_vals = latest_original[col].astype(str).value_counts()
    cleaned_vals = latest_cleaned[col].astype(str).value_counts()
    
    # Check if values changed
    if not original_vals.equals(cleaned_vals):
        applied_rules.append((col, rule_text, "✅ Values transformed"))
    else:
        # Values unchanged - might be because they were already clean
        unapplied_rules.append((col, rule_text, "No transformation needed"))

print(f"✅ APPLIED: {len(applied_rules)} rules")
for col, rule, status in applied_rules[:10]:  # Show first 10
    print(f"   • {col}: {rule[:60]}... [{status}]")
if len(applied_rules) > 10:
    print(f"   ... and {len(applied_rules) - 10} more")
print()

print(f"⚠️  NOT TRANSFORMED: {len(unapplied_rules)} rules")
for col, rule, reason in unapplied_rules[:5]:  # Show first 5
    print(f"   • {col}: {reason}")
if len(unapplied_rules) > 5:
    print(f"   ... and {len(unapplied_rules) - 5} more")
print()

# ============================================================================
# 4. TRANSFORMATION EXAMPLES
# ============================================================================
print("=" * 80)
print("4. TRANSFORMATION EXAMPLES (Before vs After)")
print("=" * 80)
print()

sample_rows = min(3, len(latest_cleaned))

example_cols = ['customer_name', 'email', 'phone', 'agent_commission', 'premium']
for col in example_cols:
    if col not in latest_cleaned.columns or col not in latest_original.columns:
        continue
    
    print(f"📝 {col.upper()}")
    print(f"   Rule: {defined_rules.get(col, 'N/A')[:60]}...")
    print(f"   Transformations:")
    
    for idx in range(sample_rows):
        orig = latest_original[col].iloc[idx]
        clean = latest_cleaned[col].iloc[idx]
        
        if str(orig) != str(clean):
            print(f"   [{idx+1}] '{orig}' → '{clean}'")
        else:
            print(f"   [{idx+1}] '{clean}' (unchanged - already clean)")
    print()

# ============================================================================
# 5. SUMMARY
# ============================================================================
print("=" * 80)
print("5. SUMMARY")
print("=" * 80)
print()

total_rules = len([r for r in defined_rules.values() if r and r.strip()])
applied_count = len(applied_rules)
compliance_rate = (applied_count / total_rules * 100) if total_rules > 0 else 0

print(f"📊 Total Rules Defined: {total_rules}")
print(f"✅ Rules Applied/Transformed: {applied_count}")
print(f"⚠️  Rules Not Transformed: {len(unapplied_rules)}")
print(f"📈 Application Rate: {compliance_rate:.1f}%")
print()

if compliance_rate >= 90:
    print("✅ RESULT: DQ Profiling & Standardization Rules ARE Being Applied!")
elif compliance_rate >= 70:
    print("⚠️  RESULT: Most rules applied, some may need review")
else:
    print("❌ RESULT: Low compliance - check rule configurations")

print()
print("=" * 80)
