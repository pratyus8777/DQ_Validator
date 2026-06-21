import pandas as pd

# Load data columns
data_cols = pd.read_csv('data/Sample_Policy_Data.csv', nrows=0).columns.tolist()
print("Actual data columns:")
for i, c in enumerate(data_cols, 1):
    print(f"  {i}. {c}")

# Load rule CDEs  
from data_io.db_helpers import read_guidewire_cleansing_rules

rules_df = read_guidewire_cleansing_rules()
rule_cdes = rules_df['CDE'].tolist()
print(f"\nRule CDEs from CSV:")
for i, c in enumerate(rule_cdes, 1):
    print(f"  {i}. {c}")

# Find matches
matches = [c for c in rule_cdes if c in data_cols]
misses = [c for c in rule_cdes if c not in data_cols]

print(f"\nMatching: {len(matches)}/{len(rule_cdes)}")
for m in matches:
    print(f"  ✓ {m}")

if misses:
    print(f"\nNot matching: {len(misses)}")
    for m in misses:
        print(f"  ✗ {m}")
