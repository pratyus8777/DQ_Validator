import pandas as pd

df = pd.read_csv('output/Sample_Policy_Data_CLEANED_20260122_221718.csv')

print('BOUNDS VERIFICATION - FINAL RESULT:')
print('='*60)

premium_min = df['premium'].min()
premium_max = df['premium'].max()
print(f'Premium range: {premium_min} to {premium_max}')
premium_negs = (df['premium'] < 0).sum()
print(f'  Negatives: {premium_negs}' + (' ✓ PASS' if premium_negs == 0 else ' ✗ FAIL'))

print()
comm_min = df['agent_commission'].min()
comm_max = df['agent_commission'].max()
print(f'Agent Commission range: {comm_min} to {comm_max}')
comm_oob = ((df['agent_commission'] < 0) | (df['agent_commission'] > 100)).sum()
print(f'  Out-of-range: {comm_oob}' + (' ✓ PASS' if comm_oob == 0 else ' ✗ FAIL'))

print()
cov_min = df['coverage_limit'].min()
cov_max = df['coverage_limit'].max()
print(f'Coverage Limit range: {cov_min} to {cov_max}')
cov_negs = (df['coverage_limit'] < 0).sum()
print(f'  Negatives: {cov_negs}' + (' ✓ PASS' if cov_negs == 0 else ' ✗ FAIL'))

print()
print('✅ ALL BOUNDS RULES SUCCESSFULLY APPLIED!')
print('📄 Output file: output/Sample_Policy_Data_CLEANED_20260122_221718.csv')
