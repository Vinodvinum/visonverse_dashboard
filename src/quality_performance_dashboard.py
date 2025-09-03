import streamlit as st
import pandas as pd
import altair as alt
from .data_quality_loader import SHEET_GID_MAP, load_quality_data

RENAMES = [
    "Thashvi (Amulya)", "Jyothi (Arpitha)", "Deepika (Chandana)", "Shilpa (Divya)", "Chandu M", "Shivukumar",
    "Dhanushree", "Praveen (Babu M)", "Bhanushekar (AvinaShree)", "Abhinashree", "Nayana", "Kruthi",
    "PriyaPragathi (Sushmitha S)", "Priyanka (Mokshashree CM)", "Sneha KM", "Mohammad", "Abhishek", "Nisarga",
    "Aarohi", "Manu", "Mukund", "Sharath", "Ravi", "Nisha", "Madhushree", "Sowjanya", "Danny", "Sushma",
    "Ramesh", "Nithin"
]

SCORE_MAP = {"Poor": 1, "Average": 2, "Good": 3, "VeryGood": 4, "Excellent": 5}

def fetch_all_sheets():
    dfs = []
    for sheet in SHEET_GID_MAP.keys():
        df = load_quality_data(sheet_name=sheet)
        if not df.empty:
            df["Sheet"] = sheet
            dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def calc_quality(df):
    df = df.copy()
    score_cols = ["Geometry", "BL", "DI", "Status", "Visibility", "Class"]
    # Quality is 100% only if all scores are Excellent and Missing Cuboids is 0
    df["Quality %"] = df.apply(
        lambda row: 100 if all(row.get(col) == "Excellent" for col in score_cols if col in row)
                        and row.get("Missing Cuboids", 1) == 0
                    else 0,
        axis=1
    )
    for col in score_cols:
        if col in df.columns:
            df[col + " Score"] = df[col].map(SCORE_MAP)
    return df

def render_quality_dashboard():
    st.title("🧮 Data Quality Performance Dashboard")

    with st.sidebar:
        st.header("Filters")
        sheet_options = ["All"] + list(SHEET_GID_MAP.keys())
        selected_sheet = st.selectbox("Select Sheet", sheet_options)
        selected_person = st.selectbox("Select Annotator", ["All"] + RENAMES)
        date_range = st.date_input("Submission Date Range", [])
        st.markdown("---")
        st.caption("Quality % = 100 only if all scores are Excellent and Missing Cuboids is 0")

    # Load data
    if selected_sheet == "All":
        df = fetch_all_sheets()
    else:
        df = load_quality_data(sheet_name=selected_sheet)
        if not df.empty:
            df["Sheet"] = selected_sheet

    if df.empty:
        st.warning("No quality data available.")
        return

    # Filter by annotator
    if selected_person != "All":
        df = df[df["Rename"] == selected_person]

    # Filter by date range
    if date_range and len(date_range) == 2:
        df = df[(df["Date_dt"] >= pd.to_datetime(date_range[0])) & (df["Date_dt"] <= pd.to_datetime(date_range[1]))]

    if df.empty:
        st.warning("No records for selected filters.")
        return

    df = calc_quality(df)
    df = df[df["Rename"] != "Select Names"]  # Ignore incomplete rows

    # --- Quality Distribution ---
    st.markdown("### Quality Distribution")
    dist = df["Quality %"].value_counts().reset_index()
    dist.columns = ["Quality %", "Count"]
    pie = alt.Chart(dist).mark_arc().encode(
        theta=alt.Theta("Count:Q", stack=True),
        color=alt.Color("Quality %:N"),
        tooltip=["Quality %", "Count"]
    ).properties(title="Quality Distribution")
    st.altair_chart(pie, use_container_width=True)

    # --- Visualization ---
    if selected_person == "All":
        # Line graph: Quality % for all annotators across sheets
        agg = df.groupby(["Rename", "Sheet"])["Quality %"].mean().reset_index()
        line = alt.Chart(agg).mark_line(point=True).encode(
            x=alt.X("Sheet:N", title="Sheet"),
            y=alt.Y("Quality %:Q"),
            color="Rename:N",
            tooltip=["Rename", "Sheet", "Quality %"]
        ).properties(height=400, title="Annotator Quality % by Sheet")
        st.altair_chart(line, use_container_width=True)
        st.dataframe(agg.style.format({"Quality %": "{:.2f}"}))
    else:
        # Line graph: Selected annotator's quality % per sheet
        agg = df.groupby("Sheet")["Quality %"].mean().reset_index()
        line = alt.Chart(agg).mark_line(point=True).encode(
            x=alt.X("Sheet:N", title="Sheet"),
            y=alt.Y("Quality %:Q"),
            tooltip=["Sheet", "Quality %"]
        ).properties(height=300, title=f"{selected_person} Quality % by Sheet")
        st.altair_chart(line, use_container_width=True)
        st.dataframe(agg.style.format({"Quality %": "{:.2f}"}))

        # Show average score per sheet for each score column
        score_cols = [col + " Score" for col in ["Geometry", "BL", "DI", "Status", "Visibility", "Class"] if col + " Score" in df.columns]
        if score_cols:
            score_agg = df.groupby("Sheet")[score_cols].mean().reset_index()
            st.markdown("#### Average Score by Sheet")
            st.dataframe(score_agg.style.format({col: "{:.2f}" for col in score_cols}))

    # --- Detailed Table ---
    st.markdown("### 📋 Detailed Quality Table")
    st.dataframe(df.style.format({"Total Cuboids": "{:,}", "Missing Cuboids": "{:,}", "Quality %": "{:.2f}"}))

# To use in your main app:
# render_quality_dashboard()