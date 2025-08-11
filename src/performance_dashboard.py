# visionverse_dashboard/src/performance_dashboard.py
import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import calendar

# Constants (change if needed)
MAKER_TARGET_DAILY = 650
EDITOR_TARGET_DAILY = 1200
MAKERS_COUNT = 20     # configured team size
EDITORS_COUNT = 10    # configured team size

# ---------------- Utility functions ----------------
def _parse_dates(df):
    """Ensure Date_dt exists and normalized."""
    df = df.copy()
    if 'Date_dt' not in df.columns:
        if 'Date' not in df.columns:
            st.error("Input dataframe must contain a 'Date' column.")
            return df
        df['Date_dt'] = pd.to_datetime(df['Date'], errors='coerce')
        if df['Date_dt'].isna().all():
            df['Date_dt'] = pd.to_datetime(df['Date'].astype(str) + ' 2025', errors='coerce')
        df['Date_dt'] = df['Date_dt'].fillna(pd.Timestamp.today().normalize())
    else:
        df['Date_dt'] = pd.to_datetime(df['Date_dt'], errors='coerce')
    df['Date_dt'] = df['Date_dt'].dt.normalize()
    return df

def _daily_target_for_role(role):
    return MAKER_TARGET_DAILY if role == 'Maker' else EDITOR_TARGET_DAILY

def _business_days_mon_fri(start, end):
    """Count Mon-Fri inclusive between start and end (business days)."""
    if pd.isna(start) or pd.isna(end):
        return 0
    rng = pd.bdate_range(start, end)
    return len(rng)

def _aggregate_for_period(df_period, by='Rename'):
    return df_period.groupby(by)['Cuboids'].sum().reset_index().rename(columns={'Cuboids': 'Total Cuboids'})

def _compute_streaks(df):
    """Longest consecutive days where annotator met daily target."""
    results = {}
    for annot in df['Rename'].unique():
        a_df = df[df['Rename'] == annot].sort_values('Date_dt')
        if a_df.empty:
            results[annot] = 0
            continue
        role_val = a_df['Role'].iloc[0] if 'Role' in a_df.columns else 'Maker'
        target = _daily_target_for_role(role_val)
        day_sum = a_df.groupby('Date_dt')['Cuboids'].sum().reindex(
            pd.date_range(a_df['Date_dt'].min(), a_df['Date_dt'].max()), fill_value=0
        )
        max_streak = streak = 0
        for v in day_sum:
            if v >= target:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        results[annot] = max_streak
    return results

# ---------------- Dashboard ----------------
def render_dashboard(df):
    """
    df expected columns: Name, Rename, Date, Cuboids, Role
    - Rename: annotator display name
    - Date: parsable date string
    - Cuboids: numeric
    - Role: 'Maker' or 'Editor'
    """
    st.title("📈 VisonVerse — Performance Intelligence")

    if df is None or df.empty:
        st.warning("No data provided to performance dashboard.")
        return

    # Normalize input and basic checks
    df = df.copy()
    df = _parse_dates(df)
    for col in ['Rename', 'Role', 'Cuboids', 'Date_dt']:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            return

    # Sidebar: period & filters
    with st.sidebar:
        st.header("Filters")
        role_filter = st.selectbox("Role", ["All", "Maker", "Editor"])
        view_period = st.radio("Timeframe", ["Daily", "Weekly", "Monthly"], index=0)

        # Select period
        if view_period == "Daily":
            available_dates = sorted(df['Date_dt'].dt.date.unique())
            default_date = available_dates[-1] if available_dates else pd.Timestamp.today().date()
            sel_date = st.date_input("Select date", value=default_date,
                                     min_value=available_dates[0] if available_dates else None,
                                     max_value=available_dates[-1] if available_dates else None)
            start_date = end_date = pd.Timestamp(sel_date).normalize()
            period_multiplier = 1
            period_label = f"{start_date.date()}"

        elif view_period == "Weekly":
            # Build ISO week options and show monday->friday (5 working days/week)
            iso = df['Date_dt'].dt.isocalendar()
            df_iso = df.assign(iso_year=iso['year'], iso_week=iso['week'])
            combos = df_iso.groupby(['iso_year','iso_week'])['Date_dt'].agg(['min','max']).reset_index()
            opts = []
            for _, r in combos.iterrows():
                y, w = int(r['iso_year']), int(r['iso_week'])
                try:
                    monday = pd.Timestamp.fromisocalendar(y, w, 1)
                except Exception:
                    monday = r['min']
                # For 6-working-day week we use Mon-Sat
                start = monday.normalize()
                end = (monday + pd.Timedelta(days=5)).normalize()
                opts.append((y, w, start, end))
            opt_labels = [f"{y}-W{w:02d} ({s.date()} → {e.date()})" for (y,w,s,e) in opts]
            if not opt_labels:
                st.warning("No weekly ranges available.")
                return
            sel_idx = st.selectbox("Select Week", opt_labels, index=len(opt_labels)-1)
            chosen = opts[opt_labels.index(sel_idx)]
            start_date, end_date = chosen[2], chosen[3]
            period_multiplier = 6   # per your clarification weekly = 6 days
            period_label = f"{start_date.date()} → {end_date.date()}"

        else:  # Monthly
            df_month = df.copy()
            df_month['year'] = df_month['Date_dt'].dt.year
            df_month['month'] = df_month['Date_dt'].dt.month
            combos = df_month.groupby(['year','month'])['Date_dt'].agg(['min','max']).reset_index()
            opts = []
            for _, r in combos.iterrows():
                y, m = int(r['year']), int(r['month'])
                start = pd.Timestamp(year=y, month=m, day=1).normalize()
                lastday = calendar.monthrange(y, m)[1]
                end = pd.Timestamp(year=y, month=m, day=lastday).normalize()
                opts.append((y, m, start, end))
            opt_labels = [f"{y}-{m:02d} ({calendar.month_name[m]} {y})" for (y,m,_,_) in opts]
            if not opt_labels:
                st.warning("No monthly ranges available.")
                return
            sel_idx = st.selectbox("Select Month", opt_labels, index=len(opt_labels)-1)
            chosen = opts[opt_labels.index(sel_idx)]
            start_date, end_date = chosen[2], chosen[3]
            period_multiplier = 24  # per your clarified monthly = 24 working days
            period_label = f"{calendar.month_name[chosen[1]]} {chosen[0]}"

        top_filter = st.selectbox("Show", ["All", "Top Performers", "Low Performers"])
        selected_person = st.selectbox("Select person (Personal tracker)", ["(none)"] + sorted(df['Rename'].unique()))
        st.markdown("---")
        st.write(f"Per-head daily targets: Maker = **{MAKER_TARGET_DAILY}**, Editor = **{EDITOR_TARGET_DAILY}**")
        st.caption("Targets use fixed multipliers: Daily×1, Weekly×5, Monthly×20 (per your configuration).")

    # Filter by role
    df_view = df if role_filter == "All" else df[df['Role'] == role_filter].copy()

    # Filter timeframe
    mask = (df_view['Date_dt'] >= pd.to_datetime(start_date)) & (df_view['Date_dt'] <= pd.to_datetime(end_date))
    df_period = df_view.loc[mask].copy()

    if df_period.empty:
        st.warning(f"No records for selected period: {period_label}")
        return

    # Per-person aggregation
    agg = _aggregate_for_period(df_period, by='Rename')
    role_map = df_period.groupby('Rename')['Role'].first().reset_index()
    agg = agg.merge(role_map, on='Rename', how='left').rename(columns={'Rename':'Annotator', 'Role':'Role'})

    # Period targets using fixed multipliers
    agg['Daily Target'] = agg['Role'].apply(_daily_target_for_role)
    agg['Period Target'] = agg['Daily Target'] * period_multiplier
    agg['Deficit'] = agg['Total Cuboids'] - agg['Period Target']
    agg['Target Met'] = agg['Deficit'] >= 0

    # Save full-aggregation BEFORE applying top/low filter (used to compute totals correctly)
    agg_full = agg.copy()

    # Apply top/low filter (on aggregated totals) — this affects what's displayed
    if top_filter == "Top Performers":
        agg = agg.sort_values('Total Cuboids', ascending=False).head(10)
    elif top_filter == "Low Performers":
        agg = agg.sort_values('Total Cuboids', ascending=True).head(10)
    else:
        agg = agg.sort_values('Total Cuboids', ascending=False)

    # ---------------- KPIs ----------------
    st.subheader(f"{view_period} Overview — {period_label}")
    col1, col2, col3 = st.columns(3)
    total_team = agg['Total Cuboids'].sum()
    avg_person = agg['Total Cuboids'].mean()
    pct_met = 100.0 * (agg['Target Met'].sum() / len(agg)) if len(agg) > 0 else 0.0
    col1.metric("Team Total (period)", f"{int(total_team):,}")
    col2.metric("Avg per person (period)", f"{avg_person:.1f}")
    col3.metric("% meeting target", f"{pct_met:.1f}%")
    st.write(f"Period length used for targets: **{period_multiplier}** working day(s) (multiplier applied)")

    # ---------------- Production Chart ----------------
    st.markdown("### 🔢 Production & Deficit")
    bar = alt.Chart(agg).mark_bar().encode(
        x=alt.X('Annotator:N', sort='-y'),
        y=alt.Y('Total Cuboids:Q'),
        color=alt.condition(alt.datum['Target Met'] == True, alt.value('#2ca02c'), alt.value('#d62728')),
        tooltip=['Annotator','Role','Total Cuboids','Period Target','Deficit']
    ).properties(height=420)
    st.altair_chart(bar, use_container_width=True)

    # ---------------- Detailed Table with TOTAL row (highlighted) ----------------
    st.markdown("### 📋 Detailed Table")
    # display_df is from agg (which may have been limited by top_filter)
    display_df = agg[['Annotator','Role','Total Cuboids','Period Target','Deficit','Target Met']].copy()

    # ---------- FIXED: compute totals from full aggregation (agg_full) for the same period ----------
    total_cuboids_team = int(agg_full['Total Cuboids'].sum()) if not agg_full.empty else 0

    # Static team period target (Maker + Editor) based on multipliers and role_filter
    if role_filter == "All":
        base_target = (MAKERS_COUNT * MAKER_TARGET_DAILY) + (EDITORS_COUNT * EDITOR_TARGET_DAILY)
    elif role_filter == "Maker":
        base_target = MAKERS_COUNT * MAKER_TARGET_DAILY
    else:  # Editor
        base_target = EDITORS_COUNT * EDITOR_TARGET_DAILY

    if view_period == "Daily":
        team_period_target = base_target * 1
    elif view_period == "Weekly":
        team_period_target = base_target * 6
    else:  # Monthly
        team_period_target = base_target * 24

    # Compute target met count & annotator count from full aggregation (agg_full)
    if not agg_full.empty:
        target_met_count = int((agg_full['Deficit'] >= 0).sum())
        annotator_count_all = int(len(agg_full))
    else:
        target_met_count = 0
        annotator_count_all = 0

    total_row = pd.DataFrame({
        'Annotator': ['TOTAL'],
        'Role': ['-'],
        'Total Cuboids': [total_cuboids_team],
        'Period Target': [team_period_target],
        'Deficit': [int(total_cuboids_team - team_period_target)],
        'Target Met': [f"{target_met_count} / {annotator_count_all}"]
    })

    display_with_total = pd.concat([display_df, total_row], ignore_index=True)

    # Styling helpers
    def highlight_total(row):
        if row['Annotator'] == 'TOTAL':
            return ['background-color: #fff2cc; color: #d62828; font-weight: bold' for _ in row.index]
        else:
            return ['' for _ in row.index]

    def color_deficit(v):
        try:
            # Accept ints/floats and formatted strings like "+1,234" (after formatting may break — but we apply before format)
            val = float(v)
            return 'color: #2ca02c' if val >= 0 else 'color: #d62728'
        except Exception:
            return ''

    # Apply styles: highlight TOTAL row, color Deficit column per value, then format numbers
    styled = (display_with_total.style
              .apply(highlight_total, axis=1)
              .applymap(color_deficit, subset=['Deficit'])
              .format({'Total Cuboids':'{:,}','Period Target':'{:,}','Deficit':'{:+,}'}))

    st.dataframe(styled)

    # ---------------- Compensation Planner ----------------
    st.markdown("### ⚖️ Compensation Planner")
    today = pd.Timestamp.today().normalize()
    # Determine days passed in period (Mon-Sat business days) to calculate remaining days relative to multiplier
    days_passed = _business_days_mon_fri(start_date, min(today, end_date))
    remaining_days = max(period_multiplier - days_passed, 0)
    if remaining_days <= 0:
        st.info("No remaining working days left in this target window (or period ended).")
    else:
        st.write(f"Remaining working days (for compensation): **{remaining_days}**")
        comp = display_df.copy()
        comp['Remaining to meet'] = comp.apply(lambda r: max(r['Period Target'] - r['Total Cuboids'], 0), axis=1)
        comp['Per-day required'] = (comp['Remaining to meet'] / remaining_days).apply(lambda x: int(np.ceil(x)) if x>0 else 0)
        st.dataframe(comp[['Annotator','Role','Total Cuboids','Period Target','Remaining to meet','Per-day required']].style.format({
            'Total Cuboids':'{:,}','Period Target':'{:,}','Remaining to meet':'{:,}'
        }))

    # ---------------- Performers (exactly 1 Maker & 1 Editor for the selected period) ----------------
    st.markdown("### ⭐ Performers")
    if view_period == "Daily":
        day = pd.to_datetime(start_date)
        day_df = df_view[df_view['Date_dt'] == day]
        if day_df.empty:
            st.write("No data for the selected date.")
        else:
            day_sum = day_df.groupby(['Role','Rename'])['Cuboids'].sum().reset_index()
            rows = []
            for r in ['Maker','Editor']:
                r_df = day_sum[day_sum['Role'] == r]
                if not r_df.empty:
                    idx = r_df['Cuboids'].idxmax()
                    rows.append(r_df.loc[idx])
            if rows:
                top_day = pd.DataFrame(rows).rename(columns={'Rename':'Annotator','Cuboids':'Cuboids Done'})[['Role','Annotator','Cuboids Done']]
                st.write(f"**Performer of the Day — {day.date()}**")
                st.dataframe(top_day)
            else:
                st.write("No Maker/Editor records for this date.")
    else:
        period_sum = df_period.groupby(['Role','Rename'])['Cuboids'].sum().reset_index()
        rows = []
        for r in ['Maker','Editor']:
            r_df = period_sum[period_sum['Role'] == r]
            if not r_df.empty:
                idx = r_df['Cuboids'].idxmax()
                rows.append(r_df.loc[idx])
        if rows:
            top_period = pd.DataFrame(rows).rename(columns={'Rename':'Annotator','Cuboids':'Cuboids Done'})[['Role','Annotator','Cuboids Done']]
            label = "Week" if view_period == "Weekly" else "Month"
            st.write(f"**Performer of the {label} — {period_label}**")
            st.dataframe(top_period)
        else:
            st.write("No Maker/Editor records in this period.")

    # ---------------- Personal Progress Tracker ----------------
    st.markdown("### 📊 Personal Progress Tracker")
    if selected_person and selected_person != "(none)":
        p_df = df_view[df_view['Rename'] == selected_person].copy()
        if p_df.empty:
            st.write("No data for selected person in the chosen scope.")
        else:
            p_agg = p_df.groupby('Date_dt')['Cuboids'].sum().reset_index().sort_values('Date_dt')
            line = alt.Chart(p_agg).mark_line(point=True).encode(
                x=alt.X('Date_dt:T', title='Date'),
                y=alt.Y('Cuboids:Q', title='Cuboids'),
                tooltip=['Date_dt','Cuboids']
            ).properties(height=300)
            st.altair_chart(line, use_container_width=True)
            streaks = _compute_streaks(df_view)
            st.info(f"🏅 {selected_person} — longest daily-target streak: **{streaks.get(selected_person,0)}** days")
            recent_total = p_agg[p_agg['Date_dt'] >= pd.to_datetime(start_date)]['Cuboids'].sum()
            person_role = df_view[df_view['Rename'] == selected_person]['Role'].iloc[0] if not df_view[df_view['Rename'] == selected_person].empty else 'Maker'
            st.write(f"Total in period: **{int(recent_total):,}** | Period target: **{_daily_target_for_role(person_role) * period_multiplier:,}**")
    else:
        st.write("Select a person to view personal progress.")

    # ---------------- Leaderboard ----------------
    st.markdown("### 🏆 Leaderboard")
    lb = display_df.copy().sort_values('Total Cuboids', ascending=False).reset_index(drop=True)
    lb['Rank'] = lb.index + 1
    st.table(lb[['Rank','Annotator','Role','Total Cuboids','Deficit']].head(10).style.format({'Total Cuboids':'{:,}','Deficit':'{:+,}'}))

    # ---------------- Badges ----------------
    st.markdown("### 🏅 Badges & Recognition")
    streaks_all = _compute_streaks(df_view)
    for r in lb.head(10).itertuples(index=False):
        annot = r[1]
        cubs = int(r[3])
        s = streaks_all.get(annot, 0)
        medal = "🔥" if s >= 7 else "🏅" if s >= 3 else ""
        if medal:
            st.write(f"{medal} **{annot}** — Total: {cubs:,} | Longest streak: {s} days")

    # ---------------- Decision Summary ----------------
    st.markdown("### 🧠 Decision Summary")
    need_action = display_df[display_df['Deficit'] < 0].sort_values('Deficit')
    if need_action.empty:
        st.success("All team members met targets 🎉")
    else:
        st.warning(f"{len(need_action)} members below target.")
        st.dataframe(need_action[['Annotator','Role','Total Cuboids','Period Target','Deficit']].style.format({
            'Total Cuboids':'{:,}','Period Target':'{:,}','Deficit':'{:+,}'
        }))

   