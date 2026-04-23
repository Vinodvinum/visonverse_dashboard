import streamlit as st
import pandas as pd
import altair as alt
import calendar

# ---- Team roster (include aliases in parentheses; both will be recognized) ----
TEAM_STRUCTURE = {
    "A": {"Lead Editor": "Sharath","Coordinator": "Abhina",
         "Members": ["Bhanushekar (AvinaShree)", "Abhinashree", "Priyanka (Mokshashree CM)", "PriyaPragathi (Sushmitha S)"]},
    "B": {"Lead Editor": "Danny","Coordinator": "Aina",
         "Members": ["Chandu M", "Aarohi", "Kruthi", "Shivukumar"]},
    "C": {"Lead Editor": "Ravi","Coordinator": "Nayana",
         "Members": ["Thashvi (Amulya)", "Jyothi (Arpitha)", "Deepika (chandana)", "Nayana"]},
    "D": {"Lead Editor": "Vinod","Coordinator": "Dhanushree",
         "Members": ["Nisarga", "Shilpa (divya)", "Dhanushree", "Sneha KM"]},
    "E": {"Lead Editor": "Ramesh","Coordinator": "Babu",
         "Members": ["Praveen (Babu M)", "Manu", "Abhishek", "Mohammad"]}
}

# ---- Targets (keep in sync with performance_dashboard.py) ----
MAKER_TARGET_DAILY = 750
EDITOR_TARGET_DAILY = 1500

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'Date' not in df.columns:
        if 'Date_dt' in df.columns: return df
        st.error("Input dataframe must contain 'Date' or 'Date_dt'.")
        return df
    
    def _smart_parse(val):
        if pd.isna(val) or str(val).strip() == '': return pd.NaT
        s = str(val).strip()
        for fmt in ('%b-%y', '%B-%y', '%b-%Y', '%B-%Y'):
            try:
                d = pd.to_datetime(s, format=fmt)
                if 2000 <= d.year <= 2100: return d
            except: continue
        return pd.to_datetime(s, errors='coerce', dayfirst=True)

    df['Date_dt'] = df['Date'].apply(_smart_parse)
    df['Date_dt'] = df['Date_dt'].fillna(pd.Timestamp.today().normalize())
    df['Date_dt'] = df['Date_dt'].dt.normalize()
    return df

def _expand_aliases(name: str) -> list[str]:
    results = [name.strip()]
    if '(' in name and ')' in name:
        before, rest = name.split('(', 1)
        before = before.strip()
        inside = rest.split(')', 1)[0]
        alts = [a.strip() for a in inside.replace('/', ',').split(',') if a.strip()]
        results.extend([before] + alts)
    return results

def _build_annotator_to_team() -> dict:
    m = {}
    for team, info in TEAM_STRUCTURE.items():
        members = [info['Coordinator'], info['Lead Editor']] + info['Members']
        expanded = []
        for person in members:
            expanded.extend(_expand_aliases(person))
        for nm in expanded:
            m.setdefault(nm, team)
    return m

def _daily_target_for_role(role: str) -> int:
    return MAKER_TARGET_DAILY if role == 'Maker' else EDITOR_TARGET_DAILY

def _working_days_excluding_sunday(start: pd.Timestamp, end: pd.Timestamp) -> int:
    rng = pd.date_range(start, end, freq='D')
    return int((rng.weekday != 6).sum())

# ------------------------------------------------------------------
# Period picker (Daily / Weekly / Monthly)
# ------------------------------------------------------------------

def _select_period(df: pd.DataFrame):
    st.sidebar.header("Team Page Filters")
    view_period = st.sidebar.radio("Timeframe", ["Daily", "Weekly", "Monthly"], index=0)
    
    if view_period == "Daily":
        available = sorted(df['Date_dt'].dt.date.unique())
        default_date = available[-1] if available else pd.Timestamp.today().date()
        sel_date = st.sidebar.date_input("Select date", value=default_date)
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
            try: monday = pd.Timestamp.fromisocalendar(y, w, 1)
            except: monday = r['min']
            start = monday.normalize()
            end = (monday + pd.Timedelta(days=4)).normalize()
            opts.append((y, w, start, end))
        
        labels = [f"{y}-W{w:02d} ({s.date()} -> {e.date()})" for (y, w, s, e) in opts]
        if not labels:
            st.warning("No weekly ranges available.")
            return None
        sel = st.sidebar.selectbox("Select week", labels, index=len(labels) - 1)
        chosen = opts[labels.index(sel)]
        start, end = chosen[2], chosen[3]
        multiplier = 5
        label = f"{start.date()} -> {end.date()}"
    else: # Monthly
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
            st.warning("No monthly ranges available.")
            return None
        sel = st.sidebar.selectbox("Select month", labels, index=len(labels) - 1)
        chosen = opts[labels.index(sel)]
        start, end = chosen[2], chosen[3]
        multiplier = _working_days_excluding_sunday(start, end)
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
        
    df = _parse_dates(df)
    
    for c in ['Rename', 'Role', 'Cuboids', 'Date_dt']:
        if c not in df.columns:
            st.error(f"Missing required column: {c}")
            return
            
    df['Cuboids'] = pd.to_numeric(df['Cuboids'], errors='coerce').fillna(0)
    
    period = _select_period(df)
    if period is None: return
    
    start_date = period["start_date"]
    end_date = period["end_date"]
    period_label = period["period_label"]
    period_multiplier = period["period_multiplier"]
    
    st.subheader(f"{period['view_period']} Overview — {period_label}")
    
    df_period = df[(df['Date_dt'] >= start_date) & (df['Date_dt'] <= end_date)].copy()
    if df_period.empty:
        st.info("No records in the selected period.")
        return
        
    annotator_to_team = _build_annotator_to_team()
    df_period['Team'] = df_period['Rename'].map(annotator_to_team).fillna("Unassigned")
    
    for team in sorted(TEAM_STRUCTURE.keys()):
        info = TEAM_STRUCTURE[team]
        names_raw = [info['Lead Editor'], info['Coordinator']] + info['Members']
        
        team_names = []
        for s in names_raw:
            team_names.extend(_expand_aliases(s))
        team_names = list(dict.fromkeys(team_names))
        
        team_df = df_period[df_period['Rename'].isin(team_names)].copy()
        
        st.markdown(f"#### Team {team}")
        st.write(f"**Lead Editor:** {info['Lead Editor']} | **Coordinator:** {info['Coordinator']}")
        
        if team_df.empty:
            st.warning(f"No data for Team {team} in this period.")
            st.markdown("---")
            continue
            
        per_person = team_df.groupby(['Rename', 'Role'])['Cuboids'].sum().reset_index().rename(columns={'Cuboids': 'Total Cuboids'})
        per_person['Daily Target'] = per_person['Role'].apply(_daily_target_for_role)
        per_person['Period Target'] = per_person['Daily Target'] * period_multiplier
        per_person['Deficit'] = per_person['Total Cuboids'] - per_person['Period Target']
        per_person['Target Met'] = per_person['Deficit'] >= 0
        
        st.dataframe(
            per_person[['Rename', 'Role', 'Total Cuboids', 'Period Target', 'Deficit', 'Target Met']]
            .sort_values('Total Cuboids', ascending=False)
            .style.format({'Total Cuboids': '{:,}', 'Period Target': '{:,}', 'Deficit': '{:+,}'})
            .map(lambda v: 'color: #2ca02c' if isinstance(v, (int, float)) and v >= 0 else 'color: #d62728', subset=['Deficit'])
        )
        st.markdown("---")

