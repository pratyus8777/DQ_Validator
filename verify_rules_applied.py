import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Get the latest cleaned file
cleaned_files = sorted(Path('output').glob('Sample_Policy_Data_CLEANED_*.csv'))
if cleaned_files:
    latest = cleaned_files[-1]
    df = pd.read_csv(latest, nrows=5)
    
    print("\nCLEANED DATA VERIFICATION:")
    print("="*80)
    print("\n1. Email column (rule: convert to uppercase)")
    print(df[['email']].head(3).to_string())
    print("\nCheck: Should be UPPERCASE")
    
    print("\n2. Phone column (rule: format as +80-XXXXX-XXXXX)")
    print(df[['phone']].head(3).to_string())
    print("\nCheck: Should be in format +80-XXXXX-XXXXX or +91-XXXXX-XXXXX")
    
    # Compare first email with original
    from data_io.db_helpers import read_sample_policy_data
    df_orig = read_sample_policy_data(1)
    orig_email = df_orig['email'].iloc[0]
    clean_email = df['email'].iloc[0]
    
    print(f"\n3. Email transformation:")
    print(f"   Original: {orig_email}")
    print(f"   Cleaned:  {clean_email}")
    if clean_email == orig_email.upper():
        print("   [OK] Email was uppercased as per rule")
    else:
        print("   [CHECK] Email transformation result")
