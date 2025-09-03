# visionverse_dashboard/src/team_structure.py
import streamlit as st
import pandas as pd
import altair as alt

# Hardcoded mapping (from your org chart)
TEAM_STRUCTURE = {
    "A": {"Coordinator": "Abhina", "Lead Editor": "Sharath",
          "Members": ["Bhanushekar","Abhina","Priyanka","PriyaPragathi"]},
    "B": {"Coordinator": "Aina", "Lead Editor": "Danny",
          "Members": ["Chandu M","Aarohi","Kruthi","Shivukumar"]},
    "C": {"Coordinator": "Nayana", "Lead Editor": "Ravi",
          "Members": ["Thashvi","Jyothi","Deepika","Nayana"]},
    "D": {"Coordinator": "Dhanushree", "Lead Editor": "Vinod",
          "Members": ["Nisarga","Shilpa","Dhanushree","Sneha KM"]},
    "E": {"Coordinator": "Babu", "Lead Editor": "Shashi",
          "Members": ["Praveen","Manu","Abhishek","Mohammad"]}
}

# Daily base targets
MAKER_TARGET_DAILY = 650
EDITOR_TARGET_DAILY = 1200

def render_team_structure(df):
    st.title("👥 Team Management & Performance")

    if df is None or df.empty:
        st.warning("No data found for team metrics.")
        return
    df = df.copy()

    # ---- Period filter (like Performance Dashboard) ----
    period = st.radio("Select Period", ["Daily", "Weekly", "Monthly"], horizontal=True)

    multiplier = {"Daily": 1, "Weekly": 6, "Monthly": 26}[period]
    maker_target = MAKER_TARGET_DAILY * multiplier
    editor_target = EDITOR_TARGET_DAILY * multiplier

    st.caption(f"📌 Using {period} targets: Maker = {maker_target}, Editor = {editor_target}")

    team_summary = []

    # ---- Loop through teams ----
    for team, info in TEAM_STRUCTURE.items():
        st.subheader(f"Team {team}")
        st.write(f"**Coordinator:** {info['Coordinator']} | **Lead Editor:** {info['Lead Editor']}")

        team_df = df[df['Rename'].isin(info["Members"])].copy()
        if team_df.empty:
            st.warning(f"No data for Team {team}")
            continue

        # Aggregate per person in this team
        agg = team_df.groupby(['Rename','Role'])['Cuboids'].sum().reset_index()
        agg['Target'] = agg['Role'].apply(lambda r: maker_target if r=="Maker" else editor_target)
        agg['Deficit'] = agg['Cuboids'] - agg['Target']
        agg['Target Met'] = agg['Deficit'] >= 0

        # Show table with deficit coloring
        st.dataframe(
            agg.style.format({'Cuboids':'{:,}','Target':'{:,}','Deficit':'+{:,}'})
               .applymap(lambda v: 'color:red;' if isinstance(v,(int,float)) and v<0 else
                                   ('color:green;' if isinstance(v,(int,float)) and v>0 else ''),
                         subset=['Deficit'])
        )

        # Compute team totals
        total_cuboids = agg['Cuboids'].sum()
        total_target = agg['Target'].sum()
        deficit = total_cuboids - total_target
        pct_met = 100 * agg['Target Met'].mean()

        team_summary.append({
            "Team": team,
            "Total Cuboids": total_cuboids,
            "Team Target": total_target,
            "Deficit": deficit,
            "% Met": pct_met
        })

        # Highlight deficit members
        underperformers = agg[agg['Deficit'] < 0]
        if not underperformers.empty:
            st.warning("⚠️ Underperformers in this team:")
            st.table(underperformers[['Rename','Role','Cuboids','Target','Deficit']])
        else:
            st.success("✅ All members met targets in this team.")

        st.markdown("---")

    # ---- Team comparison ----
    if team_summary:
        st.subheader("📊 Team Comparison")
        summary_df = pd.DataFrame(team_summary)

        chart = alt.Chart(summary_df).mark_bar().encode(
            x='Team:N',
            y='Total Cuboids:Q',
            color=alt.condition(alt.datum['Deficit']>=0, alt.value('#2ca02c'), alt.value('#d62728')),
            tooltip=['Team','Total Cuboids','Team Target','Deficit','% Met']
        ).properties(height=400)

        st.altair_chart(chart, use_container_width=True)
        st.dataframe(
            summary_df.style.format({'Total Cuboids':'{:,}','Team Target':'{:,}','Deficit':'+{:,}','% Met':'{:.1f}%'})
               .applymap(lambda v: 'color:red;' if isinstance(v,(int,float)) and v<0 else
                                   ('color:green;' if isinstance(v,(int,float)) and v>0 else ''),
                         subset=['Deficit'])
        )

    # ---- Hierarchy ----
    st.markdown("### 📌 Reporting Hierarchy")
    st.info("""
    - **Team Co-ordinators & Lead Editors** → Report to **Jayanth (Team Lead)**  
    - **Jayanth (Team Lead)** → Reports to **Santosh (Reporting Manager)**  
    - **Santosh (Reporting Manager)** → Reports to **Kavya (Project Delivery Director)**  
    """)
