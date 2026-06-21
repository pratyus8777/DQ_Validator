"""
Comprehensive DQ Cleaning Pipeline
Reads input CSV, detects violations, applies fixes, outputs cleaned CSV
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
from pathlib import Path

class ComprehensiveDataCleaner:
    """Clean data based on real quality rules"""
    
    def __init__(self):
        self.input_file = 'data/Sample_Policy_Data.csv'
        self.output_dir = 'output'
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def read_data(self):
        """Read input data"""
        print(f"Reading: {self.input_file}")
        df = pd.read_csv(self.input_file, encoding='latin-1')
        print(f"Loaded {len(df)} records with {len(df.columns)} columns")
        return df.copy()
    
    def standardize_dates(self, df):
        """Standardize mixed date formats to YYYY-MM-DD"""
        date_columns = ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 
                       'Endorsement Effective Date', 'Cancellation Effective Date']
        
        violations = []
        
        for col in date_columns:
            if col not in df.columns:
                continue
                
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                    
                val_str = str(val).strip()
                parsed_date = None
                
                # Try multiple date formats
                formats = ['%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y', '%Y-%m-%d', '%d/%m/%Y']
                for fmt in formats:
                    try:
                        parsed_date = pd.to_datetime(val_str, format=fmt)
                        break
                    except:
                        continue
                
                if parsed_date is None:
                    # Try pandas automatic parsing
                    try:
                        parsed_date = pd.to_datetime(val_str, infer_datetime_format=True)
                    except:
                        # Do NOT delete or null the original value. Keep original and flag for review.
                        violations.append({
                            'row': idx,
                            'column': col,
                            'original_value': val,
                            'issue': 'Invalid date format',
                            'fix': 'Keep original value; flagged for manual remediation'
                        })
                        # keep original string unchanged
                        continue
                
                # Standardize to YYYY-MM-DD for this row only
                standardized = parsed_date.strftime('%Y-%m-%d')
                if str(val_str) != standardized:
                    violations.append({
                        'row': idx,
                        'column': col,
                        'original_value': val,
                        'issue': 'Non-standard date format',
                        'fix': f'Standardized to {standardized}'
                    })
                    df.at[idx, col] = standardized
        
        return df, violations
    
    def clean_emails(self, df):
        """Validate and clean email addresses"""
        violations = []
        
        if 'Email' not in df.columns:
            return df, violations
        
        for idx, email in df['Email'].items():
            if pd.isna(email):
                continue
            
            email_str = str(email).strip()
            
            # Basic email validation
            if '@' not in email_str or '.' not in email_str.split('@')[-1]:
                violations.append({
                    'row': idx,
                    'column': 'Email',
                    'original_value': email,
                    'issue': 'Invalid email format',
                    'fix': 'Removed invalid email'
                })
                df.at[idx, 'Email'] = np.nan
            else:
                # Standardize
                cleaned = email_str.lower().strip()
                if cleaned != email_str:
                    violations.append({
                        'row': idx,
                        'column': 'Email',
                        'original_value': email,
                        'issue': 'Non-standard email format',
                        'fix': f'Standardized to {cleaned}'
                    })
                    df.at[idx, 'Email'] = cleaned
        
        return df, violations
    
    def clean_phone(self, df):
        """Standardize phone numbers"""
        violations = []
        
        if 'Phone' not in df.columns:
            return df, violations
        
        for idx, phone in df['Phone'].items():
            if pd.isna(phone):
                continue
            
            phone_str = str(phone).strip()
            
            # Remove non-numeric characters except spaces and dashes
            numeric_only = ''.join(c for c in phone_str if c.isdigit())
            
            # Check length (phone numbers should be reasonable length)
            if len(numeric_only) < 7 or len(numeric_only) > 15:
                violations.append({
                    'row': idx,
                    'column': 'Phone',
                    'original_value': phone,
                    'issue': f'Invalid phone length: {len(numeric_only)} digits',
                    'fix': 'Removed invalid phone'
                })
                df.at[idx, 'Phone'] = np.nan
            else:
                # Standardize format
                if len(numeric_only) == 10:
                    standardized = f"{numeric_only[:3]}-{numeric_only[3:6]}-{numeric_only[6:]}"
                else:
                    standardized = numeric_only
                
                if standardized != phone_str:
                    violations.append({
                        'row': idx,
                        'column': 'Phone',
                        'original_value': phone,
                        'issue': 'Non-standard phone format',
                        'fix': f'Standardized to {standardized}'
                    })
                    df.at[idx, 'Phone'] = standardized
        
        return df, violations
    
    def clean_policy_number(self, df):
        """Validate and clean policy numbers"""
        violations = []
        
        if 'Policy Number' not in df.columns:
            return df, violations
        
        for idx, policy in df['Policy Number'].items():
            if pd.isna(policy):
                violations.append({
                    'row': idx,
                    'column': 'Policy Number',
                    'original_value': policy,
                    'issue': 'Missing policy number',
                    'fix': 'Removed null policy'
                })
                continue
            
            policy_str = str(policy).strip()
            
            # Policy should start with POL- and have 8 digits
            if not policy_str.startswith('POL-'):
                violations.append({
                    'row': idx,
                    'column': 'Policy Number',
                    'original_value': policy,
                    'issue': 'Invalid policy format',
                    'fix': f'Corrected to standard format'
                })
                if len(policy_str) >= 8:
                    df.at[idx, 'Policy Number'] = f"POL-{policy_str[-8:]}"
            
            # Check for valid format
            parts = policy_str.split('-')
            if len(parts) != 2 or len(parts[1]) != 8 or not parts[1].isdigit():
                violations.append({
                    'row': idx,
                    'column': 'Policy Number',
                    'original_value': policy,
                    'issue': 'Invalid policy number format',
                    'fix': 'Removed malformed policy'
                })
                df.at[idx, 'Policy Number'] = np.nan
        
        return df, violations
    
    def clean_numeric_fields(self, df):
        """Clean numeric fields"""
        violations = []
        numeric_cols = ['Coverage Limit', 'Coverage Deductible', 'Premium Amount', 'Agent Commission %']
        
        for col in numeric_cols:
            if col not in df.columns:
                continue
            
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                
                try:
                    numeric_val = float(val)
                    
                    # Check for negative values (should be positive)
                    if numeric_val < 0:
                        violations.append({
                            'row': idx,
                            'column': col,
                            'original_value': val,
                            'issue': 'Negative value in positive field',
                            'fix': f'Converted to absolute value: {abs(numeric_val)}'
                        })
                        df.at[idx, col] = abs(numeric_val)
                    
                    # Check for unreasonable values
                    if col == 'Agent Commission %' and (numeric_val < 0 or numeric_val > 100):
                        violations.append({
                            'row': idx,
                            'column': col,
                            'original_value': val,
                            'issue': f'Invalid percentage: {numeric_val}%',
                            'fix': 'Set to 0'
                        })
                        df.at[idx, col] = 0
                        
                except (ValueError, TypeError):
                    violations.append({
                        'row': idx,
                        'column': col,
                        'original_value': val,
                        'issue': 'Non-numeric value',
                        'fix': 'Removed invalid value'
                    })
                    df.at[idx, col] = np.nan
        
        return df, violations
    
    def clean_text_fields(self, df):
        """Clean text fields - remove extra whitespace, standardize case"""
        violations = []
        text_cols = ['Customer Name', 'Address', 'Agent ID', 'Underwriter ID']
        
        for col in text_cols:
            if col not in df.columns:
                continue
            
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                
                val_str = str(val).strip()
                
                # Remove multiple spaces
                cleaned = ' '.join(val_str.split())
                
                if cleaned != val_str:
                    violations.append({
                        'row': idx,
                        'column': col,
                        'original_value': val,
                        'issue': 'Extra whitespace',
                        'fix': 'Removed extra whitespace'
                    })
                    df.at[idx, col] = cleaned
        
        return df, violations
    
    def remove_duplicates(self, df):
        """Identify and flag duplicate policy numbers"""
        violations = []
        
        if 'Policy Number' not in df.columns:
            return df, violations
        
        # Find duplicate policy numbers
        dup_mask = df['Policy Number'].duplicated(keep=False)
        dup_policies = df[dup_mask]['Policy Number'].unique()
        
        for policy in dup_policies:
            dup_rows = df[df['Policy Number'] == policy].index.tolist()
            for row_idx in dup_rows:
                violations.append({
                    'row': row_idx,
                    'column': 'Policy Number',
                    'original_value': policy,
                    'issue': f'Duplicate policy number ({len(dup_rows)} occurrences)',
                    'fix': 'Flagged for review'
                })
        
        return df, violations
    
    def process(self):
        """Run complete cleaning process"""
        print("\n" + "="*80)
        print("COMPREHENSIVE DATA QUALITY CLEANING")
        print("="*80 + "\n")
        
        # Read input
        df_original = self.read_data()
        df_cleaned = df_original.copy()
        
        all_violations = []
        
        # Apply cleaning steps
        print("\n1. Cleaning dates...")
        df_cleaned, viol = self.standardize_dates(df_cleaned)
        all_violations.extend(viol)
        print(f"   Found {len(viol)} date violations")
        
        print("2. Cleaning emails...")
        df_cleaned, viol = self.clean_emails(df_cleaned)
        all_violations.extend(viol)
        print(f"   Found {len(viol)} email violations")
        
        print("3. Cleaning phone numbers...")
        df_cleaned, viol = self.clean_phone(df_cleaned)
        all_violations.extend(viol)
        print(f"   Found {len(viol)} phone violations")
        
        print("4. Cleaning policy numbers...")
        df_cleaned, viol = self.clean_policy_number(df_cleaned)
        all_violations.extend(viol)
        print(f"   Found {len(viol)} policy violations")
        
        print("5. Cleaning numeric fields...")
        df_cleaned, viol = self.clean_numeric_fields(df_cleaned)
        all_violations.extend(viol)
        print(f"   Found {len(viol)} numeric violations")
        
        print("6. Cleaning text fields...")
        df_cleaned, viol = self.clean_text_fields(df_cleaned)
        all_violations.extend(viol)
        print(f"   Found {len(viol)} text violations")
        
        print("7. Detecting duplicates...")
        df_cleaned, viol = self.remove_duplicates(df_cleaned)
        all_violations.extend(viol)
        print(f"   Found {len(viol)} duplicate violations")
        
        # Save outputs
        print("\n" + "="*80)
        print("SAVING OUTPUTS")
        print("="*80 + "\n")
        
        # Save cleaned data
        cleaned_file = os.path.join(self.output_dir, f'Sample_Policy_Data_CLEANED_{self.timestamp}.csv')
        df_cleaned.to_csv(cleaned_file, index=False)
        print(f"✓ Cleaned data saved: {cleaned_file}")
        
        # Save original data
        original_file = os.path.join(self.output_dir, f'Sample_Policy_Data_ORIGINAL_{self.timestamp}.csv')
        df_original.to_csv(original_file, index=False)
        print(f"✓ Original data saved: {original_file}")
        
        # Save violations report
        violations_file = os.path.join(self.output_dir, f'Violations_Report_{self.timestamp}.csv')
        df_violations = pd.DataFrame(all_violations)
        df_violations.to_csv(violations_file, index=False)
        print(f"✓ Violations report saved: {violations_file}")
        
        # Save JSON report
        summary = {
            'timestamp': self.timestamp,
            'total_records': len(df_original),
            'total_columns': len(df_original.columns),
            'total_violations': len(all_violations),
            'violations_by_column': df_violations['column'].value_counts().to_dict() if len(df_violations) > 0 else {},
            'violations_by_issue': df_violations['issue'].value_counts().to_dict() if len(df_violations) > 0 else {},
            'before_nulls': df_original.isnull().sum().to_dict(),
            'after_nulls': df_cleaned.isnull().sum().to_dict(),
        }
        
        report_file = os.path.join(self.output_dir, f'Cleaning_Summary_{self.timestamp}.json')
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"✓ Summary report saved: {report_file}")

        # Generate Excel assessment report
        try:
            excel_file = os.path.join(self.output_dir, f'DQ_Assessment_{self.timestamp}.xlsx')
            with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
                # Summary sheet
                summary_df = pd.DataFrame({
                    'metric': ['total_records', 'total_columns', 'total_violations'],
                    'value': [summary['total_records'], summary['total_columns'], summary['total_violations']]
                })
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Violations sheet
                if len(df_violations) > 0:
                    df_violations.to_excel(writer, sheet_name='Violations', index=False)
                else:
                    pd.DataFrame(columns=['row','column','original_value','issue','fix']).to_excel(writer, sheet_name='Violations', index=False)

                # Before/After nulls
                before_nulls_df = pd.DataFrame(list(summary['before_nulls'].items()), columns=['column', 'before_nulls'])
                after_nulls_df = pd.DataFrame(list(summary['after_nulls'].items()), columns=['column', 'after_nulls'])
                nulls_df = pd.merge(before_nulls_df, after_nulls_df, on='column', how='outer')
                nulls_df.to_excel(writer, sheet_name='Nulls', index=False)

            print(f"✓ Assessment Excel report saved: {excel_file}")
        except Exception as e:
            print(f"Failed to write Excel assessment: {e}")
        
        # Print summary
        print("\n" + "="*80)
        print("CLEANING SUMMARY")
        print("="*80)
        print(f"\nTotal Records: {len(df_original)}")
        print(f"Total Columns: {len(df_original.columns)}")
        print(f"Total Violations Found & Fixed: {len(all_violations)}")
        
        print("\n\nViolations by Column:")
        if len(df_violations) > 0:
            for col, count in df_violations['column'].value_counts().items():
                print(f"  {col}: {count}")
        
        print("\n\nViolations by Issue Type:")
        if len(df_violations) > 0:
            for issue, count in df_violations['issue'].value_counts().items():
                print(f"  {issue}: {count}")
        
        print("\n\nBefore Cleaning - Null Values:")
        for col in ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 'Phone', 'Email']:
            if col in df_original.columns:
                print(f"  {col}: {df_original[col].isnull().sum()}")
        
        print("\n\nAfter Cleaning - Null Values:")
        for col in ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 'Phone', 'Email']:
            if col in df_cleaned.columns:
                print(f"  {col}: {df_cleaned[col].isnull().sum()}")
        
        print("\n" + "="*80)
        print("CLEANING COMPLETE!")
        print("="*80 + "\n")
        
        return df_original, df_cleaned, all_violations, summary

if __name__ == '__main__':
    cleaner = ComprehensiveDataCleaner()
    original, cleaned, violations, summary = cleaner.process()
