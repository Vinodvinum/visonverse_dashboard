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

SCORE_MAP = {"Poor": 1, "Average": 2, "Good": 2.5, "Excellent": 3}


def fetch_all_sheets():
    dfs = []
    for sheet in SHEET_GID_MAP.keys():
        df = load_quality_data(sheet_name=sheet)
        if not df.empty:
            df["Sheet"] = sheet
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def calc_quality(df):
    df = df.copy()
    score_cols = ["Geometry", "BL", "DI", "Status", "Visibility", "Class"]

    for col in score_cols:
        if col in df.columns:
            df[col + " Score"] = df[col].map(SCORE_MAP)

    def row_quality(row):
        scores = [row.get(col + " Score") for col in score_cols if pd.notna(row.get(col + " Score"))]
        if not scores:
            return 0
        base = (sum(scores) / len(scores)) / 3 * 100

        total = row.get("Total Cuboids", 0)
        missing = row.get("Missing Cuboids", 0)
        penalty = (missing / total * 100) if total > 0 else 0
        penalty = min(penalty, 30)

        return max(0, base - penalty)

    df["Quality %"] = df.apply(row_quality, axis=1)
    df["Base Quality %"] = df[[c + " Score" for c in score_cols]].mean(axis=1) / 3 * 100
    df["Penalty %"] = df.apply(
        lambda r: min((r["Missing Cuboids"] / r["Total Cuboids"]) * 100, 30)
        if r.get("Total Cuboids", 0) > 0 else 0, axis=1
    )
    if "Date" in df.columns:
        df["Date_dt"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    return df


def classify_quality(q):
    if q >= 90: return "Excellent"
    elif q >= 75: return "Good"
    elif q >= 60: return "Needs Improvement"
    return "Critical"


def text_color(val):
    if pd.isna(val):
        return ""
    if isinstance(val, (int, float)):
        if val >= 90: return "color: green"
        elif val >= 75: return "color: orange"
        else: return "color: red"
    if val in ["Excellent"]: return "color: green"
    if val in ["Good"]: return "color: orange"
    if val in ["Needs Improvement", "Critical"]: return "color: red"
    return ""


def render_quality_dashboard():
    st.title("🧮 Individual Quality Performance Dashboard")

    with st.sidebar:
        st.header("Filters")
        sheet_options = ["All"] + list(SHEET_GID_MAP.keys())
        selected_sheet = st.selectbox("Select Sheet", sheet_options)
        selected_person = st.selectbox("Select Annotator", ["All"] + RENAMES)
        date_range = st.date_input("Submission Date Range", [])

    df = fetch_all_sheets() if selected_sheet == "All" else load_quality_data(sheet_name=selected_sheet)
    if selected_sheet != "All" and not df.empty:
        df["Sheet"] = selected_sheet

    if df.empty:
        st.warning("No quality data available.")
        return

    df = calc_quality(df)
    df = df[df["Rename"] != "Select Names"]

    if selected_person != "All":
        df = df[df["Rename"] == selected_person]
    if date_range and len(date_range) == 2:
        df = df[(df["Date_dt"] >= pd.to_datetime(date_range[0])) &
                (df["Date_dt"] <= pd.to_datetime(date_range[1]))]

    if df.empty:
        st.warning("No records for selected filters.")
        return

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Base %", f"{df['Base Quality %'].mean():.1f}%")
    col2.metric("Avg Penalty %", f"-{df['Penalty %'].mean():.1f}%")
    col3.metric("Final Quality %", f"{df['Quality %'].mean():.1f}%")
    col4.metric("Jobs Evaluated", f"{df['Job ID'].nunique()}")

    # Trend
    st.markdown("### 📈 Quality Trend Over Time")
    trend = df.groupby("Date_dt")[["Base Quality %", "Quality %"]].mean().reset_index()
    st.altair_chart(
        alt.Chart(trend).mark_line(point=True).encode(
            x="Date_dt:T", y="Quality %:Q", tooltip=["Date_dt", "Base Quality %", "Quality %"]
        ).properties(height=300), use_container_width=True
    )

    # Breakdown
    st.markdown("### 📊 Score Breakdown by Metric")
    score_cols = [c for c in df.columns if c.endswith(" Score")]
    score_avg = df[score_cols].mean().reset_index()
    score_avg.columns = ["Metric", "Avg Score"]
    st.altair_chart(
        alt.Chart(score_avg).mark_bar().encode(
            x="Metric:N", y="Avg Score:Q", color="Avg Score:Q",
            tooltip=["Metric", "Avg Score"]
        ).properties(height=300), use_container_width=True
    )

    # Leaderboard
    st.markdown("### 🏆 Annotator Leaderboard")
    per_person = df.groupby("Rename").agg({
        "Base Quality %": "mean", "Penalty %": "mean", "Quality %": "mean",
        "Total Cuboids": "sum", "Missing Cuboids": "sum"
    }).reset_index()
    per_person["Decision"] = per_person["Quality %"].apply(classify_quality)
    st.dataframe(per_person.style.applymap(text_color))

    # Decision summary
    st.markdown("### 📝 Decision Summary")
    decision_counts = per_person["Decision"].value_counts().reset_index()
    decision_counts.columns = ["Category", "Count"]
    st.dataframe(decision_counts.style.applymap(text_color))

    # Improvement areas
    st.markdown("### 🔍 Improvement Areas")
    improvement_df = []
    for person, sub in df.groupby("Rename"):
        avg_scores = sub[score_cols].mean()
        weak = [m.replace(" Score", "") for m, s in avg_scores.items() if pd.notna(s) and s < 3]
        improvement_df.append({
            "Annotator": person,
            "Weakest Areas": ", ".join(weak) if weak else "None",
            "Quality %": sub["Quality %"].mean()
        })
    st.dataframe(pd.DataFrame(improvement_df).style.applymap(text_color))

    # Detailed table
    st.markdown("### 📋 Detailed Quality Table")
    detail_cols = ["Rename", "Job ID", "BL", "DI", "Status", "Visibility", "Class", "Geometry",
                   "Base Quality %", "Penalty %", "Quality %", "Sheet", "Date_fmt"]
    detail_df = df[[c for c in detail_cols if c in df.columns]]
    st.dataframe(detail_df.style.applymap(text_color))
