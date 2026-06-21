import pandas as pd
df = pd.read_csv('output/Sample_Policy_Data_CLEANED_20260122_221335.csv')
print('Agent Commission > 100:')
high = df[df['agent_commission'] > 100][['policy_number', 'agent_commission']]
print(high.to_string() if not high.empty else 'None')
