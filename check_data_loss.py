import pandas as pd

orig = pd.read_csv('data/Sample_Policy_Data.csv')
print('ORIGINAL DATA')
print('Shape:', orig.shape)
print('\nFirst row sample:')
for col in orig.columns[:5]:
    print(f'  {col}: {orig.iloc[0][col]}')

clean = pd.read_csv('output/Sample_Policy_Data_clean.csv')
print('\n\nCLEANED DATA')
print('Shape:', clean.shape)
print('\nFirst row sample:')
for col in clean.columns[:5]:
    print(f'  {col}: {clean.iloc[0][col]}')

print('\n\nNaN increase analysis:')
nan_increase = False
for col in orig.columns:
    orig_nan = orig[col].isnull().sum()
    clean_nan = clean[col].isnull().sum() if col in clean.columns else 0
    if clean_nan > orig_nan:
        print(f'{col}: {orig_nan} -> {clean_nan} (+{clean_nan - orig_nan})')
        nan_increase = True

if not nan_increase:
    print('No NaN increase detected. Data appears to be preserved.')

# Show sample of date columns
print('\n\nDate columns sample (original):')
for col in orig.columns:
    if 'date' in col.lower() or 'dob' in col.lower():
        print(f'\n{col}:')
        print(f'  Type: {orig[col].dtype}')
        print(f'  Sample values: {orig[col].head(3).tolist()}')

print('\n\nDate columns sample (cleaned):')
for col in clean.columns:
    if 'date' in col.lower() or 'dob' in col.lower():
        print(f'\n{col}:')
        print(f'  Type: {clean[col].dtype}')
        print(f'  Sample values: {clean[col].head(3).tolist()}')
