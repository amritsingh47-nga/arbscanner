import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Arbitrage Command Center", layout="wide")

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "Database", "Deep_Data_Database.csv"
)

st.title("Amazon Arbitrage Command Center")
st.markdown(
    "Real-time lead scoring, profit calculations, and product inventory tracker."
)
st.markdown("---")


def load_data():
    if os.path.exists(DB_PATH):
        df = pd.read_csv(DB_PATH)
        df = df.fillna("N/A")
        return df
    return pd.DataFrame()


df = load_data()

if df.empty:
    st.warning("No scanned leads found yet! Run a scan using main.py to populate data.")
else:
    st.sidebar.header("Filter Controls")
    status_filter = st.sidebar.selectbox(
        "Lead Status Filter",
        ["All", "WINNING_LEAD", "FAIL", "NOT_FOUND", "MISSING_UPC"],
    )

    filtered_df = df.copy()
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Lead Status"] == status_filter]

    total_leads = len(df)
    winning_leads = len(df[df["Lead Status"] == "WINNING_LEAD"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Scanned", str(total_leads))
    col2.metric("Winning Leads", str(winning_leads))
    col3.metric("Filtered Leads", str(len(filtered_df)))

    st.markdown("### Scanned Inventory Cards")

    if filtered_df.empty:
        st.info("No items match the selected filter.")
    else:
        for index, row in filtered_df.iterrows():
            title = str(row.get("Product Title", "Unknown Title"))
            amz_link = str(row.get("Amz Link", ""))
            src_link = str(row.get("Source Link", ""))

            # Product title as clickable link to Amazon if valid
            if amz_link and amz_link != "N/A" and amz_link.startswith("http"):
                title_html = f'<a href="{amz_link}" target="_blank" style="color: #58a6ff; text-decoration: none;">{title} ?</a>'
            else:
                title_html = f'<span style="color: #58a6ff;">{title}</span>'

            st.markdown(
                f"""
            <div style="background-color: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px; word-break: break-word;">
                <h3 style="margin: 0 0 10px 0;">{title_html}</h3>
                <p style="color: #8b949e; font-size: 14px; margin-bottom: 15px;">
                    <b>Category:</b> {row.get('Category', 'N/A')} | 
                    <b>Scanned:</b> {row.get('Date Scanned', 'N/A')} | 
                    <b>UPC:</b> {row.get('UPC', 'N/A')}
                </p>
                <p style="color: #c9d1d9; font-size: 13px; margin-bottom: 15px;">
                    <b>Description:</b> {row.get('Description', 'N/A')}
                </p>
                <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; background-color: #0d1117; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
                    <div><span style="color: #8b949e; font-size: 12px;">STATUS</span><br/><b>{row.get('Lead Status', 'N/A')}</b></div>
                    <div><span style="color: #8b949e; font-size: 12px;">BUY COST</span><br/><b>{row.get('Buy Cost', 'N/A')}</b></div>
                    <div><span style="color: #8b949e; font-size: 12px;">AMZ PRICE</span><br/><b>{row.get('Amz Price', 'N/A')}</b></div>
                    <div><span style="color: #8b949e; font-size: 12px;">NET PROFIT</span><br/><b>{row.get('Net Profit', 'N/A')}</b></div>
                    <div><span style="color: #8b949e; font-size: 12px;">ROI / MARGIN</span><br/><b>{row.get('ROI %', 'N/A')} / {row.get('Margin %', 'N/A')}</b></div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 13px; color: #8b949e; margin-bottom: 15px;">
                    <div><b>Weight:</b> {row.get('Weight', 'N/A')}</div>
                    <div><b>Sales:</b> {row.get('Monthly Sales', 'N/A')}</div>
                    <div><b>Rating:</b> {row.get('Rating', 'N/A')} ({row.get('Reviews', 'N/A')} reviews)</div>
                    <div><b>Break-Even:</b> {row.get('Break-Even', 'N/A')}</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

            if src_link and src_link != "N/A" and src_link.startswith("http"):
                st.markdown(
                    f'<a href="{src_link}" target="_blank" style="margin-right: 15px; color: #3399ff; font-size: 13px;">Open Source Supplier Page ?</a>',
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Refresh Data"):
        st.rerun()
