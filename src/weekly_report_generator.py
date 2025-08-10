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