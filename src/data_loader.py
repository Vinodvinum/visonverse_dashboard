# visionverse_dashboard/src/data_loader.py
import pandas as pd
import streamlit as st

# Your published Google Sheet CSV link
GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQI2WohwqGbKw24Q7I1SeVXXlPoL_DDaAmUdq-S2YTonJWPPPp3POsdSRuuTgQjZEZXSBYLxkKZeyEc/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=600)  # Cache for 600 seconds (auto refresh every 10 minutes)
def load_team_data(role_map):
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV)
    except Exception as e:
        st.error(f"Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    df = df[~df['Name'].isin(['TOTAL', 'DEFICIT'])]

    if 'Role' in df.columns:
        date_columns = [col for col in df.columns if col not in ['Name', 'Rename', 'Role']]
    else:
        date_columns = [col for col in df.columns if col not in ['Name', 'Rename']]

    df_long = df.melt(
        id_vars=[col for col in ['Name', 'Rename', 'Role'] if col in df.columns],
        value_vars=date_columns,
        var_name='Date',
        value_name='Cuboids'
    )

    df_long['Cuboids'] = pd.to_numeric(df_long['Cuboids'], errors='coerce')
    df_long = df_long.dropna(subset=['Cuboids'])

    if 'Role' not in df_long.columns or df_long['Role'].isnull().all():
        df_long['Role'] = df_long['Rename'].map(role_map)
    else:
        df_long['Role'] = df_long['Role'].fillna(df_long['Rename'].map(role_map))

    return df_long
