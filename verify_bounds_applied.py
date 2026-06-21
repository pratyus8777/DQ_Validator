import pandas as pd

# Check actual cleaned values
df = pd.read_csv('output/Sample_Policy_Data_CLEANED_20260122_221335.csv')

print('CLEANED DATA VERIFICATION:')
print('='*80)

print('\nPremium column:')
print(f"  Range: {df['premium'].min()} to {df['premium'].max()}")
print(f"  Sample values: {df['premium'].head(5).values}")
print(f"  All positive? {(df['premium'] >= 0).all()}")

print('\nAgent Commission column:')
print(f"  Range: {df['agent_commission'].min()} to {df['agent_commission'].max()}")
print(f"  Sample values: {df['agent_commission'].head(5).values}")
print(f"  Max value constrained to 100? {df['agent_commission'].max() <= 100}")

print('\nCoverage Limit column:')
print(f"  Range: {df['coverage_limit'].min()} to {df['coverage_limit'].max()}")
print(f"  All non-negative? {(df['coverage_limit'] >= 0).all()}")

# Check for original data to compare
original_df = pd.read_csv('data/Sample_Policy_Data.csv')
print('\n\nCOMPARISON WITH ORIGINAL:')
print('='*80)

premium_col = original_df['premium']
print('\nOriginal Premium:')
print(f"  Range: {premium_col.min()} to {premium_col.max()}")
original_negatives = (premium_col < 0).sum()
print(f"  Negative values count: {original_negatives}")

print('\nCleaned Premium:')
cleaned_negatives = (df['premium'] < 0).sum()
print(f"  Negative values count: {cleaned_negatives}")
print(f"  Negatives removed? {original_negatives > 0 and cleaned_negatives == 0}")

comm_col = original_df['agent_commission']
print('\nOriginal Agent Commission:')
print(f"  Range: {comm_col.min()} to {comm_col.max()}")
original_oob = ((comm_col < 0) | (comm_col > 100)).sum()
print(f"  Out-of-range (< 0 or > 100) count: {original_oob}")

print('\nCleaned Agent Commission:')
cleaned_oob = ((df['agent_commission'] < 0) | (df['agent_commission'] > 100)).sum()
print(f"  Out-of-range (< 0 or > 100) count: {cleaned_oob}")
print(f"  Out-of-range values fixed? {original_oob > 0 and cleaned_oob == 0}")

print('\n✅ SUCCESS!' if (cleaned_negatives == 0 and cleaned_oob == 0) else '\n❌ ISSUES FOUND')
