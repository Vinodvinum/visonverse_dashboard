# visionverse_dashboard/streamlit_app.py
import streamlit as st
from src.data_loader import load_team_data
from src.performance_dashboard import render_dashboard
from src.weekly_report_generator import render_weekly_report
#from src.data_validation import render_data_validation
from streamlit_autorefresh import st_autorefresh
from src.team_structure import render_team_structure
from src.quality_performance_dashboard import render_quality_dashboard
from src.team_quality import render_team_quality
# Auto-refresh every 600 seconds
st_autorefresh(interval=600000, key="data_refresh")

st.set_page_config(page_title="VisonVerse Dashboard", page_icon="📊", layout="wide")

role_map = {
    'Mukund': 'Editor',
    'Sharath': 'Editor',
    'Ravi': 'Editor',
    'Nisha': 'Editor',
    'Madhushree': 'Editor',
    'Sowjanya': 'Editor',
    'Danny': 'Editor',
    'Sushma': 'Editor',
    'Ramesh': 'Editor',
    'Nithin': 'Editor',
    'Thashvi': 'Maker',
    'Jyothi': 'Maker',
    'Deepika': 'Maker',
    'Shilpa': 'Maker',
    'Chandu M': 'Maker',
    'Shivukumar': 'Maker',
    'Dhanushree': 'Maker',
    'Praveen': 'Maker',
    'Bhanushekar': 'Maker',
    'Abhinashree': 'Maker',
    'Nayana': 'Maker',
    'Kruthi': 'Maker',
    'PriyaPragathi': 'Maker',
    'Priyanka': 'Maker',
    'Sneha KM': 'Maker',
    'Mohammad': 'Maker',
    'Abhishek': 'Maker',
    'Nisarga': 'Maker',
    'Aarohi': 'Maker',
    'Manu': 'Maker'
}

# Sidebar Navigation
st.sidebar.title("📊 VisonVerse Dashboard")
page = st.sidebar.radio("Go to", [
    "Home", "Performance Dashboard", "Weekly Report", "Team Structure", "Quality Performance", "Team Quality"
])


# Load fresh data every 10 minutes without page reload
st.cache_data.clear()  # clear all cached datasets on every run
df = load_team_data(role_map)

if df.empty:
    st.error("No data found from Google Sheet.")
    st.stop()

if page == "Home":
    st.title("👁️ VisonVerse Annotation Dashboard")
    st.markdown("""
Welcome to the VisonVerse QA Dashboard.

**Roles**:
- **Makers** → 780/day (≥80% quality)  
- **Editors** → 1500/day (≥95% quality)  

Data updates from Google Sheets every 1 minute automatically (no reload).
""")

elif page == "Performance Dashboard":
    render_dashboard(df)

elif page == "Weekly Report":
    render_weekly_report(df)

elif page == "Team Structure":
    render_team_structure(df)

elif page == "Quality Performance":
    render_quality_dashboard()

elif page == "Team Quality":
    render_team_quality()

#elif page == "Data Validation":
    #render_data_validation(df)

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align:center;font-weight:bold'>✨ Dashboard built by <span style='color:#d62828'>Vinod M</span> ✨</p>",
    unsafe_allow_html=True
)
