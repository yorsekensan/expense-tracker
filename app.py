import streamlit as st
import pandas as pd
import plotly.express as px

def ingest_tracker_data(file_buffer):
    """Reads, validates, and cleans the raw daily tracker CSV."""
    df = pd.read_csv(file_buffer)
    
    # 1. The Validation Gatekeeper
    required_cols = ['Date', 'Category', 'Item / Description', 'Amount (Rp)', 'Notes']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        # Returns empty data and a list of the missing columns
        return None, missing_cols
        
    # 2. Clean the Data (Only executes if validation passes)
    df['Amount (Rp)'] = df['Amount (Rp)'].astype(str).str.replace(r'[Rp,]', '', regex=True).astype(float)
    df['Date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
    df = df.dropna(subset=['Date'])
    df = df.sort_values(by='Date').reset_index(drop=True)
    
    return df, []

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Expense Summary")

# Injecting CSS to fix metric truncation and hide UI when printing
custom_css = """
    <style>
    /* Hide UI for PDF Print */
    @media print {
        header, .stFileUploader, .stDownloadButton, .stRadio {
            display: none !important;
        }
    }
    
    /* Fix Metric Truncation on Mobile/Mac */
    [data-testid="stMetricValue"] > div {
        white-space: normal !important; 
        word-wrap: break-word !important;
        font-size: 28px !important; 
        line-height: 1.2 !important;
    }
    </style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 0. HOMEPAGE & INSTRUCTIONS ---
st.title("📊 Household Financial Tracker")
st.markdown("""
**Welcome to your private financial dashboard.** 
This tool converts your raw daily expenses into a clear, single-page summary. 

**Security First:** This app operates with strictly **Zero-Data Retention**. Your file is processed entirely in your browser's temporary memory. It is never saved to a database, and the data is completely destroyed the moment you close this tab.
""")

with st.expander("📖 Guide: How to use and edit the CSV template"):
    st.markdown("""
    **1. How to open the file:**
    Even though it is a `.csv` (Comma Separated Values) file, you do not need special software. You can open it directly in **Microsoft Excel, Google Sheets, or Apple Numbers** just like a normal spreadsheet.
    
    **2. How to fill in the data:**
    *   **Date:** Type your dates clearly (e.g., `1-Oct-2026`). 
    *   **Category:** Group your spending into broad buckets (e.g., *Housing, Transport, Food, Utilities*). Using consistent categories creates the best pie charts.
    *   **Amount (Rp):** Enter raw numbers only. Do not type "Rp" or add dots/commas (e.g., type `150000` instead of `Rp 150.000`). The app will format it for you.
    *   **Notes & Others:** Use these for your own context, or leave them blank.
    
    **3. How to save your work:**
    When you are done logging your expenses, go to `File > Save As` and ensure the file format remains **CSV (Comma delimited)**. Do not save it as a standard `.xlsx` Excel workbook, or the application will not be able to read it.
    """)

# The 3-Row Example Template
template_csv = (
    "Month,Date,Category,Item / Description,Amount (Rp),Notes,Split,Review\n"
    "October 2026,1-Oct-2026,Utilities,Monthly Internet Bill,350000,Person A,Yes,Yes\n"
    "October 2026,3-Oct-2026,Food & Lifestyle,Weekly Groceries,450000,Person B,Yes,Yes\n"
    "October 2026,5-Oct-2026,Transport,Train Ticket,150000,Person A,No,Yes"
)

st.download_button(
    label="📥 Download Starter Template (CSV)", 
    data=template_csv, 
    file_name="spending_tracker_template.csv", 
    mime="text/csv"
)

st.divider()

# --- 1. INGESTION ZONE ---
st.markdown("### Upload Your Data")
st.info("💡 **Pro Tip:** To share this dashboard with your household, adjust the time toggle to your preference, then press `Ctrl + P` (or `Cmd + P`) to save a clean, UI-free PDF.")
uploaded_file = st.file_uploader("Drop Daily Tracker (CSV)", type="csv")

if uploaded_file:
    # Pass the file through the gatekeeper
    df, missing_columns = ingest_tracker_data(uploaded_file)
    
    if missing_columns:
        # Gracefully halt and warn the user
        st.error(f"🚨 **Incorrect format detected.** Your file is missing the following required columns: `{', '.join(missing_columns)}`")
        st.info("💡 **How to fix:** Please download the Starter Template above, ensure your column headers match exactly, and re-upload.")
    else:
        # --- 2. THE TIME CONTROL --- (Proceed with the dashboard as normal)
        view_mode = st.radio("Temporal View:", ["Daily", "Weekly", "Monthly", "Yearly"], horizontal=True)
        
        # ... (The rest of your dashboard code remains exactly the same below this line)
    
    st.divider()
    
# --- 3. DYNAMIC AGGREGATION & KPIS ---
    
    # Map the radio button to a Pandas frequency string
    freq_map = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS", "Yearly": "YS"}
    selected_freq = freq_map[view_mode]
    
    # Aggregate data for the Burn Chart based on the selected timeframe
    df_time = df.groupby(pd.Grouper(key='Date', freq=selected_freq))['Amount (Rp)'].sum().reset_index()
    
    # Calculate the math for the KPIs
    total_spend = df['Amount (Rp)'].sum()
    
    # Determine the total span of days in the uploaded dataset to calculate accurate velocity
    total_days = (df['Date'].max() - df['Date'].min()).days
    total_days = total_days if total_days > 0 else 1 # Prevent division by zero if only 1 day is uploaded
    
    daily_velocity = total_spend / total_days
    projected_yearly = daily_velocity * 365
    period_average = df_time['Amount (Rp)'].mean()
    
    # Render the Core KPIs (Formatted with commas for readability)
    col1, col2, col3 = st.columns(3)
    col1.metric("Actual Spend (Total)", f"Rp {total_spend:,.0f}")
    col2.metric("Projected Yearly Run Rate", f"Rp {projected_yearly:,.0f}")
    col3.metric(f"Average {view_mode} Velocity", f"Rp {period_average:,.0f}")
    
# --- 4. VISUALIZATIONS ---
    chart_col1, chart_col2 = st.columns([2, 1])
    
    with chart_col1:
        st.subheader(f"{view_mode} Burn Chart")
        
        # Now plotting the dynamically aggregated df_time instead of raw df
        fig_burn = px.bar(
            df_time, 
            x='Date', 
            y='Amount (Rp)', 
            labels={'Amount (Rp)': 'Total Spend (IDR)'}
        )
        # Removes the background grid for a cleaner, enterprise look
        fig_burn.update_layout(xaxis_title="", yaxis_title="", plot_bgcolor="rgba(0,0,0,0)") 
        st.plotly_chart(fig_burn, use_container_width=True)
        
    with chart_col2:
        st.subheader("Allocation Breakdown")
        
        # Groups raw data by Category for the donut chart
        df_category = df.groupby('Category', as_index=False)['Amount (Rp)'].sum()
        
        fig_allocation = px.pie(
            df_category, 
            values='Amount (Rp)', 
            names='Category', 
            hole=0.4 # Creates the "donut" style
        )
        fig_allocation.update_traces(textposition='inside', textinfo='percent+label')
        fig_allocation.update_layout(showlegend=False) # Hides legend to save space
        
        st.plotly_chart(fig_allocation, use_container_width=True)

# --- 5. THE LEDGER ---
    st.subheader("Top 5 Spending")
    
    # Isolate the top 5 transactions
    top_5 = df.nlargest(5, 'Amount (Rp)')[['Date', 'Category', 'Item / Description', 'Amount (Rp)', 'Notes']].copy()
    
    # Format Date to DD-MM-YYYY (strips the time)
    top_5['Date'] = top_5['Date'].dt.strftime('%d-%m-%Y')
    
    # Format Amount with thousands separators
    top_5['Amount (Rp)'] = top_5['Amount (Rp)'].apply(lambda x: f"{x:,.0f}")
    
    # Render table and explicitly hide the index row numbers
    st.dataframe(top_5, hide_index=True)
