import streamlit as st
import pandas as pd
import plotly.express as px

def ingest_tracker_data(file_buffer):
    """Reads and cleans the raw daily tracker CSV."""
    # 1. Read the CSV into a DataFrame
    df = pd.read_csv(file_buffer)
    
    # 2. Clean the 'Amount (Rp)' column
    # Strip 'Rp', remove commas, and convert to numeric (float)
    df['Amount (Rp)'] = df['Amount (Rp)'].astype(str).str.replace(r'[Rp,]', '', regex=True).astype(float)
    
    # 3. Standardize the 'Date' column
    # Converts format like '1-Nov-2025' into a computable datetime object
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%Y')
    
    # 4. Sort chronologically to ensure accurate time-series plotting
    df = df.sort_values(by='Date').reset_index(drop=True)
    
    return df

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Expense Summary")
st.title("Household Financial Summary")

# --- 1. INGESTION ZONE ---
uploaded_file = st.file_uploader("Drop Daily Tracker (CSV)", type="csv")

if uploaded_file:
    # Read and clean data in memory
    df = ingest_tracker_data(uploaded_file)
    
    # --- 2. THE TIME CONTROL ---
    view_mode = st.radio("Temporal View:", ["Daily", "Weekly", "Monthly", "Yearly"], horizontal=True)
    
    st.divider()
    
    # --- 3. THE CORE KPIS (Placeholders for now) ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Actual Spend", "Calculation Pending...")
    col2.metric("Projected Run Rate", "Calculation Pending...")
    col3.metric("Average Velocity", "Calculation Pending...")
    
    # --- 4. VISUALIZATIONS ---
    chart_col1, chart_col2 = st.columns([2, 1])
    
    with chart_col1:
        st.subheader(f"{view_mode} Burn Chart")
        
        # Currently plotting raw daily dates. Aggregation logic to follow.
        fig_burn = px.bar(
            df, 
            x='Date', 
            y='Amount (Rp)', 
            labels={'Amount (Rp)': 'Total Spend (IDR)'}
        )
        # Removes the background grid for a cleaner, enterprise look
        fig_burn.update_layout(xaxis_title="", yaxis_title="", plot_bgcolor="rgba(0,0,0,0)") 
        st.plotly_chart(fig_burn, use_container_width=True)
        
    with chart_col2:
        st.subheader("Allocation Breakdown")
        
        # Groups data by Category for the donut chart
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
        
    st.divider()
    
    # --- 5. THE LEDGER ---
    st.subheader("Anomaly Ledger (Top 5 Transactions)")
    # Filters the top 5 largest expenses
    st.dataframe(df.nlargest(5, 'Amount (Rp)')[['Date', 'Category', 'Item / Description', 'Amount (Rp)', 'Notes']])
