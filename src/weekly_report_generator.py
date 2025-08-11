# visionverse_dashboard/src/weekly_report_generator.py
import streamlit as st
import pandas as pd
import altair as alt
import calendar

# Keep these constants in sync with performance_dashboard.py
MAKER_TARGET_DAILY = 650
EDITOR_TARGET_DAILY = 1200
MAKERS_COUNT = 20
EDITORS_COUNT = 10
WEEK_WORKING_DAYS = 6  # Mon-Sat

def _parse_dates_for_report(df):
    df = df.copy()
    if 'Date_dt' in df.columns:
        df['Date_dt'] = pd.to_datetime(df['Date_dt'], errors='coerce').dt.normalize()
        return df

    if 'Date' not in df.columns:
        st.error("Input must include 'Date' or 'Date_dt' column.")
        return df

    df['Date_dt'] = pd.to_datetime(df['Date'], errors='coerce')
    if df['Date_dt'].isna().all():
        df['Date_dt'] = pd.to_datetime(df['Date'].astype(str) + ' 2025', errors='coerce')

    df['Date_dt'] = df['Date_dt'].fillna(pd.Timestamp.today().normalize())
    df['Date_dt'] = df['Date_dt'].dt.normalize()
    return df

def render_weekly_report(df):
    st.title("📅 VisonVerse — Weekly Report")

    if df is None or df.empty:
        st.warning("No data provided to Weekly Report.")
        return

    df = df.copy()
    if 'Date' not in df.columns and 'Date_dt' not in df.columns:
        date_cols = [c for c in df.columns if c not in ['Name', 'Rename', 'Role']]
        if date_cols:
            df = df.melt(
                id_vars=[c for c in ['Name', 'Rename', 'Role'] if c in df.columns],
                value_vars=date_cols,
                var_name='Date',
                value_name='Cuboids'
            )

    df = _parse_dates_for_report(df)

    for col in ['Rename', 'Role', 'Cuboids', 'Date_dt']:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            return

    df['Cuboids'] = pd.to_numeric(df['Cuboids'], errors='coerce')
    df = df.dropna(subset=['Cuboids', 'Date_dt'])

    iso = df['Date_dt'].dt.isocalendar()
    df['iso_year'] = iso['year']
    df['iso_week'] = iso['week']

    week_ranges = df.groupby(['iso_year', 'iso_week'])['Date_dt'].agg(['min', 'max']).reset_index()

    opts = []
    for _, r in week_ranges.iterrows():
        y = int(r['iso_year'])
        w = int(r['iso_week'])
        try:
            monday = pd.Timestamp.fromisocalendar(y, w, 1)
        except Exception:
            monday = r['min']
        start = monday.normalize()
        end = (monday + pd.Timedelta(days=WEEK_WORKING_DAYS-1)).normalize()
        label = f"{y}-W{w:02d} ({start.date()} → {end.date()})"
        opts.append((y, w, start, end, label))

    if not opts:
        st.warning("No weekly ranges available.")
        return

    labels = [t[4] for t in opts]
    sel_index = st.selectbox("Select Week", labels, index=len(labels)-1)
    sel_tuple = opts[labels.index(sel_index)]
    sel_year, sel_week, start_date, end_date, sel_label = sel_tuple

    st.subheader(f"Weekly Overview — {sel_label}")

    week_df = df[(df['Date_dt'] >= start_date) & (df['Date_dt'] <= end_date)].copy()
    if week_df.empty:
        st.info("No records found in the selected week range.")
        return

    person_agg = week_df.groupby(['Role', 'Rename'], as_index=False)['Cuboids'].sum().rename(columns={'Cuboids': 'Total Cuboids'})
    person_agg = person_agg.sort_values(['Role', 'Total Cuboids'], ascending=[True, False])

    maker_target_week = MAKER_TARGET_DAILY * WEEK_WORKING_DAYS
    editor_target_week = EDITOR_TARGET_DAILY * WEEK_WORKING_DAYS
    person_agg['Weekly Target'] = person_agg['Role'].apply(
        lambda r: maker_target_week if r == 'Maker' else editor_target_week
    )
    person_agg['Deficit'] = person_agg['Total Cuboids'] - person_agg['Weekly Target']

    st.markdown("### ⚠️ Individuals Below Target")
    deficit_people = person_agg[person_agg['Deficit'] < 0]
    if deficit_people.empty:
        st.success("🎉 All annotators met or exceeded their weekly targets!")
    else:
        for _, row in deficit_people.iterrows():
            st.warning(
                f"📩 **{row['Rename']}** ({row['Role']}) is below target by "
                f"**{abs(int(row['Deficit'])):,}** cuboids this week."
            )

    role_totals = person_agg.groupby('Role', as_index=False)['Total Cuboids'].sum()
    team_total = int(role_totals['Total Cuboids'].sum())

    top_rows = []
    for role in ['Maker', 'Editor']:
        r_df = person_agg[person_agg['Role'] == role]
        if not r_df.empty:
            top_idx = r_df['Total Cuboids'].idxmax()
            top_rows.append(r_df.loc[top_idx])
    top_df = pd.DataFrame(top_rows)

    maker_team_target = maker_target_week * MAKERS_COUNT
    editor_team_target = editor_target_week * EDITORS_COUNT
    team_period_target = maker_team_target + editor_team_target

    summary = [
        {
            'Role': 'Maker',
            'Per-head target': maker_target_week,
            'Team target': maker_team_target,
            'Actual total': int(role_totals[role_totals['Role'] == 'Maker']['Total Cuboids'].sum()) if 'Maker' in role_totals['Role'].values else 0,
            'Deficit': int(role_totals[role_totals['Role'] == 'Maker']['Total Cuboids'].sum()) - maker_team_target
        },
        {
            'Role': 'Editor',
            'Per-head target': editor_target_week,
            'Team target': editor_team_target,
            'Actual total': int(role_totals[role_totals['Role'] == 'Editor']['Total Cuboids'].sum()) if 'Editor' in role_totals['Role'].values else 0,
            'Deficit': int(role_totals[role_totals['Role'] == 'Editor']['Total Cuboids'].sum()) - editor_team_target
        }
    ]
    summary_df = pd.DataFrame(summary)

    def highlight_deficit(val):
        color = 'background-color: #ffcccc' if val < 0 else ''
        return color

    st.markdown("### 📋 Person-level totals (Mon → Sat)")
    st.dataframe(
        person_agg.style.format({'Total Cuboids': '{:,}', 'Weekly Target': '{:,}', 'Deficit': '{:+,}'})
        .applymap(lambda v: 'color: red;' if v < 0 else ('color: green;' if v > 0 else ''), subset=['Deficit'])

    )

    csv_person = person_agg.to_csv(index=False)
    st.download_button(label="Download person-level CSV", data=csv_person, file_name=f"weekly_persons_{sel_year}_W{sel_week:02d}.csv", mime="text/csv")

    st.markdown("### 📊 Role summary & targets")
    st.dataframe(summary_df.style.format({'Per-head target': '{:,}', 'Team target': '{:,}', 'Actual total': '{:,}', 'Deficit': '{:+,}'}))

    csv_summary = summary_df.to_csv(index=False)
    st.download_button(label="Download role-summary CSV", data=csv_summary, file_name=f"weekly_summary_{sel_year}_W{sel_week:02d}.csv", mime="text/csv")

    col1, col2, col3 = st.columns(3)
    col1.metric("Team Actual (period)", f"{team_total:,}")
    col2.metric("Team Target (period)", f"{team_period_target:,}")
    deficit_all = team_total - team_period_target
    col3.metric("Team Deficit", f"{deficit_all:+,}")

    st.markdown("### 🏆 Top performers (this week)")
    if not top_df.empty:
        st.table(top_df.rename(columns={'Rename': 'Annotator', 'Total Cuboids': 'Cuboids Done'}).set_index('Role'))
    else:
        st.write("No Maker/Editor records to show top performers.")

    st.markdown("### 📈 Top 10 Annotators (by cuboids)")
    top10 = person_agg.sort_values('Total Cuboids', ascending=False).head(10)
    if not top10.empty:
        chart = alt.Chart(top10).mark_bar().encode(
            x=alt.X('Total Cuboids:Q'),
            y=alt.Y('Rename:N', sort='-x'),
            color='Role:N',
            tooltip=['Rename', 'Role', 'Total Cuboids']
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.write("No data for chart.")

    st.caption(f"Week treated as Mon → Sat ({WEEK_WORKING_DAYS} working days). Per-head targets: Maker {MAKER_TARGET_DAILY} × {WEEK_WORKING_DAYS} = {maker_target_week}, Editor {EDITOR_TARGET_DAILY} × {WEEK_WORKING_DAYS} = {editor_target_week}.")
