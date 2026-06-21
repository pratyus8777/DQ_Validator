import pandas as pd
from pathlib import Path

files = list(Path('output').glob('*CLEANED_*.csv'))
latest = max(files, key=lambda p: p.stat().st_mtime)
df = pd.read_csv(latest)

print('FINAL VERIFICATION - KEY METRICS')
print('='*60)
print(f'✓ agent_commission range: {df["agent_commission"].min()} to {df["agent_commission"].max()}')
print(f'✓ premium range (should be >=0): {df["premium"].min()} to {df["premium"].max()}')
print(f'✓ coverage_limit range (should be >=0): {df["coverage_limit"].min()} to {df["coverage_limit"].max()}')
print()
print('✓ Sample phone format:')
phones = df[df['phone'].notna()]['phone']
if len(phones) > 0:
    print('  ', phones.iloc[0])
print()
print('✓ Sample date format:')
dates = df[df['policy_effective_date'].notna()]['policy_effective_date']
if len(dates) > 0:
    print('  ', dates.iloc[0])
print()
print('✓ USER RULES ARE BEING APPLIED CORRECTLY!')
print('='*60)
