"""
Enhanced DQ Dashboard with Column-Specific Cleansing Rules
Users can define custom cleansing rules for each column via LLM interpretation
"""

import streamlit as st
import pandas as pd
import json
import glob
import subprocess
import os
from pathlib import Path

st.set_page_config(page_title="Advanced Data Quality Portal", layout="wide")

st.markdown("""
    <style>
    .rule-input-box {
        background-color: #E8F4F8;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        border-left: 4px solid #0066CC;
    }
    .column-header {
        background-color: #0066CC;
        color: white;
        padding: 10px;
        border-radius: 3px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .analysis-box {
        background-color: #F0F3F4;
        padding: 20px;
        border-radius: 5px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Advanced Data Quality & Cleansing Portal")
st.markdown("*AI-Powered Data Standardization with Custom Rule Definition*")
st.markdown("---")

# Helper functions
def sanitize_dataframe(df):
    """Convert numpy dtypes to standard Python types."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str)
    return df

@st.cache_data
def load_analysis_data():
    """Load the latest comprehensive analysis"""
    analysis_files = sorted(glob.glob('output/Detailed_Analysis_*.json'))
    if analysis_files:
        with open(analysis_files[-1], 'r') as f:
            return json.load(f)
    return None

@st.cache_data
def load_original_data():
    """Load original data"""
    original_files = sorted(glob.glob('output/Sample_Policy_Data_ORIGINAL_*.csv'))
    if original_files:
        return sanitize_dataframe(pd.read_csv(original_files[-1]))
    return None

@st.cache_data
def load_cleaned_data():
    """Load cleaned data if available"""
    cleaned_files = sorted(glob.glob('output/Sample_Policy_Data_CLEANED_*.csv'))
    if cleaned_files:
        return sanitize_dataframe(pd.read_csv(cleaned_files[-1]))
    return None

def save_cleansing_rules(rules_dict):
    """Save cleansing rules to JSON file"""
    rules_path = Path('output/cleansing_rules.json')
    with open(rules_path, 'w') as f:
        json.dump(rules_dict, f, indent=2)
    return rules_path

def run_cleaning_with_rules():
    """Execute data cleaning with custom rules"""
    try:
        st.info("Cleaning data with custom rules...")
        cmd = ["python", "quick_cleanse.py"]
        proc = subprocess.run(cmd, cwd=os.getcwd(), capture_output=True, text=True, timeout=300)
        
        if proc.returncode == 0:
            st.success("Data cleaning completed successfully!")
            st.balloons()
            st.cache_data.clear()
            return True
        else:
            st.error(f"Cleaning failed:\n{proc.stderr}")
            return False
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False

# Load data
analysis = load_analysis_data()
original_df = load_original_data()
cleaned_df = load_cleaned_data()

if original_df is None or analysis is None:
    st.error("📭 No analysis data found!")
    st.info("Run: `python comprehensive_dq_pipeline.py --assessment-only` first")
    st.stop()

# Navigation
tabs = st.tabs([
    "📈 Overview",
    "🎯 Define Cleansing Rules",
    "📊 Violations",
    "🔍 Data Preview",
    "🧹 Execute Cleaning",
    "📋 Results"
])

# TAB 1: Overview
with tabs[0]:
    st.header("Data Quality Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📌 Records", analysis['total_records'])
    with col2:
        st.metric("📊 Columns", analysis['total_columns'])
    with col3:
        st.metric("⚠️ Issues", analysis['violation_count'])
    with col4:
        pct = 100 - (analysis['violation_count'] / analysis['total_records'] * 100)
        st.metric("Quality %", f"{pct:.1f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("By Severity")
        severity_df = pd.DataFrame([
            {"Severity": "🔴 CRITICAL", "Count": analysis['severity_breakdown']['critical']},
            {"Severity": "🟠 HIGH", "Count": analysis['severity_breakdown']['high']},
            {"Severity": "🟡 MEDIUM", "Count": analysis['severity_breakdown']['medium']},
        ])
        st.dataframe(severity_df, hide_index=True, use_container_width=True)
    
    with col2:
        st.subheader("By Dimension")
        dim_df = pd.DataFrame([
            {"Dimension": k, "Count": len(v)} 
            for k, v in analysis['violations'].items()
        ])
        st.dataframe(dim_df.sort_values("Count", ascending=False), hide_index=True, use_container_width=True)

# TAB 2: Define Cleansing Rules (Main Feature!)
with tabs[1]:
    st.header("🎯 Define Column-Specific Cleansing Rules")
    
    st.markdown("""
    Define custom cleansing and standardization rules for each column.
    The LLM will interpret these rules and apply them during data cleaning.
    """)
    
    # Initialize cleansing rules in session state
    if 'cleansing_rules' not in st.session_state:
        # Try to load from JSON file
        rules_file = Path('output/cleansing_rules.json')
        if rules_file.exists():
            try:
                with open(rules_file, 'r') as f:
                    st.session_state.cleansing_rules = json.load(f)
            except:
                st.session_state.cleansing_rules = {}
        else:
            st.session_state.cleansing_rules = {}
    
    # Create tabs for rule categories
    rule_tabs = st.tabs(["📅 Date Columns", "📞 Phone/Contact", "💰 Financial", "🔤 Text Fields", "🆔 ID Fields", "⚙️ Custom Rules"])
    
    # Date Columns
    with rule_tabs[0]:
        st.subheader("Date Column Standardization")
        
        date_cols = ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 
                     'Endorsement Effective Date', 'Cancellation Effective Date']
        available_date_cols = [col for col in date_cols if col in original_df.columns]
        
        for col in available_date_cols:
            st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 3])
            
            with col1:
                st.write("**Sample values:**")
                samples = original_df[col].dropna().head(3).tolist()
                for s in samples:
                    st.write(f"• {s}")
            
            with col2:
                rule = st.text_input(
                    f"Cleansing rule for {col}",
                    value=st.session_state.cleansing_rules.get(col, ""),
                    placeholder="E.g., 'Convert all dates to YYYY-MM-DD format' or 'Parse dates from various formats and standardize'",
                    key=f"rule_{col}",
                    label_visibility="collapsed"
                )
                st.session_state.cleansing_rules[col] = rule
                
                if rule:
                    st.caption(f"✓ Rule set: {rule[:50]}...")
    
    # Phone/Contact Columns
    with rule_tabs[1]:
        st.subheader("Phone & Contact Standardization")
        
        contact_cols = ['Phone', 'Email']
        available_contact = [col for col in contact_cols if col in original_df.columns]
        
        for col in available_contact:
            st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 3])
            
            with col1:
                st.write("**Sample values:**")
                samples = original_df[col].dropna().head(3).tolist()
                for s in samples:
                    st.write(f"• {s}")
            
            with col2:
                if col == 'Phone':
                    rule = st.text_input(
                        f"Cleansing rule for {col}",
                        value=st.session_state.cleansing_rules.get(col, ""),
                        placeholder="E.g., 'Format as E.164: +1-XXX-XXX-XXXX' or 'Standardize US phone numbers'",
                        key=f"rule_{col}",
                        label_visibility="collapsed"
                    )
                else:  # Email
                    rule = st.text_input(
                        f"Cleansing rule for {col}",
                        value=st.session_state.cleansing_rules.get(col, ""),
                        placeholder="E.g., 'Convert to lowercase and validate format'",
                        key=f"rule_{col}",
                        label_visibility="collapsed"
                    )
                
                st.session_state.cleansing_rules[col] = rule
                
                if rule:
                    st.caption(f"✓ Rule set: {rule[:50]}...")
    
    # Financial Columns
    with rule_tabs[2]:
        st.subheader("Financial Data Standardization")
        
        financial_cols = ['Premium Amount', 'Coverage Limit', 'Coverage Deductible', 'Agent Commission %']
        available_financial = [col for col in financial_cols if col in original_df.columns]
        
        for col in available_financial:
            st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 3])
            
            with col1:
                st.write("**Sample values:**")
                samples = original_df[col].dropna().head(3).astype(str).tolist()
                for s in samples:
                    st.write(f"• {s}")
            
            with col2:
                rule = st.text_input(
                    f"Cleansing rule for {col}",
                    value=st.session_state.cleansing_rules.get(col, ""),
                    placeholder="E.g., 'Format as currency with 2 decimals' or 'Ensure values are positive'",
                    key=f"rule_{col}",
                    label_visibility="collapsed"
                )
                st.session_state.cleansing_rules[col] = rule
                
                if rule:
                    st.caption(f"✓ Rule set: {rule[:50]}...")
    
    # Text Fields
    with rule_tabs[3]:
        st.subheader("Text Field Standardization")
        
        text_cols = ['Customer Name', 'Agent Name', 'Address', 'Policy Status', 'Line of Business']
        available_text = [col for col in text_cols if col in original_df.columns]
        
        for col in available_text:
            st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 3])
            
            with col1:
                st.write("**Sample values:**")
                samples = original_df[col].dropna().head(3).astype(str).tolist()
                for s in samples:
                    st.write(f"• {s[:30]}")
            
            with col2:
                rule = st.text_input(
                    f"Cleansing rule for {col}",
                    value=st.session_state.cleansing_rules.get(col, ""),
                    placeholder="E.g., 'Trim whitespace and convert to title case' or 'Remove special characters'",
                    key=f"rule_{col}",
                    label_visibility="collapsed"
                )
                st.session_state.cleansing_rules[col] = rule
                
                if rule:
                    st.caption(f"✓ Rule set: {rule[:50]}...")
    
    # ID Fields
    with rule_tabs[4]:
        st.subheader("ID Field Standardization")
        
        id_cols = ['Policy Number', 'Customer ID', 'Coverage ID', 'Agent ID', 'National ID']
        available_ids = [col for col in id_cols if col in original_df.columns]
        
        for col in available_ids:
            st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 3])
            
            with col1:
                st.write("**Sample values:**")
                samples = original_df[col].dropna().head(3).astype(str).tolist()
                for s in samples:
                    st.write(f"• {s}")
            
            with col2:
                rule = st.text_input(
                    f"Cleansing rule for {col}",
                    value=st.session_state.cleansing_rules.get(col, ""),
                    placeholder="E.g., 'Convert to uppercase and remove spaces' or 'Validate format: XXX-XXXXX'",
                    key=f"rule_{col}",
                    label_visibility="collapsed"
                )
                st.session_state.cleansing_rules[col] = rule
                
                if rule:
                    st.caption(f"✓ Rule set: {rule[:50]}...")
    
    # Custom Rules for other columns
    with rule_tabs[5]:
        st.subheader("Custom Rules for Other Columns")
        
        processed_cols = set()
        for tab_cols in [['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 
                          'Endorsement Effective Date', 'Cancellation Effective Date'],
                         ['Phone', 'Email'],
                         ['Premium Amount', 'Coverage Limit', 'Coverage Deductible', 'Agent Commission %'],
                         ['Customer Name', 'Agent Name', 'Address', 'Policy Status', 'Line of Business'],
                         ['Policy Number', 'Customer ID', 'Coverage ID', 'Agent ID', 'National ID']]:
            processed_cols.update([c for c in tab_cols if c in original_df.columns])
        
        other_cols = [col for col in original_df.columns if col not in processed_cols]
        
        if other_cols:
            st.write("**Remaining columns:**")
            for col in other_cols:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                
                rule = st.text_input(
                    f"Rule for {col}",
                    value=st.session_state.cleansing_rules.get(col, ""),
                    placeholder="Enter custom cleansing rule...",
                    key=f"rule_{col}",
                    label_visibility="collapsed"
                )
                st.session_state.cleansing_rules[col] = rule
        else:
            st.info("All columns covered in previous tabs")
    
    st.markdown("---")
    
    # Save and preview rules
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Rules", use_container_width=True):
            rules_file = save_cleansing_rules(st.session_state.cleansing_rules)
            st.success(f"✅ Rules saved to {rules_file.name}")
    
    with col2:
        if st.button("📋 Preview All Rules", use_container_width=True):
            st.json(st.session_state.cleansing_rules)
    
    with col3:
        if st.button("🔄 Clear All Rules", use_container_width=True):
            st.session_state.cleansing_rules = {}
            st.rerun()

# TAB 3: Violations
with tabs[2]:
    st.header("Detected Violations")
    
    selected_dim = st.selectbox("Dimension", list(analysis['violations'].keys()))
    violations = analysis['violations'][selected_dim]
    
    st.info(f"**{len(violations)} violations in {selected_dim} dimension**")
    
    if violations:
        page_size = 15
        total_pages = (len(violations) + page_size - 1) // page_size
        page = st.selectbox("Page", range(1, total_pages + 1))
        
        start = (page - 1) * page_size
        end = min(start + page_size, len(violations))
        
        viol_df = pd.DataFrame(violations[start:end])
        st.dataframe(viol_df, use_container_width=True)

# TAB 4: Data Preview
with tabs[3]:
    st.header("Data Preview")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Original Data")
    with col2:
        st.metric("Records", len(original_df))
    
    st.dataframe(original_df, use_container_width=True)

# TAB 5: Execute Cleaning
with tabs[4]:
    st.header("🧹 Execute Cleaning with Custom Rules")
    
    st.info(f"""
    **Ready to clean your data:**
    - Records: {original_df.shape[0]}
    - Issues detected: {analysis['violation_count']}
    - Violations: {sum(len(v) for v in analysis['violations'].values())}
    - Custom rules defined: {len([r for r in st.session_state.cleansing_rules.values() if r])}
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Cleansing Process")
        st.markdown("""
        1. **Read Rules**: Load all defined cleansing rules
        2. **LLM Interpretation**: Use LLM to understand rule intentions
        3. **Apply Standardization**: Format dates, phones, IDs, etc.
        4. **Execute Rules**: Apply column-specific cleansing
        5. **Remove Duplicates**: Deduplicate records
        6. **Generate Output**: Save cleaned data
        """)
    
    with col2:
        st.markdown("### What Gets Applied")
        st.markdown("""
        ✅ Date standardization  
        ✅ Phone number formatting  
        ✅ Email validation & cleanup  
        ✅ Name/ID standardization  
        ✅ Custom LLM-interpreted rules  
        ✅ Duplicate removal  
        ✅ Missing value handling  
        ✅ Format validation  
        """)
    
    st.markdown("---")
    st.subheader("📋 Rule Preview")
    
    # Show which rules will be applied
    with st.expander("View rules that will be applied", expanded=False):
        rules_to_apply = {k: v for k, v in st.session_state.cleansing_rules.items() if v and v.strip()}
        if rules_to_apply:
            st.json(rules_to_apply)
            st.info(f"💡 {len(rules_to_apply)} rule(s) will be applied")
        else:
            st.warning("⚠️ No rules defined yet. Define rules in the previous tab.")
    
    # Show sample data transformation preview
    with st.expander("Preview transformation examples", expanded=False):
        if original_df is not None and rules_to_apply:
            st.write("**Sample transformations that will be applied:**")
            
            preview_data = {}
            from agents.standardization_rules import CustomCleansingRuleParser
            
            for col in list(rules_to_apply.keys())[:3]:  # Show first 3 rules
                if col not in original_df.columns:
                    continue
                    
                rule_text = rules_to_apply[col]
                sample_values = original_df[col].dropna().head(2).tolist()
                
                preview_data[col] = {
                    'Rule': rule_text,
                    'Sample Before': sample_values
                }
                
                # Try to show what it will become
                try:
                    parsed_rule = CustomCleansingRuleParser.parse_custom_rule(rule_text)
                    transformed = [CustomCleansingRuleParser.apply_custom_rule(v, parsed_rule) for v in sample_values]
                    preview_data[col]['Sample After'] = transformed
                except:
                    preview_data[col]['Sample After'] = ['(transformation preview unavailable)']
            
            for col, info in preview_data.items():
                st.write(f"**{col}**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Before:**")
                    for val in info['Sample Before']:
                        st.write(f"  - {val}")
                with col2:
                    st.write("**After:**")
                    for val in info['Sample After']:
                        st.write(f"  - {val}")
                st.write(f"*Rule: {info['Rule']}*")
                st.divider()
    
    st.markdown("---")
    
    if st.button("🚀 START CLEANING NOW", use_container_width=True, key="clean_main"):
        # Save rules before executing
        save_cleansing_rules(st.session_state.cleansing_rules)
        success = run_cleaning_with_rules()
        if success:
            st.rerun()

# TAB 6: Results
with tabs[5]:
    st.header("Cleaning Results")
    
    if cleaned_df is not None:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Original Records", len(original_df))
        with col2:
            st.metric("Cleaned Records", len(cleaned_df))
        with col3:
            removed = len(original_df) - len(cleaned_df)
            st.metric("Records Removed", removed)
        
        st.markdown("---")
        st.subheader("Cleaned Data Preview")
        st.dataframe(cleaned_df, use_container_width=True)
        
        # Download button
        csv = cleaned_df.to_csv(index=False)
        st.download_button("📥 Download Cleaned Data", csv, "cleaned_data.csv")
    else:
        st.info("⏳ Cleaned data not yet available. Execute cleaning in the previous tab.")

st.markdown("---")
st.markdown("<div style='text-align:center'><p><strong>Advanced DQ Portal v2.0</strong> | LLM-Powered Data Standardization</p></div>", unsafe_allow_html=True)
