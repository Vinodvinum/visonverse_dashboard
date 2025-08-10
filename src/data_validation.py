# visionverse_dashboard/src/data_validation.py
import streamlit as st
import pandas as pd

def render_data_validation(df):
    st.title("🧪 Data Validation Checks")

    st.markdown("### Missing or Invalid Entries")
    issues = df[df['Cuboids'].isna() | (df['Cuboids'] <= 0)]

    if issues.empty:
        st.success("✅ No missing or invalid cuboid counts detected.")
    else:
        st.warning(f"⚠️ Found {len(issues)} issues in cuboid entries.")
        st.dataframe(issues)

    st.markdown("### Outliers (Above 2000 Cuboids)")
    outliers = df[df['Cuboids'] > 2000]

    if not outliers.empty:
        st.error(f"🚨 {len(outliers)} potential outliers detected.")
        st.dataframe(outliers)
    else:
        st.success("✅ No cuboid count outliers found.")