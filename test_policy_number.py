import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Get the latest cleaned file
cleaned_files = sorted(Path('output').glob('Sample_Policy_Data_CLEANED_*.csv'))
if cleaned_files:
    latest = cleaned_files[-1]
    print(f'Latest cleaned file: {latest.name}')
    print()
    
    df = pd.read_csv(latest, nrows=5)
    print('Cleaned data - policy_number column:')
    print(df[['policy_number']].head())
    print()
    
    # Compare with original
    from data_io.db_helpers import read_sample_policy_data
    df_orig = read_sample_policy_data(5)
    print('Original data - policy_number column:')
    print(df_orig[['policy_number']].head())
    print()
    
    # Check if preserved
    orig_val = df_orig['policy_number'].iloc[0]
    clean_val = df['policy_number'].iloc[0]
    
    if clean_val == orig_val:
        print('✓ SUCCESS: policy_number format is PRESERVED')
    else:
        print('✗ FAILED: policy_number format is NOT preserved')
        print(f'  Original: {orig_val}')
        print(f'  Cleaned:  {clean_val}')
