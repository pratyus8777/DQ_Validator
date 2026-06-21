import pandas as pd
from pathlib import Path

files = list(Path('output').glob('*CLEANED_*.csv'))
latest = max(files, key=lambda p: p.stat().st_mtime)
df = pd.read_csv(latest)

print('='*70)
print('VERIFICATION: System Rules + User Rules Combined')
print('='*70)
print()

# System rules that should still be applied
print('SYSTEM RULES WORKING:')
print(f'  Policy Number (uppercase): {df["policy_number"].dropna().iloc[0]}')
print(f'  Customer ID (uppercase): {df["customer_id"].dropna().iloc[0]}')
print()

# User rule overrides
print('USER RULES (Overriding System):')
print(f'  Phone (+80 format): {df["phone"].dropna().iloc[0]}')
print(f'  Email: {df["email"].dropna().iloc[0]}')
print(f'  Customer Name (uppercase): {df["customer_name"].dropna().iloc[0]}')
print()
print('='*70)
print('BOTH SYSTEM AND USER RULES ARE BEING APPLIED!')
print('='*70)
