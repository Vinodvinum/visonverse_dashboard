# visionverse_dashboard/streamlit_app.py
import streamlit as st
import os
import pandas as pd

from src.data_loader import load_team_data
from src.performance_dashboard import render_dashboard
from src.weekly_report_generator import render_weekly_report
from src.data_validation import render_data_validation

st.set_page_config(page_title="VisionVerse Dashboard", layout="wide")

role_map = {
    'Thashvi': 'Maker', 'Sushma': 'Editor', 'Jyothi': 'Maker', 'Deepika': 'Maker',
    'Nisarga': 'Maker', 'Shilpa': 'Maker', 'Chandu M': 'Maker', 'Ramesh S': 'Editor',
    'Dhanushree S': 'Maker', 'Shivukumar': 'Editor', 'Praveen': 'Maker',
    'Bhanushekar': 'Editor', 'Danny S': 'Maker', 'Abhina': 'Editor',
    'Priyanka J': 'Editor', 'Nayana R M': 'Maker', 'Sneha K M': 'Maker',
    'Abhishek': 'Editor', 'Mohammad': 'Editor', 'Priyapragathi': 'Maker'
}

DATA_PATH = "data/daily_cuboids.csv"
if os.path.exists(DATA_PATH):
    df = load_team_data(DATA_PATH, role_map)
else:
    st.error("Dataset not found. Please add data/daily_cuboids.csv")
    st.stop()

st.sidebar.title("📊 VisionVerse Dashboard")
page = st.sidebar.radio("Go to", [
    "Home", "Performance Dashboard", "Weekly Report", "Data Validation"
])

if page == "Home":
    st.title("👁️ VisionVerse Annotation Dashboard")
    st.markdown("""
Welcome to the VisionVerse QA Dashboard.

### 🡩‍🛫 Roles:
- **Makers** must deliver **650 cuboids/day** with **≥80% quality**
- **Editors** must deliver **1200 cuboids/day** with **≥95% quality**

Upload your latest daily CSV in the `data/` folder and explore real-time performance.
""")

elif page == "Performance Dashboard":
    render_dashboard(df)

elif page == "Weekly Report":
    render_weekly_report(df)

elif page == "Data Validation":
    render_data_validation(df)


# visionverse_dashboard/src/data_loader.py
import pandas as pd

def load_team_data(file_path, role_map):
    df = pd.read_csv(file_path, skiprows=1)
    df = df[~df['Name'].isin(['TOTAL', 'DEFICIT'])]

    df_long = df.melt(id_vars=['Name', 'Rename'], var_name='Date', value_name='Cuboids')
    df_long['Cuboids'] = pd.to_numeric(df_long['Cuboids'], errors='coerce')
    df_long = df_long.dropna(subset=['Cuboids'])

    df_long['Role'] = df_long['Rename'].map(role_map)
    df_long = df_long.dropna(subset=['Role'])

    return df_long


# visionverse_dashboard/src/performance_dashboard.py
import streamlit as st
import altair as alt
import pandas as pd

def render_dashboard(df):
    st.title("📈 Annotator Performance Overview")

    role = st.selectbox("Select Role", ["All", "Maker", "Editor"])

    if role != "All":
        df = df[df["Role"] == role]

    target = 650 if role == "Maker" else 1200 if role == "Editor" else None

    summary = df.groupby('Rename')['Cuboids'].sum().reset_index()
    summary.columns = ['Annotator', 'Total Cuboids']

    if target:
        summary['Target Met'] = summary['Total Cuboids'] >= target
    else:
        summary['Target Met'] = False

    chart = alt.Chart(summary).mark_bar().encode(
        x='Annotator:N',
        y='Total Cuboids:Q',
        color='Target Met:N',
        tooltip=['Annotator', 'Total Cuboids']
    ).properties(width=700)

    st.altair_chart(chart, use_container_width=True)
    st.dataframe(summary)


# visionverse_dashboard/src/weekly_report_generator.py
import streamlit as st
import pandas as pd
import altair as alt

def render_weekly_report(df):
    st.title("📅 Weekly Summary Report")

    role = st.selectbox("Filter by Role", ["All", "Maker", "Editor"])
    if role != "All":
        df = df[df['Role'] == role]

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    summary = df.groupby(['Date', 'Role']).agg({
        'Cuboids': ['sum', 'mean', 'count']
    }).reset_index()
    summary.columns = ['Date', 'Role', 'Total Cuboids', 'Average per Annotator', 'Entries']

    st.markdown("### 📊 Daily Trend")
    line_chart = alt.Chart(summary).mark_line(point=True).encode(
        x='Date:T',
        y='Total Cuboids:Q',
        color='Role:N',
        tooltip=['Date:T', 'Total Cuboids:Q', 'Role:N']
    ).properties(width=700)

    st.altair_chart(line_chart, use_container_width=True)
    st.markdown("### 📋 Data Table")
    st.dataframe(summary)


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


# small UX footer
    st.markdown("---")
    st.caption("Tip: adjust the period end date to plan compensation for upcoming days. Use 'Top/Low Performers' to focus the view.")
    st.markdown("""
    This dashboard provides a comprehensive overview of annotator performance, enabling data-driven decisions for team management.
    """)