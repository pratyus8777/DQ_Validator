import pandas as pd
df = pd.read_csv('output/Sample_Policy_Data_CLEANED_20260122_221335.csv')
print('Agent Commission values > 100:')
high_values = df[df['agent_commission'] > 100]['agent_commission'].values
print(high_values)
print(f'Count: {len(high_values)}')
print(f'Max: {df["agent_commission"].max()}')
