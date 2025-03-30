import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Trial Balance Classifier", layout="wide")
st.title("📊 Trial Balance to P&L and Balance Sheet Generator")

# --- Upload Inputs ---
trial_balance_file = st.file_uploader("Upload Trial Balance Excel", type=["xlsx"])
ranges_file = st.file_uploader("Upload Ranges Excel (Optional)", type=["xlsx"])

def extract_code_and_name(row):
    parts = str(row).split(" - ", 1)
    if len(parts) == 2 and parts[0].strip().isdigit():
        return int(parts[0].strip()), parts[1].strip()
    return np.nan, np.nan

def classify_with_ranges(code, ranges_df):
    for _, row in ranges_df.iterrows():
        if row["From Range"] <= code <= row["To Range"]:
            return row["Catogiry"]
    return "Unclassified"

def get_default_ranges():
    return pd.DataFrame([
        {"Catogiry": "Non Current Assets", "From Range": 100000, "To Range": 109999},
        {"Catogiry": "Current Assets", "From Range": 110000, "To Range": 119999},
        {"Catogiry": "Other Assets", "From Range": 120000, "To Range": 129999},
        {"Catogiry": "Non Current Liabilities", "From Range": 200000, "To Range": 209999},
        {"Catogiry": "Current Liabilities", "From Range": 210000, "To Range": 219999},
        {"Catogiry": "Equity", "From Range": 300000, "To Range": 309999},
        {"Catogiry": "Income", "From Range": 400000, "To Range": 409999},
        {"Catogiry": "Direct Expenses", "From Range": 500000, "To Range": 509999},
        {"Catogiry": "Indirect Expenses", "From Range": 510000, "To Range": 599999},
    ])

if trial_balance_file:
    # Load trial balance, skip title rows
    df_raw = pd.read_excel(trial_balance_file, sheet_name="Input", skiprows=5)
    df_raw = df_raw.rename(columns={"c": "Account", "Total": "Amount"})

    # Extract code and name
    df_raw[["Code", "Account Name"]] = df_raw["Account"].apply(lambda x: pd.Series(extract_code_and_name(x)))
    df_tb = df_raw.dropna(subset=["Code"]).copy()
    df_tb["Code"] = df_tb["Code"].astype(int)
    df_tb["Amount"] = pd.to_numeric(df_tb["Amount"], errors="coerce").fillna(0)

    # Load ranges or use default
    if ranges_file:
        ranges_df = pd.read_excel(ranges_file, sheet_name=0)
        ranges_df.columns = ranges_df.columns.str.strip()
        ranges_df = ranges_df.dropna(subset=["Catogiry", "From Range", "To Range"])
        ranges_df["From Range"] = ranges_df["From Range"].astype(int)
        ranges_df["To Range"] = ranges_df["To Range"].astype(int)
    else:
        ranges_df = get_default_ranges()

    # Classification
    df_tb["Category"] = df_tb["Code"].apply(lambda x: classify_with_ranges(x, ranges_df))

    # Output views
    st.subheader("Classified Trial Balance")
    st.dataframe(df_tb, use_container_width=True)

    # Prepare P&L and Balance Sheet
    pnl_cats = ["Income", "Direct Expenses", "Indirect Expenses"]
    bs_cats = [c for c in ranges_df["Catogiry"].unique() if c not in pnl_cats]

    df_pnl = df_tb[df_tb["Category"].isin(pnl_cats)].copy()
    df_bs = df_tb[df_tb["Category"].isin(bs_cats)].copy()

    st.subheader("Profit and Loss")
    st.dataframe(df_pnl[["Account Name", "Amount", "Category"]], use_container_width=True)

    st.subheader("Balance Sheet")
    st.dataframe(df_bs[["Account Name", "Amount", "Category"]], use_container_width=True)

    # Export to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_tb.to_excel(writer, sheet_name='Classified Trial Balance', index=False)
        df_pnl.to_excel(writer, sheet_name='Profit and Loss', index=False)
        df_bs.to_excel(writer, sheet_name='Balance Sheet', index=False)

    st.download_button("📥 Download Excel Report", data=output.getvalue(), file_name="Accounting_Report.xlsx")
