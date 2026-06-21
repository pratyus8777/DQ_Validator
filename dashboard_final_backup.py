"""
Enhanced DQ Dashboard - Assessment First, Then Cleansing
Workflow: Input Rules -> Profile & Assess -> Review -> Clean (on demand)
Features: AI-Powered Data Standardization with Custom Rule Definition
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
    /* Main styling */
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #f0f2f6;
        font-weight: 600;
        padding: 12px 20px;
        border-radius: 5px 5px 0 0;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #0066CC;
        color: white;
        border-radius: 5px 5px 0 0;
    }
    
    /* Phase boxes */
    .phase-box { 
        padding: 20px; 
        border-radius: 10px; 
        margin: 15px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .phase-1 { 
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-left: 5px solid #2196F3; 
    }
    .phase-2 { 
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        border-left: 5px solid #FF9800; 
    }
    .phase-3 { 
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        border-left: 5px solid #4CAF50; 
    }
    .phase-4 {
        background: linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%);
        border-left: 5px solid #9C27B0;
    }
    
    /* Rule input styling */
    .rule-input-box {
        background: linear-gradient(135deg, #E8F4F8 0%, #D0E8F2 100%);
        padding: 18px;
        border-radius: 8px;
        margin: 12px 0;
        border-left: 4px solid #0066CC;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Column header */
    .column-header {
        background: linear-gradient(135deg, #0066CC 0%, #0052A3 100%);
        color: white;
        padding: 12px 15px;
        border-radius: 5px;
        font-weight: bold;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Success cards */
    .success-card {
        background-color: #D4EDDA;
        border-left: 4px solid #28A745;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Info cards */
    .info-card {
        background-color: #D1ECF1;
        border-left: 4px solid #17A2B8;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Warning cards */
    .warning-card {
        background-color: #FFF3CD;
        border-left: 4px solid #FFC107;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Title styling */
    h1 {
        color: #0066CC;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    h2 {
        color: #0052A3;
        font-weight: 600;
        margin-top: 20px;
    }
    
    /* Divider */
    hr {
        margin: 20px 0;
        border: none;
        height: 2px;
        background: linear-gradient(to right, #0066CC, transparent);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏆 Data Quality Portal")
st.markdown("### Assessment First → Define Rules → Review → Clean")
st.markdown("**Modern DQ Workflow**: Profile & Assess → Define Rules → Review Report → Clean on Demand with Deduplication")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def sanitize_dataframe(df):
    """Convert numpy dtypes to standard Python types."""
    try:
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str)
        return df
    except Exception as e:
        st.warning(f"Could not sanitize dataframe: {e}")
        return df

@st.cache_data
def load_original_data():
    """Load original data"""
    try:
        original_files = sorted(glob.glob('output/Sample_Policy_Data_ORIGINAL_*.csv'))
        if original_files:
            return sanitize_dataframe(pd.read_csv(original_files[-1]))
        return sanitize_dataframe(pd.read_csv('data/Sample_Policy_Data.csv'))
    except Exception:
        return None

@st.cache_data
def load_cleaned_data():
    """Load cleaned data if available"""
    try:
        cleaned_files = sorted(glob.glob('output/Sample_Policy_Data_CLEANED_*.csv'))
        if cleaned_files:
            return sanitize_dataframe(pd.read_csv(cleaned_files[-1]))
    except Exception:
        pass
    return None

def save_cleansing_rules(rules_dict):
    """Save cleansing rules to JSON file"""
    try:
        rules_path = Path('output/cleansing_rules.json')
        with open(rules_path, 'w') as f:
            json.dump(rules_dict, f, indent=2)
        return rules_path
    except Exception as e:
        st.error(f"Failed to save rules: {e}")
        return None

def load_cleansing_rules():
    """Load cleansing rules from JSON file"""
    try:
        rules_file = Path('output/cleansing_rules.json')
        if rules_file.exists():
            with open(rules_file, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'pipeline_run' not in st.session_state:
    st.session_state.pipeline_run = None
if 'assessment_report' not in st.session_state:
    st.session_state.assessment_report = None
if 'custom_rules' not in st.session_state:
    st.session_state.custom_rules = {}
if 'cleansing_rules' not in st.session_state:
    st.session_state.cleansing_rules = load_cleansing_rules()

# Load data
original_df = load_original_data()
cleaned_df = load_cleaned_data()

# ============================================================================
# MAIN TABS
# ============================================================================

tabs = st.tabs([
    "1. Run Assessment",
    "2. Assessment Report",
    "3. Define Cleansing Rules",
    "4. Clean Data",
    "5. Results"
])

# ============================================================================
# TAB 1: RUN ASSESSMENT
# ============================================================================

with tabs[0]:
    st.header("Step 1: Run Assessment (Profile & Report)")
    st.markdown("This will analyze your data and generate an assessment report **WITHOUT cleaning**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Assessment Mode")
        assessment_mode = st.radio(
            "Choose assessment depth:",
            ["⚡ Fast (no LLM, ~2 sec)", "🧠 Full (with LLM, ~1+ min)"],
            index=0,
            key="assess_mode"
        )
        use_fast_mode = "Fast" in assessment_mode
    
    with col2:
        st.subheader("Mode Details")
        if use_fast_mode:
            st.info("✓ **Fast Mode**\n- Skip LLM rule interpretation\n- Quick profiling (~2 sec)")
        else:
            st.info("🧠 **Full Mode**\n- LLM interprets rules\n- Detailed analysis (~1+ min)")
    
    st.divider()
    
    if st.button("📊 RUN ASSESSMENT", use_container_width=True, key="assess_btn"):
        st.info("Running assessment...")
        
        rules_source = None
        if Path('temp_rules.csv').exists():
            rules_source = 'temp_rules.csv'
            st.write("Using uploaded CSV rules")
        elif Path('output/custom_rules.json').exists():
            rules_source = 'output/custom_rules.json'
            st.write("Using custom rules")
        else:
            st.write("Using standard DQ rules")
        
        try:
            if use_fast_mode:
                cmd = ["python", "assessment_first_pipeline.py", "--fast"]
            else:
                cmd = ["python", "assessment_first_pipeline.py"]
            
            if rules_source:
                cmd.extend(["--rules-file", rules_source])
            
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if proc.returncode == 0:
                st.markdown("<div class='success-card'>✨ <b>Assessment Complete!</b> All data profiled and violations detected.</div>", unsafe_allow_html=True)
                
                reports = sorted(Path('output').glob('Assessment_Report_*.json'), reverse=True)
                if reports:
                    with open(reports[0], 'r') as f:
                        st.session_state.assessment_report = json.load(f)
                    st.markdown(f"<div class='info-card'>📋 Report saved: <b>{reports[0].name}</b></div>", unsafe_allow_html=True)
            else:
                st.error("Assessment failed")
                st.error(proc.stderr)
        except Exception as e:
            st.error(f"Error: {e}")

# ============================================================================
# TAB 2: ASSESSMENT REPORT
# ============================================================================

with tabs[1]:
    st.header("Step 2: Review Assessment Report")
    
    st.markdown("""
    **Workflow**: 
    1. ✓ Assessment completed  
    2. → **Review violations and rules** (you are here)
    3. → Edit or add rules in Tab 3
    4. → Clean data in Tab 4
    """)
    st.divider()
    
    if st.session_state.assessment_report:
        report = st.session_state.assessment_report
        
        st.markdown("<div class='phase-box phase-2'>", unsafe_allow_html=True)
        st.subheader("Data Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Records", report.get('summary', {}).get('total_records', 'N/A'))
        with col2:
            st.metric("Columns", report.get('summary', {}).get('total_columns', 'N/A'))
        with col3:
            problem_cols = report.get('summary', {}).get('columns_with_issues', report.get('summary', {}).get('problem_columns', 0))
            st.metric("Problem Columns", problem_cols)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show Violations by Dimension
        st.subheader("Violations Detected (by Dimension)")
        try:
            violations_by_dim = report.get('violations_by_dimension', {})
            if violations_by_dim:
                for dimension, violations in violations_by_dim.items():
                    if violations:
                        col1, col2 = st.columns([2, 3])
                        with col1:
                            st.write(f"**{dimension}**")
                        with col2:
                            st.write(f"{len(violations)} issue types")
                        for viol in violations[:3]:  # Show first 3
                            st.write(f"  • {viol.get('column', 'N/A')}: {viol.get('type', 'Unknown')} ({viol.get('count', 0)} records)")
        except Exception as e:
            st.warning(f"Could not display violations by dimension: {e}")
        
        st.divider()
        
        # Show Violations by Column
        st.subheader("Violations by Column (sorted by count)")
        try:
            violations_by_col = report.get('violations_by_column', {})
            if violations_by_col:
                viol_data = [{'Column': col, 'Violation Count': count} for col, count in sorted(violations_by_col.items(), key=lambda x: x[1], reverse=True)]
                st.dataframe(pd.DataFrame(viol_data), use_container_width=True)
        except Exception as e:
            st.warning(f"Could not display violations by column: {e}")
        
        st.divider()
        
        # Show Column Profiles / Data Sheet
        st.subheader("Data Sheet - Column Profiles")
        
        try:
            columns_data = []
            for col, profile in report.get('column_profiles', {}).items():
                columns_data.append({
                    'Column': col,
                    'Type': profile.get('data_type', 'N/A'),
                    'Non-null %': f"{100 - profile.get('null_percentage', 0):.1f}%",
                    'Unique': profile.get('unique_values', 0),
                    'Sample': ', '.join(str(v) for v in profile.get('sample_values', [])[:2])
                })
            if columns_data:
                st.dataframe(pd.DataFrame(columns_data), use_container_width=True)
        except Exception as e:
            st.warning(f"Could not display column profiles: {e}")
        
        st.divider()
        
        st.subheader("Rules Sheet - Cleansing Rules to Apply")
        st.markdown("**Verify these rules** before cleaning. Edit or add new rules in Tab 3.")
        
        try:
            rules_data = []
            for col, rule in report.get('rules_for_cleaning', {}).items():
                if isinstance(rule, dict):
                    rules_data.append({'Column': col, 'Rule': rule.get('user_rule', 'N/A')})
                else:
                    rules_data.append({'Column': col, 'Rule': str(rule)})
            
            if rules_data:
                st.dataframe(pd.DataFrame(rules_data), use_container_width=True)
        except Exception as e:
            st.warning(f"Could not display rules: {e}")
        
        if report.get('data_quality_issues'):
            st.subheader("Data Quality Issues Detected")
            for issue in report['data_quality_issues']:
                st.warning(issue)
        
        st.download_button(
            "Download Full Report (JSON)",
            data=json.dumps(report, indent=2, default=str),
            file_name=f"Assessment_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            key="download_report"
        )
    else:
        st.info("Run assessment first to see the report")

# ============================================================================
# TAB 3: DEFINE CLEANSING RULES
# ============================================================================

with tabs[2]:
    st.markdown("### 🎯 Define Column-Specific Cleansing Rules")
    
    st.markdown("""
    **Workflow**:
    1. ✓ Assessment completed
    2. ✓ Reviewed violations and rules
    3. → **Define/Edit rules for each column** (you are here)
    4. → Clean data in Tab 4
    
    **How to use**: For each column below, see sample values and define how to clean/standardize them.
    You can write natural language rules like "Format as +23-XXXXX-XXXXX" or "Convert to uppercase".
    """)
    st.divider()
    
    st.markdown("""
    **Rule Examples**:
    - **Phone**: "Format as +23-XXXXX-XXXXX" → Converts to +23-49746-89883
    - **Email**: "Convert to uppercase" → Converts to JOHN70@EXAMPLE.COM
    - **Dates**: "Format as YYYY-MM-DD" → Converts mixed formats to standardized date
    - **Text**: "Trim and titlecase" → Removes whitespace and capitalizes properly
    """)
    The system will interpret these rules and apply them during data cleaning.
    """)
    
    if original_df is None:
        st.error("No data available. Please load data first.")
    else:
        # Organize columns by type
        date_cols = ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 
                     'Endorsement Effective Date', 'Cancellation Effective Date']
        contact_cols = ['Phone', 'Email']
        financial_cols = ['Premium Amount', 'Coverage Limit', 'Coverage Deductible', 'Agent Commission %']
        text_cols = ['Customer Name', 'Agent Name', 'Address', 'Policy Status', 'Line of Business']
        id_cols = ['Policy Number', 'Customer ID', 'Coverage ID', 'Agent ID', 'National ID']
        
        # Get available columns
        avail_dates = [c for c in date_cols if c in original_df.columns]
        avail_contact = [c for c in contact_cols if c in original_df.columns]
        avail_financial = [c for c in financial_cols if c in original_df.columns]
        avail_text = [c for c in text_cols if c in original_df.columns]
        avail_ids = [c for c in id_cols if c in original_df.columns]
        
        # Date Columns Section
        if avail_dates:
            st.subheader("📅 Date Column Standardization")
            for col in avail_dates:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.write("**Sample values:**")
                    samples = original_df[col].dropna().head(3).tolist()
                    for s in samples:
                        st.write(f"• {s}")
                
                with col2:
                    rule = st.text_input(
                        f"Rule for {col}",
                        value=st.session_state.cleansing_rules.get(col, ""),
                        placeholder="E.g., 'Convert to YYYY-MM-DD format'",
                        key=f"date_rule_{col}"
                    )
                    st.session_state.cleansing_rules[col] = rule
        
        # Contact Columns Section
        if avail_contact:
            st.markdown("### 📞 Phone & Contact Standardization")
            st.markdown("Define how you want phone numbers and contact information formatted", help="Examples: Format as +XX-XXXXX-XXXXX, Convert to lowercase")
            for col in avail_contact:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.write("**Sample values:**")
                    samples = original_df[col].dropna().head(3).tolist()
                    for s in samples:
                        st.write(f"• {s}")
                
                with col2:
                    if col == 'Phone':
                        placeholder = "E.g., 'Format as +1-XXX-XXX-XXXX'"
                    else:
                        placeholder = "E.g., 'Convert to lowercase'"
                    
                    rule = st.text_input(
                        f"Rule for {col}",
                        value=st.session_state.cleansing_rules.get(col, ""),
                        placeholder=placeholder,
                        key=f"contact_rule_{col}"
                    )
                    st.session_state.cleansing_rules[col] = rule
        
        # Financial Columns Section
        if avail_financial:
            st.markdown("### 💰 Financial Data Standardization")
            st.markdown("Define formatting rules for currency, amounts, and percentages", help="Examples: Format as currency, Remove decimals, Validate positive values")
            for col in avail_financial:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.write("**Sample values:**")
                    samples = original_df[col].dropna().head(3).astype(str).tolist()
                    for s in samples:
                        st.write(f"• {s}")
                
                with col2:
                    rule = st.text_input(
                        f"Rule for {col}",
                        value=st.session_state.cleansing_rules.get(col, ""),
                        placeholder="E.g., 'Format as currency with 2 decimals'",
                        key=f"financial_rule_{col}"
                    )
                    st.session_state.cleansing_rules[col] = rule
        
        # Text Columns Section
        if avail_text:
            st.markdown("### 🔤 Text Field Standardization")
            st.markdown("Define how text fields should be formatted and cleaned", help="Examples: Trim, Titlecase, Remove special characters")
            for col in avail_text:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.write("**Sample values:**")
                    samples = original_df[col].dropna().head(3).astype(str).tolist()
                    for s in samples:
                        st.write(f"• {s[:30]}")
                
                with col2:
                    rule = st.text_input(
                        f"Rule for {col}",
                        value=st.session_state.cleansing_rules.get(col, ""),
                        placeholder="E.g., 'Trim and convert to title case'",
                        key=f"text_rule_{col}"
                    )
                    st.session_state.cleansing_rules[col] = rule
        
        # ID Columns Section
        if avail_ids:
            st.subheader("🆔 ID Field Standardization")
            for col in avail_ids:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.write("**Sample values:**")
                    samples = original_df[col].dropna().head(3).astype(str).tolist()
                    for s in samples:
                        st.write(f"• {s}")
                
                with col2:
                    rule = st.text_input(
                        f"Rule for {col}",
                        value=st.session_state.cleansing_rules.get(col, ""),
                        placeholder="E.g., 'Convert to uppercase'",
                        key=f"id_rule_{col}"
                    )
                    st.session_state.cleansing_rules[col] = rule
        
        st.markdown("---")
        
        # Action buttons - improved UI
        st.markdown("### 📤 Save & Apply Rules")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Rules", use_container_width=True, key="save_rules_btn"):
                rules_file = save_cleansing_rules(st.session_state.cleansing_rules)
                if rules_file:
                    st.markdown("""
                    <div class='success-card'>
                    <b>Rules Saved Successfully!</b>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"File: **{rules_file.name}**")
        
        with col2:
            if st.button("📋 Preview All Rules", use_container_width=True, key="preview_rules_btn"):
                rules_with_values = {k: v for k, v in st.session_state.cleansing_rules.items() if v and v.strip()}
                st.json(rules_with_values)
        
        with col3:
            if st.button("🔄 Clear All Rules", use_container_width=True, key="clear_rules_btn"):
                st.session_state.cleansing_rules = {}
                st.rerun()

# ============================================================================
# TAB 4: CLEAN DATA
# ============================================================================

with tabs[3]:
    st.header("Step 4: Clean Data (On Demand)")
    
    st.markdown("""
    **Workflow**:
    1. ✓ Assessment completed
    2. ✓ Reviewed violations and rules
    3. ✓ Defined/edited rules
    4. → **Execute cleaning with deduplication** (you are here)
    5. → View results in Tab 5
    """)
    st.divider()
    
    st.markdown("""
    This will apply your defined cleansing rules to transform and deduplicate the data.
    **WARNING**: Cleansing cannot be undone. Make sure the rules are correct.
    """)
    
    if st.session_state.assessment_report:
        report = st.session_state.assessment_report
        
        st.markdown("<div class='phase-box phase-3'>", unsafe_allow_html=True)
        st.subheader("Cleansing Rules Summary")
        
        active_rules = {k: v for k, v in st.session_state.cleansing_rules.items() if v and v.strip()}
        
        if active_rules:
            st.write(f"**{len(active_rules)} custom cleansing rules will be applied:**")
            for col, rule in active_rules.items():
                st.write(f"- **{col}**: {rule}")
        else:
            st.warning("⚠️ No custom cleansing rules defined. Define rules in Tab 3 before cleaning.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Cleansing Process")
            st.markdown("""
            1. **Apply Custom Rules**: Transform data per your specifications
            2. **Standardize Formats**: Dates, phone, ID fields, etc.
            3. **Remove Duplicates**: Deduplicate records based on key fields
            4. **Handle Missing Values**: Apply smart defaults
            5. **Generate Output**: Save cleaned dataset
            """)
        
        with col2:
            st.markdown("### What Gets Applied")
            if active_rules:
                st.markdown("✅ Custom column rules")
            st.markdown("""
            ✅ Format standardization
            ✅ Duplicate removal
            ✅ Whitespace trimming
            ✅ Case standardization
            ✅ Missing value handling
            ✅ Data validation
            """)
        
        st.divider()
        
        # Options for deduplication
        st.subheader("Deduplication Settings")
        
        dedup_method = st.radio(
            "Choose deduplication method:",
            [
                "Keep first occurrence",
                "Keep last occurrence",
                "Remove all duplicates"
            ],
            index=0,
            key="dedup_method"
        )
        
        if st.button("🧹 CLEAN & DEDUPLICATE MY DATA NOW", use_container_width=True, key="clean_btn"):
            st.info("Saving rules and starting cleansing process...")
            
            try:
                # Save cleansing rules to be used by the pipeline
                rules_file = save_cleansing_rules(st.session_state.cleansing_rules)
                if rules_file:
                    st.write(f"✓ Saved {len(active_rules)} rules")
                
                st.info("Running cleansing pipeline...")
                
                # Run cleansing with rules
                cmd = [
                    "python", "assessment_first_pipeline.py", 
                    "--clean",
                    "--dedup-method", dedup_method.lower().replace(" ", "-")
                ]
                
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if proc.returncode == 0:
                    st.markdown("""
                    <div class='success-card'>
                    🎯 <b>Cleaning Complete!</b> Data has been standardized and deduplicated.
                    </div>
                    """, unsafe_allow_html=True)
                    st.cache_data.clear()
                    
                    cleaned_files = sorted(Path('output').glob('Sample_Policy_Data_CLEANED_*.csv'), reverse=True)
                    if cleaned_files:
                        st.markdown(f"""
                        <div class='info-card'>
                        💾 Cleaned data saved: <b>{cleaned_files[0].name}</b>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        df_cleaned = pd.read_csv(cleaned_files[0])
                        
                        # Show metrics
                        st.metric("Records after cleaning & deduplication", len(df_cleaned))
                        
                        st.subheader("Cleaned Data Preview")
                        st.dataframe(df_cleaned.head(10), use_container_width=True)
                        
                        st.download_button(
                            "📥 Download Cleaned CSV",
                            data=df_cleaned.to_csv(index=False),
                            file_name=cleaned_files[0].name,
                            key="download_cleaned"
                        )
                else:
                    st.error("❌ Cleansing failed")
                    if proc.stderr:
                        st.error("Error details:")
                        st.code(proc.stderr)
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("⚠️ Complete assessment first (Tab 1) before cleaning")

# ============================================================================
# TAB 5: RESULTS
# ============================================================================

with tabs[4]:
    st.header("Step 5: Results & Comparison")
    
    st.markdown("""
    **Workflow Complete!**
    1. ✓ Assessment completed
    2. ✓ Reviewed violations and rules
    3. ✓ Defined/edited rules
    4. ✓ Executed cleaning with deduplication
    5. → **Review results** (you are here)
    """)
    st.divider()
    
    if cleaned_df is not None and original_df is not None:
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
        st.dataframe(cleaned_df.head(20), use_container_width=True)
        
        csv = cleaned_df.to_csv(index=False)
        st.download_button("📥 Download Cleaned Data", csv, "cleaned_data.csv", mime="text/csv", key="download_final")
        
        st.markdown("---")
        st.subheader("Before & After Comparison")
        
        if len(original_df.columns) > 0:
            column_to_compare = st.selectbox("Select column to compare:", original_df.columns, key="compare_col")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Original Data**")
                st.dataframe(original_df[[column_to_compare]].head(10), use_container_width=True)
            
            with col2:
                st.write("**Cleaned Data**")
                st.dataframe(cleaned_df[[column_to_compare]].head(10), use_container_width=True)
    else:
        st.info("⏳ Cleaned data not yet available. Execute cleaning in Tab 5.")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("<center>DQ Portal v2.0 - Assessment First, Clean on Demand | AI-Powered Data Standardization</center>", unsafe_allow_html=True)
