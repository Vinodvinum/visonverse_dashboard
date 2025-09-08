# visionverse_dashboard/src/team_structure.py
import streamlit as st
import pandas as pd
import altair as alt
import calendar

# ---- Team roster (include aliases in parentheses; both will be recognized) ----
TEAM_STRUCTURE = {
    "A": {"Lead Editor": "Sharath","Coordinator": "Abhina", 
          "Members": ["Bhanushekar (AvinaShree)", "Abhinashree",
                      "Priyanka (Mokshashree CM)", "PriyaPragathi (Sushmitha S)"]},
    "B": {"Lead Editor": "Danny","Coordinator": "Aina", 
          "Members": ["Chandu M", "Aarohi", "Kruthi", "Shivukumar"]},
    "C": {"Lead Editor": "Ravi","Coordinator": "Nayana", 
          "Members": ["Thashvi (Amulya)", "Jyothi (Arpitha)",
                      "Deepika (chandana)", "Nayana"]},
    "D": {"Lead Editor": "Vinod","Coordinator": "Dhanushree", 
          "Members": ["Nisarga", "Shilpa (divya)", "Dhanushree", "Sneha KM"]},
    "E": {"Lead Editor": "Ramesh","Coordinator": "Babu", 
          "Members": ["Praveen (Babu M)", "Manu", "Abhishek", "Mohammad"]}
}

# ---- Targets (keep in sync with performance_dashboard.py) ----
MAKER_TARGET_DAILY = 780
EDITOR_TARGET_DAILY = 1500

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'Date_dt' not in df.columns:
        if 'Date' not in df.columns:
            st.error("Input dataframe must contain 'Date' or 'Date_dt'.")
            return df
        df['Date_dt'] = pd.to_datetime(df['Date'], errors='coerce')
        if df['Date_dt'].isna().all():
            df['Date_dt'] = pd.to_datetime(df['Date'].astype(str) + ' 2025', errors='coerce')
        df['Date_dt'] = df['Date_dt'].fillna(pd.Timestamp.today().normalize())
    else:
        df['Date_dt'] = pd.to_datetime(df['Date_dt'], errors='coerce')
    df['Date_dt'] = df['Date_dt'].dt.normalize()
    return df

def _expand_aliases(name: str) -> list[str]:
    """
    'Priyanka (Mokshashree CM)' -> 
        ['Priyanka (Mokshashree CM)', 'Priyanka', 'Mokshashree CM']
    """
    results = [name.strip()]  # keep full original
    if '(' in name and ')' in name:
        before, rest = name.split('(', 1)
        before = before.strip()
        inside = rest.split(')', 1)[0]
        alts = [a.strip() for a in inside.replace('/', ',').split(',') if a.strip()]
        results.extend([before] + alts)
    return results

def _build_annotator_to_team() -> dict:
    """Map every listed person & alias to a team (coordinator/lead included)."""
    m = {}
    for team, info in TEAM_STRUCTURE.items():
        members = [info['Coordinator'], info['Lead Editor']] + info['Members']
        expanded = []
        for person in members:
            expanded.extend(_expand_aliases(person))
        for nm in expanded:
            m.setdefault(nm, team)  # don’t overwrite if duplicate across teams
    return m

def _daily_target_for_role(role: str) -> int:
    return MAKER_TARGET_DAILY if role == 'Maker' else EDITOR_TARGET_DAILY

# ------------------------------------------------------------------
# Period picker (Daily / Weekly / Monthly)
# ------------------------------------------------------------------
def _select_period(df: pd.DataFrame):
    st.sidebar.header("Team Page Filters")
    view_period = st.sidebar.radio("Timeframe", ["Daily", "Weekly", "Monthly"], index=0)

    if view_period == "Daily":
        available = sorted(df['Date_dt'].dt.date.unique())
        default_date = available[-1] if available else pd.Timestamp.today().date()
        sel_date = st.sidebar.date_input(
            "Select date", value=default_date,
            min_value=available[0] if available else None,
            max_value=available[-1] if available else None
        )
        start = end = pd.Timestamp(sel_date).normalize()
        multiplier = 1
        label = f"{start.date()}"

    elif view_period == "Weekly":
        iso = df['Date_dt'].dt.isocalendar()
        df_iso = df.assign(iso_year=iso['year'], iso_week=iso['week'])
        combos = df_iso.groupby(['iso_year', 'iso_week'])['Date_dt'].agg(['min', 'max']).reset_index()
        opts = []
        for _, r in combos.iterrows():
            y, w = int(r['iso_year']), int(r['iso_week'])
            try:
                monday = pd.Timestamp.fromisocalendar(y, w, 1)
            except Exception:
                monday = r['min']
            start = monday.normalize()
            end = (monday + pd.Timedelta(days=4)).normalize()  # Mon–Fri
            opts.append((y, w, start, end))
        labels = [f"{y}-W{w:02d} ({s.date()} → {e.date()})" for (y, w, s, e) in opts]
        if not labels:
            st.warning("No weekly ranges available in data.")
            return None
        sel = st.sidebar.selectbox("Select week", labels, index=len(labels) - 1)
        chosen = opts[labels.index(sel)]
        start, end = chosen[2], chosen[3]
        multiplier = 5
        label = f"{start.date()} → {end.date()}"

    else:  # Monthly
        df_m = df.copy()
        df_m['year'] = df_m['Date_dt'].dt.year
        df_m['month'] = df_m['Date_dt'].dt.month
        combos = df_m.groupby(['year', 'month'])['Date_dt'].agg(['min', 'max']).reset_index()
        opts = []
        for _, r in combos.iterrows():
            y, m = int(r['year']), int(r['month'])
            start = pd.Timestamp(year=y, month=m, day=1).normalize()
            last = calendar.monthrange(y, m)[1]
            end = pd.Timestamp(year=y, month=m, day=last).normalize()
            opts.append((y, m, start, end))
        labels = [f"{y}-{m:02d} ({calendar.month_name[m]} {y})" for (y, m, _, _) in opts]
        if not labels:
            st.warning("No monthly ranges available in data.")
            return None
        sel = st.sidebar.selectbox("Select month", labels, index=len(labels) - 1)
        chosen = opts[labels.index(sel)]
        start, end = chosen[2], chosen[3]
        multiplier = 21  # Mon–Fri (20) + last Saturday
        label = f"{calendar.month_name[chosen[1]]} {chosen[0]}"

    return {
        "view_period": view_period,
        "start_date": start,
        "end_date": end,
        "period_label": label,
        "period_multiplier": multiplier
    }

# ------------------------------------------------------------------
# Main renderer
# ------------------------------------------------------------------
def render_team_structure(df: pd.DataFrame):
    st.title("👥 Team Management & Performance")

    if df is None or df.empty:
        st.warning("No data provided.")
        return

    # Normalize
    df = _parse_dates(df)
    for c in ['Rename', 'Role', 'Cuboids', 'Date_dt']:
        if c not in df.columns:
            st.error(f"Missing required column: {c}")
            return
    df['Cuboids'] = pd.to_numeric(df['Cuboids'], errors='coerce')
    df = df.dropna(subset=['Cuboids', 'Date_dt'])

    # Period selection
    period = _select_period(df)
    if period is None:
        return
    start_date = period["start_date"]
    end_date = period["end_date"]
    period_label = period["period_label"]
    period_multiplier = period["period_multiplier"]

    st.subheader(f"{period['view_period']} Overview — {period_label}")

    # Slice to period
    df_period = df[(df['Date_dt'] >= start_date) & (df['Date_dt'] <= end_date)].copy()
    if df_period.empty:
        st.info("No records in the selected period.")
        return

    # Mapping annotators to teams (aliases included)
    annotator_to_team = _build_annotator_to_team()
    df_period['Team'] = df_period['Rename'].map(annotator_to_team).fillna("Unassigned")

    # ---------- Per-Team Sections ----------
    team_summaries = []
    for team in sorted(TEAM_STRUCTURE.keys()):
        info = TEAM_STRUCTURE[team]
        names_raw = [info['Lead Editor'], info['Coordinator']] + info['Members']  # <-- Lead Editor first
        team_names = []
        for s in names_raw:
            team_names.extend(_expand_aliases(s))
        team_names = list(dict.fromkeys(team_names))

        team_df = df_period[df_period['Rename'].isin(team_names)].copy()

        st.markdown(f"#### Team {team}")
        st.write(f"**Lead Editor:** {info['Lead Editor']} &nbsp;&nbsp;|&nbsp;&nbsp; **Coordinator:** {info['Coordinator']}")  # <-- Lead Editor first

        if team_df.empty:
            st.warning(f"No data for Team {team} in this period.")
            st.markdown("---")
            continue

        # Per-person totals
        per_person = (team_df.groupby(['Rename', 'Role'])['Cuboids']
                      .sum().reset_index().rename(columns={'Cuboids': 'Total Cuboids'}))

        per_person['Daily Target'] = per_person['Role'].apply(_daily_target_for_role)
        per_person['Period Target'] = per_person['Daily Target'] * period_multiplier
        per_person['Deficit'] = per_person['Total Cuboids'] - per_person['Period Target']
        per_person['Target Met'] = per_person['Deficit'] >= 0

        st.dataframe(
            per_person[['Rename', 'Role', 'Total Cuboids', 'Period Target', 'Deficit', 'Target Met']]
            .sort_values('Total Cuboids', ascending=False)
            .style.format({'Total Cuboids': '{:,}', 'Period Target': '{:,}', 'Deficit': '{:+,}'})
                  .applymap(lambda v: 'color: #2ca02c' if isinstance(v, (int, float)) and v > 0
                                        else ('color: #d62728' if isinstance(v, (int, float)) and v < 0 else ''),
                            subset=['Deficit'])
        )

        under = per_person[per_person['Deficit'] < 0].copy()
        if not under.empty:
            st.warning("⚠️ Members below target")
            st.table(under[['Rename', 'Role', 'Total Cuboids', 'Period Target', 'Deficit']]
                     .sort_values('Deficit').style.format({'Total Cuboids': '{:,}', 'Period Target': '{:,}', 'Deficit': '{:+,}'}))
        else:
            st.success("✅ All members met their period targets.")

        team_actual = int(per_person['Total Cuboids'].sum())
        team_target = int(per_person['Period Target'].sum())
        team_deficit = team_actual - team_target
        pct_met = float((per_person['Target Met'].mean() * 100.0)) if not per_person.empty else 0.0

        team_summaries.append({
            "Team": team,
            "Total Cuboids": team_actual,
            "Team Target": team_target,
            "Deficit": team_deficit,
            "% Met": pct_met
        })

        st.markdown("---")

    # ---------- Cross-Team Comparison ----------
    if team_summaries:
        st.subheader("📊 Team Comparison")
        summary_df = pd.DataFrame(team_summaries).sort_values('Total Cuboids', ascending=False)

        long = summary_df.melt(id_vars='Team', value_vars=['Total Cuboids', 'Team Target'],
                               var_name='Metric', value_name='Value')
        chart_grouped = alt.Chart(long).mark_bar().encode(
            x=alt.X('Team:N', title='Team'),
            y=alt.Y('Value:Q', title='Cuboids'),
            color=alt.Color('Metric:N', title=''),
            tooltip=['Team', 'Metric', 'Value']
        ).properties(height=360)
        st.altair_chart(chart_grouped, use_container_width=True)

        chart_def = alt.Chart(summary_df).mark_bar().encode(
            x=alt.X('Team:N', title='Team'),
            y=alt.Y('Deficit:Q', title='Surplus / Deficit'),
            color=alt.condition(alt.datum.Deficit >= 0, alt.value('#2ca02c'), alt.value('#d62728')),
            tooltip=['Team', 'Total Cuboids', 'Team Target', 'Deficit', alt.Tooltip('% Met:Q', format='.1f')]
        ).properties(height=300)
        st.altair_chart(chart_def, use_container_width=True)

        st.dataframe(
            summary_df.style.format({'Total Cuboids': '{:,}', 'Team Target': '{:,}', 'Deficit': '{:+,}', '% Met': '{:.1f}%'})
                      .applymap(lambda v: 'color: #2ca02c' if isinstance(v, (int, float)) and v > 0
                                            else ('color: #d62728' if isinstance(v, (int, float)) and v < 0 else ''),
                                subset=['Deficit'])
        )

        st.download_button(
            "Download team summary CSV",
            data=summary_df.to_csv(index=False),
            file_name="team_summary.csv",
            mime="text/csv"
        )

    # ---------- Hierarchy ----------
    st.markdown("### 📌 Reporting Hierarchy")
    st.info(
        "- **Team Co-ordinators & Lead Editors** → report to **Jayanth (Team Lead)**\n"
        "- **Jayanth (Team Lead)** → reports to **Santosh (Reporting Manager)**\n"
        "- **Santosh (Reporting Manager)** → reports to **Kavya (Project Delivery Director)**"
    )
