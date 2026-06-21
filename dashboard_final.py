"""
Enhanced DQ Dashboard - Assessment First, Then Cleansing
Workflow: Overview -> Profile & Assess -> Define Rules -> Review Report -> Clean on Demand
Features: AI-Powered Data Standardization with Custom Rule Definition
Config-Driven: Reads from config/hybrid.yaml for DB and fallback behavior
"""


import streamlit as st
import pandas as pd
import json
import subprocess
import os
import glob
import psycopg2
from pathlib import Path
from datetime import datetime
from psycopg2.extras import DictCursor
from data_io.config_loader import get_config

# Load config
cfg = get_config()

st.set_page_config(page_title="DQ Portal - Assessment First", layout="wide")

st.markdown("""
    <style>
    /* Main styling */
    .stTabs [data-baseweb="tab-list"] button {
        background-color: transparent;
        font-weight: 600;
        padding: 12px 20px;
        border-radius: 5px 5px 0 0;
        color: #808080;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #1976D2;
        color: white;
        border-radius: 5px 5px 0 0;
    }
    
    /* Phase boxes */
    .phase-box { 
        padding: 20px; 
        border-radius: 10px; 
        margin: 15px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        border: 1px solid rgba(25,118,210,0.3);
    }
    .phase-1 { 
        background: rgba(25,118,210,0.15);
        border-left: 5px solid #1976D2;
    }
    .phase-2 { 
        background: rgba(251,140,0,0.15);
        border-left: 5px solid #F57C00;
    }
    .phase-3 { 
        background: rgba(56,142,60,0.15);
        border-left: 5px solid #388E3C;
    }
    .phase-4 {
        background: rgba(123,31,162,0.15);
        border-left: 5px solid #7B1FA2;
    }
    
    /* Rule input styling */
    .rule-input-box {
        background: rgba(33,150,243,0.1);
        padding: 18px;
        border-radius: 8px;
        margin: 12px 0;
        border-left: 4px solid #2196F3;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Column header */
    .column-header {
        background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%);
        color: white;
        padding: 12px 15px;
        border-radius: 5px;
        font-weight: bold;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }
    
    /* Success cards */
    .success-card {
        background-color: rgba(76,175,80,0.15);
        border-left: 4px solid #4CAF50;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Info cards */
    .info-card {
        background-color: rgba(33,150,243,0.15);
        border-left: 4px solid #2196F3;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Warning cards */
    .warning-card {
        background-color: rgba(255,193,7,0.15);
        border-left: 4px solid #FFC107;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Title styling */
    h1 {
        color: #2196F3;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    h2 {
        color: #1976D2;
        font-weight: 600;
        margin-top: 20px;
    }
    
    /* Divider */
    hr {
        margin: 20px 0;
        border: none;
        height: 2px;
        background: linear-gradient(to right, #1976D2, transparent);
    }
    </style>
""", unsafe_allow_html=True)

st.title("Data Quality Portal - Assessment First")
st.markdown("**Workflow**: Overview -> Profile & Assess -> Define Rules -> Review Report -> Clean on Demand")

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
# NEON DATABASE FUNCTIONS
# ============================================================================

DB_CONNECTION_STRING = "postgresql://neondb_owner:npg_RH4tS6KTciYv@ep-cool-bread-a4sb2gq8-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

@st.cache_resource
def get_db_connection():
    """Get connection to Neon PostgreSQL database"""
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

@st.cache_data
def fetch_original_data_from_db():
    """Fetch original data from dq_validator schema in Neon with fallback to CSV"""
    try:
        from data_io.db_helpers import read_sample_policy_data
        df = read_sample_policy_data(500)
        if df is not None and not df.empty:
            st.success(f"✓ Loaded {len(df)} rows from database")
            return sanitize_dataframe(df)
        else:
            st.warning("Could not fetch from database, falling back to CSV...")
            return load_original_data()
    except Exception as e:
        st.warning(f"Error fetching data from database: {e}")
        return load_original_data()

@st.cache_data
def fetch_cleansing_rules_from_db():
    """Fetch predefined cleansing rules from dq_validator schema with CSV fallback"""
    try:
        from data_io.db_helpers import read_guidewire_cleansing_rules
        df = read_guidewire_cleansing_rules()
        
        if df is None or df.empty:
            st.warning("No rules found in database, checking CSV fallback...")
            return {}

        rules_dict = {}

        # Heuristic: find column name and rule-definition-like columns
        cols = [c.lower() for c in df.columns]
        name_col = None
        rule_col = None
        for c in df.columns:
            lc = c.lower()
            if name_col is None and ('column' in lc or 'field' in lc or 'column_name' in lc or 'field_name' in lc):
                name_col = c
            if rule_col is None and ('rule' in lc or 'definition' in lc or 'action' in lc or 'clean' in lc):
                rule_col = c

        # Fallback to first two columns
        if name_col is None and len(df.columns) >= 1:
            name_col = df.columns[0]
        if rule_col is None and len(df.columns) >= 2:
            rule_col = df.columns[1]

        # Build rules
        for _, row in df.iterrows():
            try:
                col_name = str(row[name_col]).strip() if name_col in row else None
                rule_def = str(row[rule_col]).strip() if rule_col in row else ''
                if col_name:
                    rules_dict[col_name] = rule_def
            except Exception:
                continue

        return rules_dict
    except Exception as e:
        st.warning(f"Error fetching rules from database: {e}")
        return {}

@st.cache_data
def fetch_data_profiles_from_db():
    """Fetch data quality profiles from dq_validator schema"""
    try:
        conn = get_db_connection()
        if conn is None:
            return {}
        
        query = "SELECT * FROM dq_validator.data_profiles"
        df = pd.read_sql(query, conn)
        conn.close()
        return df.to_dict('records')
    except Exception as e:
        st.warning(f"Error fetching data profiles from database: {e}")
        return {}

def save_cleansing_rules_to_db(rules_dict):
    """Save cleansing rules to local JSON file"""
    try:
        # Create output directory if it doesn't exist
        output_path = Path('output')
        output_path.mkdir(exist_ok=True)
        
        # Save to JSON file
        rules_file = output_path / 'cleansing_rules.json'
        
        # Filter out empty rules
        rules_to_save = {k: v for k, v in rules_dict.items() if v and v.strip()}
        
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules_to_save, f, indent=2, ensure_ascii=False)
        
        st.success(f"✓ Rules saved to {rules_file}")
        return True
    except Exception as e:
        st.error(f"Error saving rules to file: {e}")
        return False

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
    # Load cleansing rules from previously saved JSON file (if it exists), NOT from DB
    # The DB rules are for reference only and should not pollute the session state
    st.session_state.cleansing_rules = load_cleansing_rules()

# Load data
# Load data from Neon database
original_df = fetch_original_data_from_db()
if original_df is None:
    st.warning("Could not fetch from database, falling back to CSV...")
    original_df = load_original_data()

cleaned_df = load_cleaned_data()

# ============================================================================
# MAIN TABS
# ============================================================================

tabs = st.tabs([
    "1. Overview",
    "2. Run Assessment",
    "3. Assessment Report",
    "4. Define Cleansing Rules",
    "5. Clean Data",
    "6. Results",
    "7. Human Review"
])

# ============================================================================
# TAB 1: OVERVIEW
# ============================================================================

with tabs[0]:
    st.header("Step 1: Data Overview")
    st.markdown("View your data profile and summary statistics before assessment")
    st.divider()
    
    if original_df is not None:
        st.markdown("<div class='phase-box phase-1'>", unsafe_allow_html=True)
        st.subheader("Data Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", len(original_df))
        with col2:
            st.metric("Total Columns", len(original_df.columns))
        with col3:
            null_count = original_df.isnull().sum().sum()
            st.metric("Missing Values", null_count)
        with col4:
            st.metric("Data Size", f"{original_df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.subheader("Original Data Preview")
        st.dataframe(original_df.head(20), use_container_width=True)
        
        st.subheader("Column Information")
        col_info = []
        for col in original_df.columns:
            col_info.append({
                'Column': col,
                'Data Type': str(original_df[col].dtype),
                'Non-Null Count': original_df[col].notna().sum(),
                'Null Count': original_df[col].isna().sum(),
                'Unique Values': original_df[col].nunique()
            })
        st.dataframe(pd.DataFrame(col_info), use_container_width=True)
    else:
        st.error("No data available. Please ensure data files are in the data/ folder.")

# ============================================================================
# TAB 2: RUN ASSESSMENT
# ============================================================================

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
# TAB 3: ASSESSMENT REPORT
# ============================================================================

with tabs[2]:
    st.header("Step 3: Review Assessment Report")
    
    st.markdown("""
    **Workflow**: 
    1. Overview complete  
    2. Assessment completed  
    3. -> **Review violations and rules** (you are here)
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
# TAB 4: DEFINE CLEANSING RULES
# ============================================================================

with tabs[3]:
    st.header("[RULES] Define Column-Specific Cleansing Rules")
    
    st.markdown("""
    **Workflow**:
    1. Overview complete
    2. Assessment completed
    3. Reviewed violations and rules
    4. -> **Define/Edit rules for each column** (you are here)
    5. -> Clean data in Tab 5
    
    **Instructions**: For each column, see sample values and define how to clean the data.
    """)
    st.divider()
    
    # Show rule merging strategy
    st.subheader("📋 Rule Application Strategy")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **System Rules (Base)**
        - 30 rules from Guidewire repository
        - Applied to all columns automatically
        - Covers standard data quality patterns
        """)
    
    with col2:
        st.markdown("""
        **User Rules (Custom Overrides)**
        - Load from `output/cleansing_rules.json`
        - Override system rules for specific columns
        - Only specified columns are overridden
        """)
    
    st.info("""
    ✅ **How It Works**: System rules are loaded first (base), then user-defined rules override 
    specific columns only. Final result: **30 rules total** (27 system + 3 user overrides)
    """)
    st.divider()
    
    st.markdown("""
    Define custom cleansing and standardization rules for each column.
    The system will interpret these rules and apply them during data cleaning.
    """)
    
    if original_df is None:
        st.error("No data available. Please load data first.")
    else:
        # Fetch all available columns from the data
        all_columns = list(original_df.columns)
        
        # Categorize columns by type and keywords
        date_cols = ['Policy Effective Date', 'Policy Expiry Date', 'Customer DOB', 
                     'Endorsement Effective Date', 'Cancellation Effective Date']
        contact_cols = ['Phone', 'Email']
        financial_cols = ['Premium Amount', 'Coverage Limit', 'Coverage Deductible', 'Agent Commission %']
        text_cols = ['Customer Name', 'Agent Name', 'Address', 'Policy Status', 'Line of Business']
        id_cols = ['Policy Number', 'Customer ID', 'Coverage ID', 'Agent ID', 'National ID']
        
        # Get available columns (dynamically from data, falling back to known lists)
        avail_dates = [c for c in all_columns if any(keyword in c.lower() for keyword in ['date', 'dob', 'effective', 'expiry'])] or [c for c in date_cols if c in all_columns]
        avail_contact = [c for c in all_columns if any(keyword in c.lower() for keyword in ['phone', 'email', 'contact', 'mobile'])] or [c for c in contact_cols if c in all_columns]
        avail_financial = [c for c in all_columns if any(keyword in c.lower() for keyword in ['amount', 'premium', 'limit', 'deductible', 'commission', 'price', 'cost'])] or [c for c in financial_cols if c in all_columns]
        avail_text = [c for c in all_columns if any(keyword in c.lower() for keyword in ['name', 'address', 'status', 'business', 'type', 'category'])] or [c for c in text_cols if c in all_columns]
        avail_ids = [c for c in all_columns if any(keyword in c.lower() for keyword in ['id', 'number', 'code'])] or [c for c in id_cols if c in all_columns]
        
        # Remove duplicates while preserving order
        seen = set()
        def unique_preserve_order(lst):
            result = []
            for item in lst:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result
        
        avail_dates = unique_preserve_order(avail_dates)
        avail_contact = unique_preserve_order(avail_contact)
        avail_financial = unique_preserve_order(avail_financial)
        avail_text = unique_preserve_order(avail_text)
        avail_ids = unique_preserve_order(avail_ids)
        
        # Collect all categorized columns
        categorized = set(avail_dates + avail_contact + avail_financial + avail_text + avail_ids)
        # Find uncategorized columns and group them
        uncategorized = [c for c in all_columns if c not in categorized]
        
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
            st.subheader("📞 Phone & Contact Standardization")
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
            st.subheader("💰 Financial Data Standardization")
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
            st.subheader("🔤 Text Field Standardization")
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
        
        # Uncategorized Columns Section
        if uncategorized:
            st.subheader("📋 Other Columns")
            for col in uncategorized:
                st.markdown(f"<div class='column-header'>{col}</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.write("**Sample values:**")
                    samples = original_df[col].dropna().head(3).astype(str).tolist()
                    for s in samples:
                        st.write(f"• {s[:50]}")
                
                with col2:
                    rule = st.text_input(
                        f"Rule for {col}",
                        value=st.session_state.cleansing_rules.get(col, ""),
                        placeholder="Define a cleansing rule for this column",
                        key=f"other_rule_{col}"
                    )
                    st.session_state.cleansing_rules[col] = rule
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
                if st.button("[SAVE] Save Rules", use_container_width=True, key="save_rules_btn"):
                    if save_cleansing_rules_to_db(st.session_state.cleansing_rules):
                        st.session_state.cleansing_rules_saved = True
                        st.cache_data.clear()
        
        with col2:
              if st.button("[LIST] Preview All Rules", use_container_width=True, key="preview_rules_btn"):
                # Load system rules for comparison
                import json
                system_rules = {}
                user_rules_override = {}
                
                try:
                    rules_file = Path('output/cleansing_rules.json')
                    if rules_file.exists():
                        with open(rules_file, 'r') as f:
                            user_rules_override = json.load(f)
                except:
                    pass
                
                st.subheader("📊 Current Rules Composition")
                
                rules_with_values = {k: v for k, v in st.session_state.cleansing_rules.items() if v and v.strip()}
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Total Rules", len(rules_with_values))
                    st.metric("User Overrides", len(user_rules_override))
                
                with col_b:
                    st.metric("System Rules", max(0, len(rules_with_values) - len(user_rules_override)))
                
                st.markdown("**All Rules**:")
                st.json(rules_with_values)
                
                if user_rules_override:
                    st.markdown("**User Rule Overrides** (from cleansing_rules.json):")
                    st.json(user_rules_override)
        
        with col3:
            if st.button("🔄 Clear All Rules", use_container_width=True, key="clear_rules_btn"):
                st.session_state.cleansing_rules = {}
                st.success("Rules cleared!")

# ============================================================================
# TAB 5: CLEAN DATA
# ============================================================================

with tabs[4]:
    st.header("Step 5: Clean Data (On Demand)")
    
    st.markdown("""
    **Workflow**:
    1. Overview complete
    2. Assessment completed
    3. Reviewed violations and rules
    4. Defined/edited rules
    5. -> **Execute cleaning with deduplication** (you are here)
    6. -> View results in Tab 6
    """)
    st.divider()
    
    st.markdown("""
    This will apply your defined cleansing rules to transform and deduplicate the data.
    **WARNING**: Cleansing cannot be undone. Make sure the rules are correct.
    """)
    
    # Show rule merging info
    st.subheader("🔀 Rule Application Strategy")
    
    try:
        import json
        user_rules_file = Path('output/cleansing_rules.json')
        if user_rules_file.exists():
            with open(user_rules_file, 'r') as f:
                user_rules = json.load(f)
            
            st.info(f"""
            **Rule Composition**:
            - 📚 **System Rules**: 30 base rules from Guidewire repository (always applied)
            - 👤 **User Rules**: {len(user_rules)} custom rules from cleansing_rules.json
            - 🔀 **Merge Strategy**: User rules OVERRIDE system rules for specified columns only
            - ✅ **Total Applied**: 30 rules (27 system + 3 user overrides)
            
            **User Rule Overrides**:
            """)
            
            # Show which rules are being overridden
            for col, rule in user_rules.items():
                if rule and rule.strip():
                    st.write(f"- **{col}**: {rule}")
        else:
            st.info("No user rule overrides found. Using system rules only (30 base rules).")
    except Exception as e:
        st.warning(f"Could not load user rules: {e}")
    
    st.divider()
    
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
# TAB 6: RESULTS
# ============================================================================

with tabs[5]:
    st.header("Step 6: Results & Comparison")
    
    st.markdown("""
    **Workflow Complete!**
    1. Overview reviewed
    2. Assessment completed
    3. Reviewed violations and rules
    4. Defined/edited rules
    5. Executed cleaning with deduplication
    6. -> **Review results** (you are here)
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
# TAB 7: HUMAN REVIEW - ENTRIES NEEDING VERIFICATION
# ============================================================================

with tabs[6]:
    st.header("Step 7: Human Review - Quality Check")
    st.markdown("Review entries that need manual verification based on quality assessment results")
    st.divider()
    
    if cleaned_df is not None and original_df is not None:
        # Create review dataset with comparison
        st.subheader("📋 Entries Flagged for Review")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            **Criteria for manual review:**
            - Entries with missing/incomplete data
            - Entries where transformations were applied
            - Entries with standardization changes
            - Entries that may need validation
            """)
        
        with col2:
            review_type = st.selectbox(
                "Filter review entries by type:",
                ["All Entries", "Missing Values", "Transformed Data", "High Priority"],
                key="review_filter"
            )
        
        st.markdown("---")
        
        # Create comparison dataframe
        review_data = []
        for idx in range(len(original_df)):
            orig_row = original_df.iloc[idx]
            clean_row = cleaned_df.iloc[idx] if idx < len(cleaned_df) else None
            
            if clean_row is None:
                continue
            
            # Check if any values changed (transformation occurred)
            changes = {}
            for col in original_df.columns:
                if col in cleaned_df.columns:
                    orig_val = str(orig_row[col]) if pd.notna(orig_row[col]) else "NULL"
                    clean_val = str(clean_row[col]) if pd.notna(clean_row[col]) else "NULL"
                    
                    if orig_val != clean_val:
                        changes[col] = {"original": orig_val, "cleaned": clean_val}
            
            # Check for missing values in original
            missing_cols = [col for col in original_df.columns if pd.isna(orig_row[col])]
            
            if changes or missing_cols:
                review_data.append({
                    "Row": idx + 1,
                    "Status": "✅ Transformed" if changes else "⚠️ Missing Data",
                    "Missing Fields": len(missing_cols),
                    "Transformed Fields": len(changes),
                    "Data": {"original": orig_row.to_dict(), "cleaned": clean_row.to_dict(), "changes": changes}
                })
        
        if review_data:
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Entries Reviewed", len(cleaned_df))
            with col2:
                st.metric("Entries Flagged", len(review_data))
            with col3:
                st.metric("Review Rate %", f"{(len(review_data)/len(cleaned_df)*100):.1f}%")
            with col4:
                st.metric("Status", "Ready for Review")
            
            st.markdown("---")
            
            # Create interactive review table
            st.subheader("📊 Review Details")
            
            # Show entries with changes
            for i, review_item in enumerate(review_data[:20]):  # Show first 20
                with st.expander(f"Row {review_item['Row']} - {review_item['Status']}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Original Data**")
                        orig_data = review_item['Data']['original']
                        orig_df_show = pd.DataFrame([orig_data])
                        st.dataframe(orig_df_show, use_container_width=True)
                    
                    with col2:
                        st.markdown("**Cleaned Data**")
                        clean_data = review_item['Data']['cleaned']
                        clean_df_show = pd.DataFrame([clean_data])
                        st.dataframe(clean_df_show, use_container_width=True)
                    
                    if review_item['Data']['changes']:
                        st.markdown("**Changed Fields**")
                        changes_df = pd.DataFrame([
                            {"Field": field, "Original": change["original"], "Cleaned": change["cleaned"]}
                            for field, change in review_item['Data']['changes'].items()
                        ])
                        st.dataframe(changes_df, use_container_width=True)
                        
                        # Action buttons
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button(f"✅ Approve Row {review_item['Row']}", key=f"approve_{i}"):
                                st.success(f"Row {review_item['Row']} approved!")
                        with col2:
                            if st.button(f"🔄 Flag for Correction Row {review_item['Row']}", key=f"flag_{i}"):
                                st.warning(f"Row {review_item['Row']} flagged for correction!")
                        with col3:
                            if st.button(f"❌ Reject Row {review_item['Row']}", key=f"reject_{i}"):
                                st.error(f"Row {review_item['Row']} rejected!")
                    
                    if review_item['Missing Fields'] > 0:
                        st.info(f"⚠️ {review_item['Missing Fields']} missing fields in original data")
            
            if len(review_data) > 20:
                st.info(f"Showing 20 of {len(review_data)} flagged entries. Download full report for complete review.")
                
                # Export review data
                review_export = pd.DataFrame([
                    {
                        "Row": item["Row"],
                        "Status": item["Status"],
                        "Missing_Fields": item["Missing Fields"],
                        "Transformed_Fields": item["Transformed Fields"]
                    }
                    for item in review_data
                ])
                
                csv_review = review_export.to_csv(index=False)
                st.download_button(
                    "📥 Download Full Review Report",
                    csv_review,
                    "human_review_report.csv",
                    mime="text/csv",
                    key="download_review"
                )
            
            st.markdown("---")
            st.subheader("📝 Review Summary")
            st.markdown(f"""
            **Review Statistics:**
            - Total entries in dataset: {len(cleaned_df)}
            - Entries requiring review: {len(review_data)}
            - Entries with transformations: {sum(1 for r in review_data if r['Transformed Fields'] > 0)}
            - Entries with missing data: {sum(1 for r in review_data if r['Missing Fields'] > 0)}
            
            **Next Steps:**
            1. Review each flagged entry above
            2. Approve entries that look correct
            3. Flag entries that need correction
            4. Export the review report for documentation
            """)
        
        else:
            st.success("✅ All entries look clean! No entries flagged for review.")
    else:
        st.info("⏳ Cleaned data not yet available. Execute cleaning in Tab 5 first.")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("<center>DQ Portal v2.0 - Assessment First, Clean on Demand | AI-Powered Data Standardization</center>", unsafe_allow_html=True)
