import streamlit as st
import pandas as pd
import altair as alt
from .data_quality_loader import load_quality_data, SHEET_GID_MAP
from .quality_performance_dashboard import calc_quality, classify_quality, text_color

TEAM_STRUCTURE = {
    "A": {"Coordinator": "Abhina", "Lead Editor": "Sharath",
          "Members": ["Bhanushekar (AvinaShree)", "Abhinashree",
                      "Priyanka (Mokshashree CM)", "PriyaPragathi (Sushmitha S)"]},
    "B": {"Coordinator": "Aina", "Lead Editor": "Danny",
          "Members": ["Chandu M", "Aarohi", "Kruthi", "Shivukumar"]},
    "C": {"Coordinator": "Nayana", "Lead Editor": "Ravi",
          "Members": ["Thashvi (Amulya)", "Jyothi (Arpitha)", "Deepika (Chandana)", "Nayana"]},
    "D": {"Coordinator": "Dhanushree", "Lead Editor": "Vinod",
          "Members": ["Nisarga", "Shilpa (Divya)", "Dhanushree", "Sneha KM"]},
    "E": {"Coordinator": "Babu", "Lead Editor": "Ramesh",
          "Members": ["Praveen (Babu M)", "Manu", "Abhishek", "Mohammad"]}
}


def _expand_aliases(name: str):
    results = [name.strip()]
    if '(' in name and ')' in name:
        before, rest = name.split('(', 1)
        before = before.strip()
        inside = rest.split(')', 1)[0]
        alts = [a.strip() for a in inside.replace('/', ',').split(',') if a.strip()]
        results.extend([before] + alts)
    return list(set(results))


def _build_annotator_to_team():
    mapping = {}
    for team, info in TEAM_STRUCTURE.items():
        all_names = [info["Coordinator"], info["Lead Editor"]] + info["Members"]
        for n in all_names:
            for alias in _expand_aliases(n):
                mapping[alias] = team
    return mapping


def fetch_all_sheets():
    dfs = []
    for sheet in SHEET_GID_MAP.keys():
        df = load_quality_data(sheet_name=sheet)
        if not df.empty:
            df["Sheet"] = sheet
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def render_team_quality():
    st.title("👥 Team Quality Performance")

    df = fetch_all_sheets()
    if df.empty:
        st.warning("No quality data available.")
        return

    df = calc_quality(df)
    df = df[df["Rename"].notna() & (df["Rename"] != "Select Names")]

    annotator_to_team = _build_annotator_to_team()
    df["Team"] = df["Rename"].apply(lambda x: annotator_to_team.get(x.strip(), "Unassigned"))

    with st.sidebar:
        st.header("Filters")
        selected_team = st.selectbox("Select Team", ["All"] + sorted(TEAM_STRUCTURE.keys()))
        date_range = st.date_input("Submission Date Range", [])

    if selected_team != "All":
        df = df[df["Team"] == selected_team]
    if date_range and len(date_range) == 2:
        df = df[(df["Date_dt"] >= pd.to_datetime(date_range[0])) &
                (df["Date_dt"] <= pd.to_datetime(date_range[1]))]

    if df.empty:
        st.warning("No records for selected filters.")
        return

    # Team members
    st.subheader("📋 Team Members")
    members_list = []
    for team, info in TEAM_STRUCTURE.items():
        raw_names = [info["Coordinator"], info["Lead Editor"]] + info["Members"]
        expanded = []
        for n in raw_names:
            expanded.extend(_expand_aliases(n))
        members_list.append({
            "Team": team,
            "Coordinator": info["Coordinator"],
            "Lead Editor": info["Lead Editor"],
            "Members": ", ".join(sorted(set(expanded)))
        })
    st.dataframe(pd.DataFrame(members_list))

    # Team comparison
    st.subheader("📊 Team Quality Comparison")
    team_summary = df.groupby("Team").agg({
        "Base Quality %": "mean", "Penalty %": "mean", "Quality %": "mean",
        "Total Cuboids": "sum", "Missing Cuboids": "sum"
    }).reset_index()

    col1, col2, col3 = st.columns(3)
    if not team_summary.empty:
        col1.metric("Best Team", team_summary.loc[team_summary["Quality %"].idxmax(), "Team"])
        col2.metric("Highest Cuboids", f"{team_summary['Total Cuboids'].max():,}")
        col3.metric("Lowest Penalty", team_summary.loc[team_summary["Penalty %"].idxmin(), "Team"])

    chart = alt.Chart(team_summary).mark_bar().encode(
        x="Team:N", y=alt.Y("Quality %:Q", title="Final Quality %"),
        color="Team:N",
        tooltip=["Team", "Base Quality %", "Penalty %", "Quality %", "Total Cuboids", "Missing Cuboids"]
    ).properties(height=400)
    st.altair_chart(chart, use_container_width=True)

    # Quality trend
    st.subheader("📈 Team Quality Trend Over Time")
    trend = df.groupby(["Date_dt", "Team"])[["Base Quality %", "Quality %"]].mean().reset_index()
    line = alt.Chart(trend).mark_line(point=True).encode(
        x="Date_dt:T", y="Quality %:Q", color="Team:N",
        tooltip=["Date_dt", "Team", "Base Quality %", "Quality %"]
    ).properties(height=400)
    st.altair_chart(line, use_container_width=True)

    # Annotator performance
    st.subheader("👤 Annotator Performance by Team")
    per_person = df.groupby(["Team", "Rename"]).agg({
        "Base Quality %": "mean", "Penalty %": "mean", "Quality %": "mean",
        "Total Cuboids": "sum", "Missing Cuboids": "sum"
    }).reset_index()
    per_person["Decision"] = per_person["Quality %"].apply(classify_quality)

    if selected_team != "All":
        per_person = per_person[per_person["Team"] == selected_team]

    st.dataframe(per_person.style.applymap(text_color))

    # Team-wise detailed tables + storytelling
    st.subheader("📋 Detailed Quality Tables (Team-wise)")
    for team, sub in df.groupby("Team"):
        st.markdown(f"#### 🟦 Team {team}")
        detail_cols = ["Team", "Rename", "Job ID", "BL", "DI", "Status",
                       "Visibility", "Class", "Geometry",
                       "Base Quality %", "Penalty %", "Quality %", "Sheet", "Date"]
        detail_df = sub[[c for c in detail_cols if c in sub.columns]]
        st.dataframe(detail_df.style.applymap(text_color))

        # Storytelling summary
        avg_base = sub["Base Quality %"].mean()
        avg_penalty = sub["Penalty %"].mean()
        final_quality = sub["Quality %"].mean()
        st.markdown(
            f"**Summary:** Team {team} achieved a strong base quality of **{avg_base:.1f}%**, "
            f"but penalties from missed cuboids averaged **-{avg_penalty:.1f}%**, "
            f"resulting in a final quality of **{final_quality:.1f}%**."
        )
