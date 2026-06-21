import pandas as pd
df = pd.read_csv('data/Sample_Policy_Data.csv')
print('Original data agent_commission:')
print(f"  Range: [{df['agent_commission'].min()}, {df['agent_commission'].max()}]")
print(f"  Count: {len(df)}")
print(f"  Values > 100: {(df['agent_commission'] > 100).sum()}")
print()
print('Values > 100:')
print(df[df['agent_commission'] > 100]['agent_commission'].values)
