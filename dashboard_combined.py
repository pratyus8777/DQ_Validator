"""
Combined DQ Dashboard - Best Features from All Versions
Assessment First -> Define Rules -> Review -> Clean -> Results
"""

import streamlit as st
import pandas as pd
import json
import subprocess
import os
import glob
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="DQ Portal - Assessment First", layout="wide")

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #f0f2f6;
        font-weight: 600;
        padding: 12px 20px;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #0066CC;
        color: white;
    }
    .phase-box { 
        padding: 20px; 
        border-radius: 10px; 
        margin: 15px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .phase-2 { 
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        border-left: 5px solid #FF9800; 
    }
    .column-header {
        background: #0066CC;
        color: white;
        padding: 12px 15px;
        border-radius: 5px;
        font-weight: bold;
    }
    .success-card {
        background-color: #D4EDDA;
        border-left: 4px solid #28A745;
        padding: 15px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Data Quality Portal")
st.markdown("### Assessment First -> Define Rules -> Clean -> Results")

def sanitize_dataframe(df):
    try:
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str)
        return df
    except:
        return df

@st.cache_data
def load_original_data():
    try:
        original_files = sorted(glob.glob('output/Sample_Policy_Data_ORIGINAL_*.csv'))
        if original_files:
            return sanitize_dataframe(pd.read_csv(original_files[-1]))
        return sanitize_dataframe(pd.read_csv('data/Sample_Policy_Data.csv'))
    except:
        return None

@st.cache_data
def load_cleaned_data():
    try:
        cleaned_files = sorted(glob.glob('output/Sample_Policy_Data_CLEANED_*.csv'))
        if cleaned_files:
            return sanitize_dataframe(pd.read_csv(cleaned_files[-1]))
    except:
        pass
    return None

def save_cleansing_rules(rules_dict):
    try:
        rules_path = Path('output/cleansing_rules.json')
        with open(rules_path, 'w') as f:
            json.dump(rules_dict, f, indent=2)
        return rules_path
    except:
        return None

def load_cleansing_rules():
    try:
        rules_file = Path('output/cleansing_rules.json')
        if rules_file.exists():
            with open(rules_file, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

if 'assessment_report' not in st.session_state:
    st.session_state.assessment_report = None
if 'cleansing_rules' not in st.session_state:
    st.session_state.cleansing_rules = load_cleansing_rules()

original_df = load_original_data()
cleaned_df = load_cleaned_data()

tabs = st.tabs(["1. Input Rules", "2. Run Assessment", "3. Assessment Report", "4. Define Rules", "5. Clean Data", "6. Results"])

# TAB 1: INPUT RULES
with tabs[0]:
    st.header("Step 1: Input Cleansing Rules")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Option A: Upload Rules CSV")
        uploaded_file = st.file_uploader("Upload CSV (Column, Rule)", type=['csv'])
        if uploaded_file:
            rules_df = pd.read_csv(uploaded_file)
            if len(rules_df.columns) >= 2:
                st.dataframe(rules_df)
                if 'Column' not in rules_df.columns:
                    rules_df.rename(columns={rules_df.columns[0]: 'Column', rules_df.columns[1]: 'Rule'}, inplace=True)
                rules_df.to_csv(Path('temp_rules.csv'), index=False)
                st.success(f"Loaded: {len(rules_df)} rules")
    
    with col2:
        st.subheader("Option B: Sample Rules by Column Type")
        st.markdown("""
        **Date Columns**: Convert to YYYY-MM-DD format
        **Phone**: Format as +CC-XXXXX-XXXXX
        **Email**: Convert to lowercase
        **Text**: Trim and titlecase
        """)

# TAB 2: RUN ASSESSMENT
with tabs[1]:
    st.header("Step 2: Run Assessment")
    
    col1, col2 = st.columns(2)
    with col1:
        mode = st.radio("Assessment Mode:", ["Fast (no LLM, 2 sec)", "Full (with LLM, 1+ min)"], index=0)
    with col2:
        st.info(f"Selected: {mode}")
    
    if st.button("RUN ASSESSMENT", use_container_width=True):
        st.info("Running assessment...")
        try:
            cmd = ["python", "assessment_first_pipeline.py"]
            if "Fast" in mode:
                cmd.append("--fast")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if proc.returncode == 0:
                st.success("Assessment Complete!")
                reports = sorted(Path('output').glob('Assessment_Report_*.json'), reverse=True)
                if reports:
                    with open(reports[0], 'r') as f:
                        st.session_state.assessment_report = json.load(f)
                    st.info(f"Report: {reports[0].name}")
            else:
                st.error(proc.stderr)
        except Exception as e:
            st.error(f"Error: {e}")

# TAB 3: ASSESSMENT REPORT
with tabs[2]:
    st.header("Step 3: Review Assessment Report")
    
    if st.session_state.assessment_report:
        report = st.session_state.assessment_report
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Records", report.get('summary', {}).get('total_records', 'N/A'))
        with col2:
            st.metric("Columns", report.get('summary', {}).get('total_columns', 'N/A'))
        with col3:
            st.metric("Problem Columns", report.get('summary', {}).get('columns_with_issues', 0))
        
        st.subheader("Column Profiles")
        try:
            columns_data = []
            for col, profile in report.get('column_profiles', {}).items():
                columns_data.append({
                    'Column': col,
                    'Type': profile.get('data_type', 'N/A'),
                    'Non-null %': f"{100 - profile.get('null_percentage', 0):.1f}%",
                    'Unique': profile.get('unique_values', 0)
                })
            if columns_data:
                st.dataframe(pd.DataFrame(columns_data), use_container_width=True)
        except:
            pass
        
        st.download_button("Download Report", json.dumps(report, indent=2, default=str), "report.json")
    else:
        st.info("Run assessment first")

# TAB 4: DEFINE CLEANSING RULES
with tabs[3]:
    st.header("Step 4: Define Cleansing Rules by Column Type")
    
    st.markdown("Configure how each column should be cleaned and standardized")
    
    if original_df is None:
        st.error("No data available")
    else:
        date_cols = ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 'Endorsement Effective Date', 'Cancellation Effective Date']
        contact_cols = ['Phone', 'Email']
        financial_cols = ['Premium Amount', 'Coverage Limit', 'Coverage Deductible', 'Agent Commission %']
        text_cols = ['Customer Name', 'Agent Name', 'Address', 'Policy Status', 'Line of Business']
        id_cols = ['Policy Number', 'Customer ID', 'Coverage ID', 'Agent ID', 'National ID']
        
        avail_dates = [c for c in date_cols if c in original_df.columns]
        avail_contact = [c for c in contact_cols if c in original_df.columns]
        avail_financial = [c for c in financial_cols if c in original_df.columns]
        avail_text = [c for c in text_cols if c in original_df.columns]
        avail_ids = [c for c in id_cols if c in original_df.columns]
        
        if avail_dates:
            st.subheader("Date Columns")
            for col in avail_dates:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.write("Samples:")
                    for s in original_df[col].dropna().head(2):
                        st.write(f"• {s}")
                with col2:
                    rule = st.text_input(f"Rule", value=st.session_state.cleansing_rules.get(col, ""), placeholder="E.g., Convert to YYYY-MM-DD", key=f"date_{col}")
                    st.session_state.cleansing_rules[col] = rule
        
        if avail_contact:
            st.subheader("Contact Columns")
            for col in avail_contact:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.write("Samples:")
                    for s in original_df[col].dropna().head(2):
                        st.write(f"• {s}")
                with col2:
                    rule = st.text_input(f"Rule", value=st.session_state.cleansing_rules.get(col, ""), placeholder="E.g., Format as +XX-XXXXX-XXXXX", key=f"contact_{col}")
                    st.session_state.cleansing_rules[col] = rule
        
        if avail_financial:
            st.subheader("Financial Columns")
            for col in avail_financial:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.write("Samples:")
                    for s in original_df[col].dropna().head(2):
                        st.write(f"• {s}")
                with col2:
                    rule = st.text_input(f"Rule", value=st.session_state.cleansing_rules.get(col, ""), placeholder="E.g., Currency format", key=f"fin_{col}")
                    st.session_state.cleansing_rules[col] = rule
        
        if avail_text:
            st.subheader("Text Columns")
            for col in avail_text:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.write("Samples:")
                    for s in original_df[col].dropna().head(2):
                        st.write(f"• {str(s)[:30]}")
                with col2:
                    rule = st.text_input(f"Rule", value=st.session_state.cleansing_rules.get(col, ""), placeholder="E.g., Trim and titlecase", key=f"text_{col}")
                    st.session_state.cleansing_rules[col] = rule
        
        if avail_ids:
            st.subheader("ID Columns")
            for col in avail_ids:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.write("Samples:")
                    for s in original_df[col].dropna().head(2):
                        st.write(f"• {s}")
                with col2:
                    rule = st.text_input(f"Rule", value=st.session_state.cleansing_rules.get(col, ""), placeholder="E.g., Uppercase", key=f"id_{col}")
                    st.session_state.cleansing_rules[col] = rule
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Save Rules"):
                rules_file = save_cleansing_rules(st.session_state.cleansing_rules)
                if rules_file:
                    st.success(f"Rules saved!")
        with col2:
            if st.button("Preview Rules"):
                rules_with_values = {k: v for k, v in st.session_state.cleansing_rules.items() if v and v.strip()}
                st.json(rules_with_values)
        with col3:
            if st.button("Clear All"):
                st.session_state.cleansing_rules = {}
                st.rerun()

# TAB 5: CLEAN DATA
with tabs[4]:
    st.header("Step 5: Clean Data")
    
    if original_df is not None:
        if cleaned_df is not None:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Original Records", len(original_df))
            with col2:
                st.metric("Cleaned Records", len(cleaned_df))
            with col3:
                st.metric("Records Removed", len(original_df) - len(cleaned_df))
            st.success("Cleaned data is available")
        else:
            st.warning("Cleaning has not been executed")
    
    st.markdown("---")
    if st.button("CLEAN MY DATA NOW", use_container_width=True):
        st.warning("Cleaning in progress...")
        try:
            rules_file = save_cleansing_rules(st.session_state.cleansing_rules)
            cmd = ["python", "assessment_first_pipeline.py", "--clean"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if proc.returncode == 0:
                st.success("Data cleaning completed!")
                st.cache_data.clear()
                cleaned_files = sorted(Path('output').glob('Sample_Policy_Data_CLEANED_*.csv'), reverse=True)
                if cleaned_files:
                    st.info(f"Cleaned: {cleaned_files[0].name}")
                    df_cleaned = pd.read_csv(cleaned_files[0])
                    st.metric("New record count", len(df_cleaned))
                    st.dataframe(df_cleaned.head(10), use_container_width=True)
                    st.download_button("Download", df_cleaned.to_csv(index=False), cleaned_files[0].name)
            else:
                st.error(proc.stderr)
        except Exception as e:
            st.error(f"Error: {e}")

# TAB 6: RESULTS
with tabs[5]:
    st.header("Step 6: Results & Comparison")
    
    if cleaned_df is not None and original_df is not None:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original", len(original_df))
        with col2:
            st.metric("Cleaned", len(cleaned_df))
        with col3:
            st.metric("Removed", len(original_df) - len(cleaned_df))
        
        st.subheader("Cleaned Data Preview")
        st.dataframe(cleaned_df.head(20), use_container_width=True)
        
        st.download_button("Download Cleaned CSV", cleaned_df.to_csv(index=False), "cleaned_data.csv")
        
        if len(original_df.columns) > 0:
            st.subheader("Before & After Comparison")
            col_name = st.selectbox("Select Column", original_df.columns)
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Original**")
                st.dataframe(original_df[[col_name]].head(10))
            with col2:
                st.write("**Cleaned**")
                st.dataframe(cleaned_df[[col_name]].head(10))
    else:
        st.info("Cleaned data not available. Execute cleaning in Tab 5.")

st.markdown("---")
st.markdown("<center>DQ Portal v3.0 - Combined Best Features</center>", unsafe_allow_html=True)
