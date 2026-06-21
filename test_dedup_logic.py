#!/usr/bin/env python
"""Test deduplication logic"""

import pandas as pd

# Create test data with duplicates
data = {
    'ID': [1, 2, 2, 3, 3, 3, 4],
    'Name': ['Alice', 'Bob', 'Bob', 'Charlie', 'Charlie', 'Charlie', 'David'],
    'Email': ['alice@test.com', 'bob@test.com', 'bob@test.com', 'charlie@test.com', 'charlie@test.com', 'charlie@test.com', 'david@test.com']
}

df = pd.DataFrame(data)
print("Original data:")
print(df)
print(f"Total rows: {len(df)}")
print(f"Duplicates: {df.duplicated().sum()}")

# Test keep-first
df_keep_first = df.drop_duplicates(keep='first')
print("\n\nAfter drop_duplicates(keep='first'):")
print(df_keep_first)
print(f"Total rows: {len(df_keep_first)}")

# Test keep-last
df_keep_last = df.drop_duplicates(keep='last')
print("\n\nAfter drop_duplicates(keep='last'):")
print(df_keep_last)
print(f"Total rows: {len(df_keep_last)}")

# Test remove-all
df_remove_all = df.drop_duplicates(keep=False)
print("\n\nAfter drop_duplicates(keep=False) [remove-all]:")
print(df_remove_all)
print(f"Total rows: {len(df_remove_all)}")
