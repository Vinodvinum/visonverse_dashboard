import pandas as pd
import streamlit as st

# Mapping of sheet names to their gid values
SHEET_GID_MAP = {
    "Mukund": "70577254",
    "Sharath": "979318921",
    "Ravi": "1901345413",
    "Danny": "722288006",
    "Nisha": "859289733",
    "Sushma": "1902555227",
    "Sowjanya": "1919545117",
    "Ramesh": "271203623",
    "Nithin": "1546359539"
}

BASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ9liiuyZqTQ7g13ORQMgdxZbTbQ2HZ1NQH8SE5ibVfn2N9AgtszltWd9-cjZKtj4gI1VnTaR_ZpoNH/pub?gid={gid}&single=true&output=csv"

@st.cache_data(ttl=600)
def load_quality_data(sheet_name="Sheet1"):
    gid = SHEET_GID_MAP.get(sheet_name, "0")
    url = BASE_URL.format(gid=gid)
    try:
        df = pd.read_csv(url)
    except Exception as e:
        st.error(f"Failed to load quality data: {e}")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        "Telus Names": "Rename",
        "JOB_ID": "Job ID",
        "Total Cuboids From Makers": "Total Cuboids",
        "Missing Cuboids Annotated": "Missing Cuboids",
        "Geometry Score": "Geometry",
        "BL Score": "BL",
        "DI Score": "DI",
        "Status Score": "Status",
        "Visibilty Score": "Visibility",
        "Submission Date": "Date",
        "Class Score": "Class"   # <-- Add this line
    })

    keep_cols = [
        "Rename", "Job ID", "Total Cuboids", "Missing Cuboids", "Geometry", "BL", "DI", "Status", "Visibility", "Class", "Date", "Date_dt"
    ]
    df = df[[col for col in keep_cols if col in df.columns]]

    return df