import pandas as pd
import json

# Check CSV user rules
rules_df = pd.read_csv('output/cleansing_rules.csv')
print('USER RULES FROM CSV:')
print('='*80)
for idx, row in rules_df.iterrows():
    if row['Column'] in ['premium', 'agent_commission', 'coverage_limit', 'underwriting_score']:
        print(f"{row['Column']}: {row['Rule']}")

# Check JSON user rules
with open('output/cleansing_rules.json') as f:
    rules_json = json.load(f)
    print('\nUSER RULES FROM JSON:')
    print('='*80)
    for col in ['premium', 'agent_commission', 'coverage_limit', 'underwriting_score']:
        if col in rules_json:
            print(f"{col}: {rules_json[col]}")

# Check actual cleaned data
df = pd.read_csv('output/Sample_Policy_Data_CLEANED_20260122_220806.csv')
print('\n\nACTUAL CLEANED VALUES:')
print('='*80)
print(f"Premium range: {df['premium'].min()} to {df['premium'].max()}")
print(f"Agent Commission range: {df['agent_commission'].min()} to {df['agent_commission'].max()}")
print(f"Coverage Limit range: {df['coverage_limit'].min()} to {df['coverage_limit'].max()}")
print(f"Underwriting Score sample: {df['underwriting_score'].head(3).values}")
print(f"\nProblem: Agent Commission max is {df['agent_commission'].max()}, should be 100!")
print(f"Problem: Underwriting Score is TEXT ('{df['underwriting_score'].iloc[0]}'), not numeric!")
