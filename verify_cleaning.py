import pandas as pd

df_in = pd.read_csv('data/Sample_Policy_Data.csv')
df_out = pd.read_csv('output/Sample_Policy_Data_clean.csv')

print('COMPLETENESS CHECK')
print('================')
print(f'Policy Effective Date - nulls in input: {df_in["Policy Effective Date"].isna().sum()}')
print(f'Policy Effective Date - nulls in output: {df_out["Policy Effective Date"].isna().sum()}')

print(f'\\nCancellation Effective Date - blanks in input: {(df_in["Cancellation Effective Date"].astype(str).str.strip() == "").sum()}')
print(f'Cancellation Effective Date - blanks in output: {(df_out["Cancellation Effective Date"].astype(str).str.strip() == "").sum()}')

print('\\nDATATYPE CHECK')
print('================')
print(f'Input Policy Effective Date dtype: {df_in["Policy Effective Date"].dtype}')
print(f'Output Policy Effective Date dtype: {df_out["Policy Effective Date"].dtype}')

print(f'\\nInput Endorsement Effective Date dtype: {df_in["Endorsement Effective Date"].dtype}')
print(f'Output Endorsement Effective Date dtype: {df_out["Endorsement Effective Date"].dtype}')

print('\\nSample standardized values:')
print(f'Output Policy Status unique values: {df_out["Policy Status"].unique()[:5]}')

print('\\nDATA SAMPLE COMPARISON')
print('========================')
print('Input row 0:')
print(f'  Policy Number: {df_in.iloc[0]["Policy Number"]}')
print(f'  Email: {df_in.iloc[0]["Email"]}')
print(f'  Policy Effective Date: {df_in.iloc[0]["Policy Effective Date"]}')

print('\\nOutput row 0:')
print(f'  Policy Number: {df_out.iloc[0]["Policy Number"]}')
print(f'  Email: {df_out.iloc[0]["Email"]}')
print(f'  Policy Effective Date: {df_out.iloc[0]["Policy Effective Date"]}')
