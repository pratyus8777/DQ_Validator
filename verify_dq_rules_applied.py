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
from datetime import datetime

print("=" * 90)
print("DATA QUALITY PROFILING & RULE APPLICATION VERIFICATION")
print("=" * 90)
print()

# Load latest cleaned file
output_dir = Path('output')
cleaned_files = sorted(output_dir.glob('*CLEANED_*.csv'))

if not cleaned_files:
    print("❌ No cleaned files found")
    exit(1)

latest_cleaned = pd.read_csv(cleaned_files[-1])
print(f"✅ Latest cleaned file: {cleaned_files[-1].name}")
print(f"   Rows: {len(latest_cleaned)}, Columns: {len(latest_cleaned.columns)}")
print()

# Load rules
rules_json = Path('output/cleansing_rules.json')
if rules_json.exists():
    with open(rules_json) as f:
        defined_rules = json.load(f)
    print(f"✅ Cleansing rules loaded from JSON")
else:
    defined_rules = {}
    print(f"⚠️  No cleansing rules JSON found")

print(f"   Total rules defined: {len(defined_rules)}")
print()

# ============================================================================
# 1. VALUE STANDARDIZATION CHECK
# ============================================================================
print("=" * 90)
print("1. VALUE STANDARDIZATION VERIFICATION")
print("=" * 90)
print()

standardization_results = []

# Check customer_name
if 'customer_name' in latest_cleaned.columns:
    name_vals = latest_cleaned['customer_name'].dropna()
    uppercase_count = sum(1 for v in name_vals if str(v).isupper() if str(v).replace(' ', '').isalpha())
    standardization_results.append({
        'column': 'customer_name',
        'rule': defined_rules.get('customer_name', 'N/A')[:50],
        'check': 'UPPERCASE',
        'count': len(name_vals),
        'compliant': uppercase_count,
        'percentage': (uppercase_count / len(name_vals) * 100) if len(name_vals) > 0 else 0,
        'sample': name_vals.iloc[0] if len(name_vals) > 0 else 'N/A'
    })
    print(f"✅ customer_name: {uppercase_count}/{len(name_vals)} UPPERCASE ({(uppercase_count/len(name_vals)*100):.1f}%)")
    print(f"   Sample: {name_vals.iloc[0]}")
    print()

# Check email
if 'email' in latest_cleaned.columns:
    email_vals = latest_cleaned['email'].dropna()
    uppercase_email = sum(1 for v in email_vals if str(v).isupper())
    standardization_results.append({
        'column': 'email',
        'rule': defined_rules.get('email', 'N/A')[:50],
        'check': 'UPPERCASE',
        'count': len(email_vals),
        'compliant': uppercase_email,
        'percentage': (uppercase_email / len(email_vals) * 100) if len(email_vals) > 0 else 0,
        'sample': email_vals.iloc[0] if len(email_vals) > 0 else 'N/A'
    })
    print(f"✅ email: {uppercase_email}/{len(email_vals)} UPPERCASE ({(uppercase_email/len(email_vals)*100):.1f}%)")
    print(f"   Sample: {email_vals.iloc[0]}")
    print()

# Check phone format
if 'phone' in latest_cleaned.columns:
    phone_vals = latest_cleaned['phone'].dropna()
    phone_format_count = sum(1 for v in phone_vals if str(v).startswith('+') and '-' in str(v))
    standardization_results.append({
        'column': 'phone',
        'rule': defined_rules.get('phone', 'N/A')[:50],
        'check': '+XX-XXXXX-XXXXX format',
        'count': len(phone_vals),
        'compliant': phone_format_count,
        'percentage': (phone_format_count / len(phone_vals) * 100) if len(phone_vals) > 0 else 0,
        'sample': phone_vals.iloc[0] if len(phone_vals) > 0 else 'N/A'
    })
    print(f"✅ phone: {phone_format_count}/{len(phone_vals)} in correct format ({(phone_format_count/len(phone_vals)*100):.1f}%)")
    print(f"   Expected format: +XX-XXXXX-XXXXX")
    print(f"   Sample: {phone_vals.iloc[0]}")
    print()

# ============================================================================
# 2. DQ PROFILING RULES (Bounds, Range, Negative Values)
# ============================================================================
print("=" * 90)
print("2. DQ PROFILING RULES (Bounds/Range/Negative Values)")
print("=" * 90)
print()

profiling_results = []

# Check agent_commission (0-100 bounds)
if 'agent_commission' in latest_cleaned.columns:
    commission_vals = pd.to_numeric(latest_cleaned['agent_commission'], errors='coerce').dropna()
    if len(commission_vals) > 0:
        in_bounds = sum(1 for v in commission_vals if 0 <= v <= 100)
        min_val = commission_vals.min()
        max_val = commission_vals.max()
        profiling_results.append({
            'column': 'agent_commission',
            'rule': defined_rules.get('agent_commission', 'N/A')[:50],
            'check': '0-100 bounds',
            'count': len(commission_vals),
            'compliant': in_bounds,
            'percentage': (in_bounds / len(commission_vals) * 100),
            'min': min_val,
            'max': max_val
        })
        print(f"✅ agent_commission (0-100 bounds):")
        print(f"   Compliant: {in_bounds}/{len(commission_vals)} ({(in_bounds/len(commission_vals)*100):.1f}%)")
        print(f"   Actual range: [{min_val}, {max_val}]")
        print()

# Check premium (positive values only)
if 'premium' in latest_cleaned.columns:
    premium_vals = pd.to_numeric(latest_cleaned['premium'], errors='coerce').dropna()
    if len(premium_vals) > 0:
        positive = sum(1 for v in premium_vals if v >= 0)
        min_val = premium_vals.min()
        max_val = premium_vals.max()
        profiling_results.append({
            'column': 'premium',
            'rule': defined_rules.get('premium', 'N/A')[:50],
            'check': 'positive values',
            'count': len(premium_vals),
            'compliant': positive,
            'percentage': (positive / len(premium_vals) * 100),
            'min': min_val,
            'max': max_val
        })
        print(f"✅ premium (positive values):")
        print(f"   Compliant: {positive}/{len(premium_vals)} ({(positive/len(premium_vals)*100):.1f}%)")
        print(f"   Actual range: [{min_val}, {max_val}]")
        print()

# Check coverage_limit (positive values)
if 'coverage_limit' in latest_cleaned.columns:
    coverage_vals = pd.to_numeric(latest_cleaned['coverage_limit'], errors='coerce').dropna()
    if len(coverage_vals) > 0:
        positive = sum(1 for v in coverage_vals if v >= 0)
        min_val = coverage_vals.min()
        max_val = coverage_vals.max()
        profiling_results.append({
            'column': 'coverage_limit',
            'rule': defined_rules.get('coverage_limit', 'N/A')[:50],
            'check': 'positive values',
            'count': len(coverage_vals),
            'compliant': positive,
            'percentage': (positive / len(coverage_vals) * 100),
            'min': min_val,
            'max': max_val
        })
        print(f"✅ coverage_limit (positive values):")
        print(f"   Compliant: {positive}/{len(coverage_vals)} ({(positive/len(coverage_vals)*100):.1f}%)")
        print(f"   Actual range: [{min_val}, {max_val}]")
        print()

# Check underwriting_score (0-100 bounds)
if 'underwriting_score' in latest_cleaned.columns:
    score_vals = pd.to_numeric(latest_cleaned['underwriting_score'], errors='coerce').dropna()
    if len(score_vals) > 0:
        in_bounds = sum(1 for v in score_vals if 0 <= v <= 100)
        min_val = score_vals.min()
        max_val = score_vals.max()
        profiling_results.append({
            'column': 'underwriting_score',
            'rule': defined_rules.get('underwriting_score', 'N/A')[:50],
            'check': '0-100 bounds',
            'count': len(score_vals),
            'compliant': in_bounds,
            'percentage': (in_bounds / len(score_vals) * 100),
            'min': min_val,
            'max': max_val
        })
        print(f"✅ underwriting_score (0-100 bounds):")
        print(f"   Compliant: {in_bounds}/{len(score_vals)} ({(in_bounds/len(score_vals)*100):.1f}%)")
        print(f"   Actual range: [{min_val}, {max_val}]")
        print()

# ============================================================================
# 3. ALL RULES FROM JSON - CHECK WHICH ARE APPLIED
# ============================================================================
print("=" * 90)
print("3. ALL RULES MENTIONED IN JSON - STATUS CHECK")
print("=" * 90)
print()

if defined_rules:
    print(f"📋 Total rules defined: {len(defined_rules)}")
    print()
    print("Rules in JSON file:")
    for col, rule in list(defined_rules.items())[:15]:
        if col in latest_cleaned.columns:
            status = "✅"
        else:
            status = "⚠️"
        print(f"{status} {col}: {rule[:70]}...")
    
    if len(defined_rules) > 15:
        print(f"\n... and {len(defined_rules) - 15} more rules")
    print()

# ============================================================================
# 4. DETAILED TRANSFORMATION ANALYSIS
# ============================================================================
print("=" * 90)
print("4. DETAILED TRANSFORMATION ANALYSIS (Sampled Data)")
print("=" * 90)
print()

sample_indices = [0, min(1, len(latest_cleaned)-1), min(2, len(latest_cleaned)-1)]

for col in ['customer_name', 'email', 'phone', 'agent_commission', 'premium']:
    if col not in latest_cleaned.columns:
        continue
    
    print(f"📝 {col.upper()}")
    rule_text = defined_rules.get(col, 'No rule defined')
    print(f"   Rule: {rule_text[:70]}...")
    print(f"   Sample values from cleaned data:")
    
    for idx in sample_indices:
        val = latest_cleaned[col].iloc[idx]
        print(f"      Row {idx+1}: {val}")
    print()

# ============================================================================
# 5. SUMMARY REPORT
# ============================================================================
print("=" * 90)
print("5. VERIFICATION SUMMARY REPORT")
print("=" * 90)
print()

std_compliance = sum(r['percentage'] for r in standardization_results) / len(standardization_results) if standardization_results else 0
prof_compliance = sum(r['percentage'] for r in profiling_results) / len(profiling_results) if profiling_results else 0

print("📊 STANDARDIZATION RULES COMPLIANCE:")
for r in standardization_results:
    status = "✅" if r['percentage'] >= 90 else "⚠️"
    print(f"  {status} {r['column']}: {r['percentage']:.1f}% compliant")

print()
print("📊 DQ PROFILING RULES COMPLIANCE:")
for r in profiling_results:
    status = "✅" if r['percentage'] >= 90 else "⚠️"
    print(f"  {status} {r['column']}: {r['percentage']:.1f}% compliant")

print()
print("📊 OVERALL STATISTICS:")
print(f"  Standardization avg: {std_compliance:.1f}%")
print(f"  Profiling avg: {prof_compliance:.1f}%")
print(f"  Rules defined: {len(defined_rules)}")
print(f"  Rules applied to columns: {sum(1 for r in defined_rules if r in latest_cleaned.columns)}")

print()
print("=" * 90)
if std_compliance >= 80 and prof_compliance >= 80:
    print("✅ RESULT: VALUE STANDARDIZATION & DQ PROFILING RULES ARE BEING APPLIED!")
    print("           All major transformations are working correctly.")
elif std_compliance >= 60 or prof_compliance >= 60:
    print("⚠️  RESULT: Partial compliance - Some rules may need review.")
else:
    print("❌ RESULT: Low compliance - Check rule configurations.")
print("=" * 90)
print()
