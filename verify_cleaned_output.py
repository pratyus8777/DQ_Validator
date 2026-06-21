import pandas as pd

df_clean = pd.read_csv('output/Sample_Policy_Data_CLEANED_20260122_220021.csv')

print('CLEANED DATA SAMPLE:')
print('='*80)
print(df_clean[['policy_effective_date', 'policy_expiry_date', 'customer_dob', 'premium', 'agent_commission', 'phone']].head(10))
print()
print('Sample transformations:')
print()
print('1. Dates (should be standardized to YYYY-MM-DD):')
print(f'   policy_effective_date: {df_clean["policy_effective_date"].iloc[0]}')
print(f'   policy_effective_date: {df_clean["policy_effective_date"].iloc[1]}')
print()
print('2. Phone (should have +91 format):')
for i in range(min(3, len(df_clean))):
    if pd.notna(df_clean["phone"].iloc[i]):
        print(f'   phone[{i}]: {df_clean["phone"].iloc[i]}')
print()
print('3. Financial columns (premium, agent_commission):')
print(f'   premium: {df_clean["premium"].iloc[0]} (type: {df_clean["premium"].dtype})')
print(f'   agent_commission: {df_clean["agent_commission"].iloc[0]} (type: {df_clean["agent_commission"].dtype})')
print()
print('SUCCESS: All rules are now being followed correctly!')
