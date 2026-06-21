"""Analyze actual data quality issues in the sample data"""

import pandas as pd
import numpy as np

# Read data
df = pd.read_csv('data/Sample_Policy_Data.csv', encoding='latin-1')

print("="*80)
print("DATA QUALITY ANALYSIS - Sample Policy Data")
print("="*80)
print(f"Total Records: {len(df)}")
print(f"Total Columns: {len(df.columns)}\n")

print("1. NULL/NAN VALUES BY COLUMN:")
print("-" * 40)
null_counts = df.isnull().sum()
null_counts = null_counts[null_counts > 0]
if len(null_counts) > 0:
    print(null_counts)
else:
    print("No NULL values found")

print("\n2. BLANK/EMPTY STRINGS BY COLUMN:")
print("-" * 40)
blank_counts = {}
for col in df.columns:
    blank_count = (df[col].astype(str).str.strip() == "").sum()
    if blank_count > 0:
        blank_counts[col] = blank_count

if blank_counts:
    for col, count in blank_counts.items():
        print(f"{col}: {count} blank values")
else:
    print("No blank values found")

print("\n3. DATA TYPE ISSUES:")
print("-" * 40)
# Check date columns
date_cols = ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 'Endorsement Effective Date', 'Cancellation Effective Date']
for col in date_cols:
    if col in df.columns:
        invalid_dates = 0
        for val in df[col].dropna():
            try:
                pd.to_datetime(val)
            except:
                invalid_dates += 1
        if invalid_dates > 0:
            print(f"{col}: {invalid_dates} invalid date values")
            # Show samples
            print(f"  Samples: {df[col].dropna().head(3).tolist()}")

print("\n4. DUPLICATE/UNIQUENESS ISSUES:")
print("-" * 40)
unique_cols = ['Policy Number', 'Customer ID', 'Coverage ID', 'Agent ID']
for col in unique_cols:
    if col in df.columns:
        total = len(df[col].dropna())
        unique = df[col].nunique()
        duplicates = total - unique
        if duplicates > 0:
            print(f"{col}: {duplicates} duplicate values out of {total}")

print("\n5. SAMPLE DATA ISSUES:")
print("-" * 40)
print("\nFirst 10 rows:")
print(df[['Policy Number', 'Policy Effective Date', 'Policy Status', 'Customer Name', 'Customer ID']].head(10))

print("\n6. COLUMNS WITH ISSUES:")
print("-" * 40)
print("\nPolicy Effective Date samples (various formats detected):")
print(df['Policy Effective Date'].unique()[:10])

print("\nPolicy Status values:")
print(df['Policy Status'].value_counts())

print("\nRenewal Indicator values:")
print(df['Renewal Indicator'].value_counts())
