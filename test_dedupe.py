import pandas as pd

# Read the original data
df = pd.read_csv('data/Sample_Policy_Data.csv')
print(f'Original records: {len(df)}')

# Check Policy Number uniqueness
print(f'Unique Policy Numbers: {df["Policy Number"].nunique()}')

# Simulate dedupe on Policy Number
df_deduped = df.drop_duplicates(subset=["Policy Number"], keep="first")
print(f'After dedup on Policy Number: {len(df_deduped)}')

# Check what happened
print(f'\nAll unique? {df["Policy Number"].is_unique}')
