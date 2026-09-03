import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Arbitrage Lead Dashboard", layout="wide")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Database', 'Deep_Data_Database.csv')

st.title("? Amazon Arbitrage Master Dashboard")
st.markdown("Real-time lead evaluation, profit tracking, and product database.")

def load_data():
    if os.path.exists(DB_PATH):
        return pd.read_csv(DB_PATH)
    return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No scanned leads found yet! Run a scan using `main.py` to populate data.")
else:
    st.sidebar.header("Filter Leads")
    status_filter = st.sidebar.selectbox("Lead Status", ["All", "WINNING_LEAD", "FAIL", "NOT_FOUND", "MISSING_UPC"])
    
    filtered_df = df.copy()
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df['Lead Status'] == status_filter]

    col1, col2, col3 = st.sidebar.columns(3)
    col1.metric("Total Scanned", len(df))
    winning_count = len(df[df['Lead Status'] == 'WINNING_LEAD'])
    col2.metric("Winning Leads", winning_count)
    
    st.subheader(f"Leads View ({status_filter})")
    if 'Amz Link' in filtered_df.columns and 'Source Link' in filtered_df.columns:
        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                "Amz Link": st.column_config.LinkColumn("Amazon Link", display_text="Open Amazon ?"),
                "Source Link": st.column_config.LinkColumn("Source Link", display_text="Open Source ?"),
            }
        )
    else:
        st.dataframe(filtered_df, use_container_width=True)

    if st.button("?? Refresh Data"):
        st.rerun()
