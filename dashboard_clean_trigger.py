"""
Enhanced DQ Dashboard with User-Triggered Cleaning
Shows comprehensive profiling and assessment first, then allows user to trigger cleaning
"""

import streamlit as st
import pandas as pd
import json
import glob
import subprocess
import os
from pathlib import Path

st.set_page_config(page_title="Data Quality Dashboard", layout="wide")

# Custom CSS for better styling
st.markdown("""
    <style>
    .cleanup-button {
        background-color: #FF6B6B;
        color: white;
        padding: 20px;
        text-align: center;
        font-size: 24px;
        border-radius: 5px;
        margin: 20px 0;
    }
    .violation-badge {
        background-color: #FFE66D;
        color: #000;
        padding: 10px 15px;
        border-radius: 5px;
        font-weight: bold;
    }
    .analysis-box {
        background-color: #F0F3F4;
        padding: 20px;
        border-radius: 5px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Data Quality Assessment & Cleaning Portal")
st.markdown("*Professional Data Quality Management System*")
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

def run_cleaning():
    """Execute the data cleaning pipeline"""
    try:
        st.info("🔄 Starting data cleaning process...")
        cmd = ["python", "comprehensive_dq_pipeline.py"]  # Run without --assessment-only
        proc = subprocess.run(cmd, cwd=os.getcwd(), capture_output=True, text=True, timeout=300)
        
        if proc.returncode == 0:
            st.success("✅ Data cleaning completed successfully!")
            st.balloons()
            # Clear cache to reload data
            st.cache_data.clear()
            return True
        else:
            st.error(f"❌ Cleaning failed with error:\n{proc.stderr}")
            return False
    except subprocess.TimeoutExpired:
        st.error("⏱️ Cleaning process timed out")
        return False
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return False

# Load data
analysis = load_analysis_data()
original_df = load_original_data()
cleaned_df = load_cleaned_data()

if original_df is None or analysis is None:
    st.error("📭 No analysis data found! Please run the pipeline first.")
    st.info("Run: `python comprehensive_dq_pipeline.py --assessment-only` to generate analysis")
    st.stop()

# Navigation
tabs = st.tabs([
    "📈 Analysis Overview",
    "📊 Detailed Violations",
    "🔍 Original Data",
    "✨ Data Quality Scorecard",
    "🧹 Cleaning Control",
    "📋 Column Analysis"
])

# TAB 1: Analysis Overview
with tabs[0]:
    st.header("Data Quality Analysis Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📌 Total Records", analysis['total_records'])
    with col2:
        st.metric("📊 Total Columns", analysis['total_columns'])
    with col3:
        st.metric("⚠️ Records with Issues", analysis['violation_count'])
    with col4:
        pct_bad = (analysis['violation_count'] / analysis['total_records'] * 100) if analysis['total_records'] > 0 else 0
        st.metric("% Data Quality", f"{100-pct_bad:.1f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Violations by Severity")
        severity_data = analysis['severity_breakdown']
        severity_df = pd.DataFrame([
            {"Severity": "🔴 CRITICAL", "Count": severity_data['critical']},
            {"Severity": "🟠 HIGH", "Count": severity_data['high']},
            {"Severity": "🟡 MEDIUM", "Count": severity_data['medium']},
            {"Severity": "🟢 LOW", "Count": severity_data['low']}
        ])
        st.dataframe(severity_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("Violations by Dimension")
        violation_counts = {k: len(v) for k, v in analysis['violations'].items()}
        dim_df = pd.DataFrame([
            {"Dimension": k, "Violations": v} 
            for k, v in sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)
        ])
        st.dataframe(dim_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("Key Findings")
    
    # Show key issues
    critical = analysis['severity_breakdown']['critical']
    high = analysis['severity_breakdown']['high']
    total = sum(analysis['severity_breakdown'].values())
    
    st.info(f"""
    **Summary**: Your dataset contains **{total} violations** across **{analysis['violation_count']} records**:
    - 🔴 **{critical} Critical** violations (must fix)
    - 🟠 **{high} High** violations (should fix)
    - 🟡 **{analysis['severity_breakdown']['medium']} Medium** violations
    - 🟢 **{analysis['severity_breakdown']['low']} Low** violations
    """)

# TAB 2: Detailed Violations
with tabs[1]:
    st.header("Detailed Violation Analysis")
    
    selected_dimension = st.selectbox(
        "Select Dimension to Analyze",
        list(analysis['violations'].keys())
    )
    
    violations = analysis['violations'][selected_dimension]
    st.subheader(f"{selected_dimension.upper()}: {len(violations)} violations")
    
    if violations:
        # Show all violations with pagination
        items_per_page = 20
        total_pages = (len(violations) + items_per_page - 1) // items_per_page
        page_num = st.selectbox("Page", range(1, total_pages + 1))
        
        start_idx = (page_num - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(violations))
        
        violations_subset = violations[start_idx:end_idx]
        violations_df = pd.DataFrame(violations_subset)
        st.dataframe(violations_df, use_container_width=True)
    else:
        st.success("✅ No violations in this dimension!")

# TAB 3: Original Data
with tabs[2]:
    st.header("Original Data Preview")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric("Records", len(original_df))
    with col2:
        st.metric("Columns", len(original_df.columns))
    
    st.dataframe(original_df, use_container_width=True)
    
    # Download button
    csv = original_df.to_csv(index=False)
    st.download_button("📥 Download Original Data", csv, "original_data.csv", "text/csv")

# TAB 4: Data Quality Scorecard
with tabs[3]:
    st.header("Column Quality Scorecard")
    
    col_quality = analysis['column_quality']
    quality_list = []
    
    for col, metrics in col_quality.items():
        quality_list.append({
            "Column": col,
            "Quality Score": f"{metrics['quality_score']:.1f}/100",
            "Violations": metrics['violation_count'],
            "Affected Rows": metrics['affected_rows']
        })
    
    quality_df = pd.DataFrame(quality_list).sort_values("Column")
    st.dataframe(quality_df, use_container_width=True, hide_index=True)

# TAB 5: Cleaning Control (Main Feature!)
with tabs[4]:
    st.header("🧹 Data Cleaning Control")
    
    st.markdown("""
    ### Two-Step Cleaning Process
    
    1. **Analysis Phase** (COMPLETED ✅): Comprehensive data quality analysis with LLM enhancement
    2. **Cleaning Phase** (PENDING ⏳): Click below to execute cleansing rules
    """)
    
    st.markdown("---")
    
    # Show current status
    if cleaned_df is not None:
        st.success("✅ Cleaned data is available")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Records", len(original_df))
        with col2:
            st.metric("Cleaned Records", len(cleaned_df))
        with col3:
            st.metric("Records Modified", len(original_df) - len(cleaned_df))
    else:
        st.warning("⏳ Cleaning has not been executed yet")
    
    st.markdown("---")
    st.markdown("### Ready to Clean Your Data?")
    
    st.markdown(f"""
    The analysis phase has identified:
    - **{analysis['violation_count']}** records with quality issues
    - **{sum(analysis['severity_breakdown'].values())}** total violations
    - **{analysis['severity_breakdown']['critical']}** critical issues requiring immediate attention
    
    Click the button below to execute the automated cleaning process:
    """)
    
    # Main cleaning button
    if st.button("🔄 CLEAN MY DATA NOW", key="clean_button", use_container_width=True):
        success = run_cleaning()
        if success:
            st.rerun()
    
    st.markdown("---")
    st.info("""
    **What happens during cleaning:**
    1. Invalid values are corrected or removed
    2. Duplicate records are deduplicated
    3. Missing values are handled
    4. Consistency rules are applied
    5. Cleaned data is saved to output folder
    """)

# TAB 6: Column Analysis
with tabs[5]:
    st.header("Detailed Column Analysis")
    
    col_name = st.selectbox("Select Column", original_df.columns)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"Column: {col_name}")
        st.write(f"**Data Type**: {original_df[col_name].dtype}")
        st.write(f"**Non-Null Count**: {original_df[col_name].notna().sum()}")
        st.write(f"**Null Count**: {original_df[col_name].isna().sum()}")
        st.write(f"**Unique Values**: {original_df[col_name].nunique()}")
    
    with col2:
        if col_name in col_quality:
            metrics = col_quality[col_name]
            st.subheader("Quality Metrics")
            st.write(f"**Quality Score**: {metrics['quality_score']:.1f}/100")
            st.write(f"**Violations**: {metrics['violation_count']}")
            st.write(f"**Affected Rows**: {metrics['affected_rows']}")
    
    st.markdown("---")
    st.subheader("Sample Values")
    sample_vals = original_df[col_name].dropna().head(20).tolist()
    st.write(sample_vals)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><strong>Data Quality Pipeline v1.0</strong></p>
    <p>Powered by LLM-Enhanced Profiling | Production Ready</p>
</div>
""", unsafe_allow_html=True)
