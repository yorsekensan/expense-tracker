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
    # Tells Pandas to auto-detect the date format, and converts unreadable text/blanks into null values instead of crashing
    df['Date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')

    # Drops any rows where the date was null (e.g., empty rows at the bottom of the CSV)
    df = df.dropna(subset=['Date'])
    
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
    st.subheader("Anomaly Ledger (Top 5 Transactions)")
    
    # Isolate the top 5 transactions
    top_5 = df.nlargest(5, 'Amount (Rp)')[['Date', 'Category', 'Item / Description', 'Amount (Rp)', 'Notes']].copy()
    
    # Format Date to DD-MM-YYYY (strips the time)
    top_5['Date'] = top_5['Date'].dt.strftime('%d-%m-%Y')
    
    # Format Amount with thousands separators
    top_5['Amount (Rp)'] = top_5['Amount (Rp)'].apply(lambda x: f"{x:,.0f}")
    
    # Render table and explicitly hide the index row numbers
    st.dataframe(top_5, hide_index=True)
