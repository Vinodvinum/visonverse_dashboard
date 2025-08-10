# visionverse_dashboard/src/review_tool.py
import streamlit as st
import pandas as pd

def render_review_tool():
    st.title("👥 Annotation Review Tracker")

    st.markdown("### 📂 Upload Review Datasets or Paste Google Sheet Links")

    # Option 1: Google Sheets CSV links
    st.markdown("#### 🔗 Paste public Google Sheet CSV links")
    maker_url = st.text_input("https://docs.google.com/spreadsheets/d/1kaQl0WpFmjP1a1JAzDBuYfcb2b3GqA1Ah7ouIDCI7dg/edit?gid=0#gid=0")
    editor_url = st.text_input("https://docs.google.com/spreadsheets/d/1G45k_FBUBUCUIp_6YJRMx-_YukE3wFh64qTt7cV6VZ8/edit?gid=0#gid=0")

    # Option 2: Manual file upload fallback
    st.markdown("#### 📁 Or upload CSV files manually")
    maker_file = st.file_uploader("Upload Maker Job Log (CSV)", type=["csv"], key="maker")
    editor_file = st.file_uploader("Upload Editor Job Log (CSV)", type=["csv"], key="editor")

    # Load Maker Data
    maker_df = None
    if maker_url:
        try:
            maker_df = pd.read_csv(maker_url)
            st.success("✅ Maker data loaded from Google Sheets")
        except Exception as e:
            st.error(f"Error loading Maker Sheet: {e}")
    elif maker_file:
        maker_df = pd.read_csv(maker_file)

    if maker_df is not None:
        st.subheader("🛠️ Maker Job Summary")
        maker_df.columns = maker_df.columns.str.strip()
        maker_df['Start date'] = pd.to_datetime(maker_df['Start date'], errors='coerce', dayfirst=True)
        maker_df['End date'] = pd.to_datetime(maker_df['End date'], errors='coerce', dayfirst=True)
        st.dataframe(maker_df)

        if 'Status' in maker_df.columns and 'Job ID' in maker_df.columns:
            summary = maker_df.groupby('Status')['Job ID'].count().reset_index()
            summary.columns = ['Status', 'Count']
            st.markdown("**📊 Maker Job Status Overview:**")
            st.dataframe(summary)

    # Load Editor Data
    editor_df = None
    if editor_url:
        try:
            editor_df = pd.read_csv(editor_url)
            st.success("✅ Editor data loaded from Google Sheets")
        except Exception as e:
            st.error(f"Error loading Editor Sheet: {e}")
    elif editor_file:
        editor_df = pd.read_csv(editor_file)

    if editor_df is not None:
        st.subheader("✍️ Editor Job Summary")
        editor_df.columns = editor_df.columns.str.strip()
        editor_df['Start date'] = pd.to_datetime(editor_df['Start date'], errors='coerce', dayfirst=True)
        editor_df['End date'] = pd.to_datetime(editor_df['End date'], errors='coerce', dayfirst=True)
        st.dataframe(editor_df)

        if 'Status' in editor_df.columns and 'Editing Job ID' in editor_df.columns:
            summary = editor_df.groupby('Status')['Editing Job ID'].count().reset_index()
            summary.columns = ['Status', 'Count']
            st.markdown("**📊 Editor Job Status Overview:**")
            st.dataframe(summary)
# ...existing code...

if __name__ == "__main__":
    render_review_tool()