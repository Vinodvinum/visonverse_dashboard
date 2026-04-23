# visionverse_dashboard/src/data_loader.py
import pandas as pd
import streamlit as st
import os
import re

# Your published Google Sheet CSV link
DEFAULT_GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQI2WohwqGbKw24Q7I1SeVXXlPoL_DDaAmUdq-S2YTonJWPPPp3POsdSRuuTgQjZEZXSBYLxkKZeyEc/pub?gid=0&single=true&output=csv"

def _to_csv_export_url(url: str) -> str:
    """Convert common Google Sheet URLs (edit/share) into a CSV export URL."""
    if not url:
        return DEFAULT_GOOGLE_SHEET_CSV
    if "output=csv" in url or "format=csv" in url:
        return url

    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not m:
        return url

    sheet_id = m.group(1)
    gid_match = re.search(r"[?&]gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

def _get_google_sheet_csv_url() -> str:
    """Resolve URL from Streamlit secrets or env, then normalize to CSV export."""
    configured = None
    try:
        configured = st.secrets.get("GOOGLE_SHEET_URL") or st.secrets.get("GOOGLE_SHEET_CSV")
    except Exception:
        configured = None

    if not configured:
        configured = os.getenv("GOOGLE_SHEET_URL") or os.getenv("GOOGLE_SHEET_CSV")

    return _to_csv_export_url(configured or DEFAULT_GOOGLE_SHEET_CSV)

@st.cache_data(ttl=600)  # Cache for 600 seconds (auto refresh every 10 minutes)
def load_team_data(role_map):
    csv_url = _get_google_sheet_csv_url()
    try:
        df = pd.read_csv(csv_url)
    except Exception as e:
        msg = str(e)
        if "401" in msg or "403" in msg:
            st.error(
                "Google Sheet is not publicly readable as CSV. "
                "Publish/share it for public access, or configure GOOGLE_SHEET_CSV with a working public CSV URL."
            )
        else:
            st.error(f"Failed to load data from Google Sheet: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    df = df[~df['Name'].isin(['TOTAL', 'DEFICIT'])]

    if 'Role' in df.columns:
        raw_date_columns = [col for col in df.columns if col not in ['Name', 'Rename', 'Role']]
    else:
        raw_date_columns = [col for col in df.columns if col not in ['Name', 'Rename']]

    # Google Sheets can emit duplicate headers as .1/.2 suffixes (e.g., Apr-23, Apr-23.1).
    # Keep only the first occurrence per base header to avoid double counting daily totals.
    date_columns = []
    normalized_header = {}
    seen_headers = set()
    for col in raw_date_columns:
        base = re.sub(r'\.\d+$', '', str(col)).strip()
        if not base:
            continue
        if base in seen_headers:
            continue
        seen_headers.add(base)
        date_columns.append(col)
        normalized_header[col] = base

    df_long = df.melt(
        id_vars=[col for col in ['Name', 'Rename', 'Role'] if col in df.columns],
        value_vars=date_columns,
        var_name='Date',
        value_name='Cuboids'
    )

    # Normalize the melted date header back to its base value (strip .1/.2 suffixes).
    df_long['Date'] = df_long['Date'].astype(str).map(normalized_header).fillna(df_long['Date'])

    df_long['Cuboids'] = pd.to_numeric(df_long['Cuboids'], errors='coerce')
    df_long = df_long.dropna(subset=['Cuboids'])

    if 'Role' not in df_long.columns or df_long['Role'].isnull().all():
        df_long['Role'] = df_long['Rename'].map(role_map)
    else:
        df_long['Role'] = df_long['Role'].fillna(df_long['Rename'].map(role_map))

    return df_long
