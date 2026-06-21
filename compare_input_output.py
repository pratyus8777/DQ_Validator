import pandas as pd
import glob

input_df = pd.read_csv('data/Sample_Policy_Data.csv', encoding='latin-1')

# Find latest cleaned file
cleaned_files = sorted(glob.glob('output/Sample_Policy_Data_CLEANED_*.csv'))
if not cleaned_files:
    print("No cleaned files found!")
    exit(1)

cleaned_file = cleaned_files[-1]
output_df = pd.read_csv(cleaned_file)

print('INPUT vs OUTPUT COMPARISON:')
print(f'Input shape: {input_df.shape}')
print(f'Output shape: {output_df.shape}')
print(f'Identical? {input_df.equals(output_df)}')

# Check specific columns
print('\n\nINPUT - Null counts:')
null_cols = ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 'National ID', 'Phone', 'Email']
for col in null_cols:
    print(f'  {col}: {input_df[col].isnull().sum()} nulls')

print('\n\nOUTPUT - Null counts:')
for col in null_cols:
    print(f'  {col}: {output_df[col].isnull().sum()} nulls')

print('\n\nSample rows comparison:')
print('\nINPUT row 0:')
print(input_df.iloc[0][['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 'Phone', 'Email']])
print('\nOUTPUT row 0:')
print(output_df.iloc[0][['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 'Phone', 'Email']])

print('\n\nChecking for differences in each column:')
for col in input_df.columns:
    diff_count = (input_df[col] != output_df[col]).sum()
    if diff_count > 0:
        print(f'{col}: {diff_count} differences')
