"""
Enhanced DQ Dashboard - Assessment First, Then Cleansing
Workflow: Input Rules -> Profile & Assess -> Review -> Clean (on demand)
"""

import streamlit as st
import pandas as pd
import json
import subprocess
import os
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="DQ Portal - Assessment First", layout="wide")

st.markdown("""
    <style>
    .phase-box { padding: 15px; border-radius: 5px; margin: 10px 0; }
    .phase-1 { background-color: #E3F2FD; border-left: 5px solid #2196F3; }
    .phase-2 { background-color: #FFF3E0; border-left: 5px solid #FF9800; }
    .phase-3 { background-color: #E8F5E9; border-left: 5px solid #4CAF50; }
    </style>
""", unsafe_allow_html=True)

st.title("Data Quality Portal - Assessment First")
st.markdown("**Workflow**: Input Rules → Profile & Assess → Review Report → Clean on Demand")

# Session state initialization
if 'pipeline_run' not in st.session_state:
    st.session_state.pipeline_run = None
if 'assessment_report' not in st.session_state:
    st.session_state.assessment_report = None
if 'custom_rules' not in st.session_state:
    st.session_state.custom_rules = {}

# Tabs
tabs = st.tabs([
    "1. Input Rules",
    "2. Run Assessment",
    "3. Assessment Report",
    "4. Clean Data"
])

# TAB 1: INPUT RULES
with tabs[0]:
    st.header("Step 1: Input Cleansing Rules")
    
    st.markdown("""
    Provide rules in one of three ways:
    1. **Upload CSV** with columns: Column, Rule
    2. **Enter Custom Rules** in text boxes for each column
    3. **Use Standard Rules** (default if nothing provided)
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Option A: Upload Rules CSV")
        uploaded_file = st.file_uploader("Upload rules CSV (columns: Column, Rule)", type=['csv'])
        if uploaded_file:
            rules_df = pd.read_csv(uploaded_file)
            
            # Validate CSV format
            if len(rules_df.columns) < 2:
                st.error("CSV must have at least 2 columns")
            else:
                st.write("Rules to be applied:")
                st.dataframe(rules_df)
                
                # Standardize column names if needed
                if 'Column' not in rules_df.columns:
                    rules_df.rename(columns={rules_df.columns[0]: 'Column', rules_df.columns[1]: 'Rule'}, inplace=True)
                
                # Save to temp location
                rules_path = Path('temp_rules.csv')
                rules_df.to_csv(rules_path, index=False)
                st.success(f"Rules loaded: {len(rules_df)} rules")
    
    with col2:
        st.subheader("Option B: Custom Rules")
        st.write("Enter rule for each column:")
        
        # Load original data to get column names
        df = pd.read_csv('data/Sample_Policy_Data.csv')
        
        # Show key columns for input
        key_columns = [
            'Policy Effective Date', 'Policy Expiry Date', 'Customer DOB',
            'Phone', 'Email', 'Customer Name', 'Policy Number', 'Customer ID'
        ]
        
        for col in key_columns:
            if col in df.columns:
                rule = st.text_input(
                    f"Rule for '{col}'",
                    value=st.session_state.custom_rules.get(col, ""),
                    key=f"rule_{col}"
                )
                if rule:
                    st.session_state.custom_rules[col] = rule
    
    # Save custom rules
    if st.button("Save Rules for Assessment"):
        if st.session_state.custom_rules:
            rules_json = Path('output/custom_rules.json')
            with open(rules_json, 'w') as f:
                json.dump(st.session_state.custom_rules, f, indent=2)
            st.success(f"Saved {len(st.session_state.custom_rules)} custom rules")
        else:
            st.info("No custom rules entered. Standard rules will be used.")

# TAB 2: RUN ASSESSMENT
with tabs[1]:
    st.header("Step 2: Run Assessment (Profile & Report)")
    st.markdown("This will analyze your data and generate an assessment report **WITHOUT cleaning**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Assessment Mode")
        assessment_mode = st.radio(
            "Choose assessment depth:",
            ["⚡ Fast (no LLM, ~2 sec)", "🧠 Full (with LLM, ~1+ min)"],
            index=0,
            help="Fast: Skip LLM for speed. Full: Use LLM to interpret rules deeply."
        )
        use_fast_mode = "Fast" in assessment_mode
    
    with col2:
        st.subheader("Mode Details")
        if use_fast_mode:
            st.info("✓ **Fast Mode**\n- Skip LLM rule interpretation\n- Skip per-column LLM analysis\n- Quick profiling (~2 sec)")
        else:
            st.info("🧠 **Full Mode**\n- LLM interprets each rule\n- LLM analyzes each column\n- Detailed analysis (~1+ min)")
    
    st.divider()
    
    if st.button("📊 RUN ASSESSMENT", use_container_width=True, key="assess_btn"):
        st.info("Running assessment...")
        
        # Determine which rules to use
        rules_source = None
        if Path('temp_rules.csv').exists():
            rules_source = 'temp_rules.csv'
            st.write("Using uploaded CSV rules")
        elif Path('output/custom_rules.json').exists():
            rules_source = 'output/custom_rules.json'
            st.write("Using custom rules")
        else:
            st.write("Using standard DQ rules")
        
        # Run assessment
        try:
            # Run assessment in selected mode
            if use_fast_mode:
                cmd = ["python", "assessment_first_pipeline.py", "--fast"]
            else:
                cmd = ["python", "assessment_first_pipeline.py"]
            
            if rules_source:
                cmd.extend(["--rules-file", rules_source])
            
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if proc.returncode == 0:
                st.success("Assessment complete!")
                st.balloons()
                
                # Find the latest assessment report
                reports = sorted(Path('output').glob('Assessment_Report_*.json'), reverse=True)
                if reports:
                    with open(reports[0], 'r') as f:
                        st.session_state.assessment_report = json.load(f)
                    st.info(f"Report saved: {reports[0].name}")
            else:
                st.error("Assessment failed")
                st.error(proc.stderr)
        except Exception as e:
            st.error(f"Error: {e}")

# TAB 3: ASSESSMENT REPORT
with tabs[2]:
    st.header("Step 3: Review Assessment Report")
    
    if st.session_state.assessment_report:
        report = st.session_state.assessment_report
        
        # Summary
        st.markdown("<div class='phase-box phase-2'>", unsafe_allow_html=True)
        st.subheader("Data Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Records", report['summary']['total_records'])
        with col2:
            st.metric("Columns", report['summary']['total_columns'])
        with col3:
            st.metric("Problem Columns", report['summary']['columns_with_issues'])
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Column Profiles
        st.subheader("Column Profiles")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            columns_data = []
            for col, profile in report['column_profiles'].items():
                columns_data.append({
                    'Column': col,
                    'Type': profile['data_type'],
                    'Non-null %': f"{100 - profile['null_percentage']:.1f}%",
                    'Unique': profile['unique_values']
                })
            st.dataframe(pd.DataFrame(columns_data), use_container_width=True)
        
        # Rules
        st.subheader("Rules for Cleaning")
        st.markdown("""
        These rules WILL be applied when you click "Clean My Data":
        """)
        
        rules_data = []
        for col, rule in report.get('rules_for_cleaning', {}).items():
            if isinstance(rule, dict):
                rules_data.append({
                    'Column': col,
                    'Rule': rule.get('user_rule', 'N/A')
                })
            else:
                rules_data.append({
                    'Column': col,
                    'Rule': rule
                })
        
        if rules_data:
            st.dataframe(pd.DataFrame(rules_data), use_container_width=True)
        
        # DQ Issues
        if report.get('data_quality_issues'):
            st.subheader("Data Quality Issues Detected")
            for issue in report['data_quality_issues']:
                st.warning(issue)
        
        # Download report
        st.download_button(
            "Download Full Report (JSON)",
            data=json.dumps(report, indent=2, default=str),
            file_name=f"Assessment_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
    
    else:
        st.info("Run assessment first to see the report")

# TAB 4: CLEAN DATA
with tabs[3]:
    st.header("Step 4: Clean Data (On Demand)")
    st.markdown("""
    This will apply the rules defined in the assessment to actually transform the data.
    **WARNING**: Cleansing cannot be undone. Make sure the assessment report is correct.
    """)
    
    if st.session_state.assessment_report:
        report = st.session_state.assessment_report
        
        st.markdown("<div class='phase-box phase-3'>", unsafe_allow_html=True)
        st.subheader("Cleansing Will Apply:")
        
        rules_summary = []
        for col, rule in report.get('rules_for_cleaning', {}).items():
            if isinstance(rule, dict):
                rules_summary.append(f"- **{col}**: {rule.get('user_rule', 'N/A')}")
            else:
                rules_summary.append(f"- **{col}**: {rule}")
        
        st.markdown("\n".join(rules_summary) if rules_summary else "No rules to apply")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.button("CLEAN MY DATA NOW", use_container_width=True, key="clean_btn"):
            st.warning("Cleansing in progress...")
            
            # Run cleansing via pipeline
            try:
                cmd = ["python", "assessment_first_pipeline.py", "--clean"]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if proc.returncode == 0:
                    st.success("Data cleaning completed!")
                    st.balloons()
                    
                    # Find cleaned file
                    cleaned_files = sorted(Path('output').glob('Sample_Policy_Data_CLEANED_*.csv'), reverse=True)
                    if cleaned_files:
                        st.info(f"Cleaned data saved: {cleaned_files[0].name}")
                        
                        # Show preview
                        df_cleaned = pd.read_csv(cleaned_files[0])
                        st.subheader("Cleaned Data Preview")
                        st.dataframe(df_cleaned.head(10), use_container_width=True)
                        
                        # Download button
                        st.download_button(
                            "Download Cleaned CSV",
                            data=df_cleaned.to_csv(index=False),
                            file_name=cleaned_files[0].name
                        )
                else:
                    st.error("Cleansing failed")
                    st.error(proc.stderr)
            except Exception as e:
                st.error(f"Error: {e}")
    
    else:
        st.warning("Complete assessment first before cleaning")

st.markdown("---")
st.markdown("<center>DQ Portal v2.0 - Assessment First, Clean on Demand</center>", unsafe_allow_html=True)
