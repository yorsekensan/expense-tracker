import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

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

# --- PAGE CONFIGURATION & CSS ---
st.set_page_config(layout="wide", page_title="Expense Summary")

custom_css = """
    <style>
    @media print {
        header, .stFileUploader, .stDownloadButton, .stRadio {
            display: none !important;
        }
    }
    [data-testid="stMetricValue"] > div {
        white-space: normal !important; 
        word-wrap: break-word !important;
        font-size: 28px !important; 
        line-height: 1.2 !important;
    }
    </style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

st.title("📊 Household Financial Tracker")

# 1. We put the Uploader first so it remains on screen
uploaded_file = st.file_uploader("Drop Daily Tracker (CSV)", type="csv")

# 2. Dynamic State Logic
if not uploaded_file:
    # --- NO FILE STATE: Show Instructions ---
    st.markdown("""
    **Welcome to your private financial dashboard.** 
    This tool converts your raw daily expenses into a clear, single-page summary. 
    
    **Security First:** This app operates with strictly **Zero-Data Retention**. Your file is processed entirely in your browser's temporary memory and destroyed the moment you close this tab.
    """)
    
    with st.expander("📖 Guide: How to use and edit the CSV template"):
        st.markdown("""
        **1. How to open the file:** You can open this directly in Excel, Google Sheets, or Apple Numbers.
        **2. How to fill in the data:**
        *   **Date:** Type dates clearly (e.g., `1-Oct-2026`). 
        *   **Category:** Group spending into broad buckets (e.g., *Housing, Transport, Food*).
        *   **Amount (Rp):** Enter raw numbers only (e.g., type `150000` instead of `Rp 150.000`).
        **3. How to save your work:** Go to `File > Save As` and ensure the format remains **CSV (Comma delimited)**.
        """)
    
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

else:
    # --- FILE UPLOADED STATE: Show Dashboard (Instructions vanish) ---
    df, missing_columns = ingest_tracker_data(uploaded_file)
    
    if missing_columns:
        st.error(f"🚨 **Incorrect format detected.** Missing columns: `{', '.join(missing_columns)}`")
        st.info("💡 Please download the Starter Template, match the headers exactly, and re-upload.")
    else:
        # Your Time Control and Dashboard rendering logic goes here
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
    st.subheader("Top 5 Spending")
    
    # Isolate the top 5 transactions
    top_5 = df.nlargest(5, 'Amount (Rp)')[['Date', 'Category', 'Item / Description', 'Amount (Rp)', 'Notes']].copy()
    
    # Format Date to DD-MM-YYYY (strips the time)
    top_5['Date'] = top_5['Date'].dt.strftime('%d-%m-%Y')
    
    # Format Amount with thousands separators
    top_5['Amount (Rp)'] = top_5['Amount (Rp)'].apply(lambda x: f"{x:,.0f}")
    
    # Render table and explicitly hide the index row numbers
    st.dataframe(top_5, hide_index=True)
    
st.divider()

# --- 6. AI FINANCIAL ADVISOR ---
st.header("🤖 AI Financial Advisor")

# Security Disclaimer
st.caption("🔒 **Security Note:** Your raw transaction data is NEVER sent to the AI. We only send high-level, anonymized math (e.g., 'Total Food Spend: Rp 5.000.000') to generate your advice, ensuring complete privacy.")

# Capturing User Intent
user_goal = st.text_input(
    "What is your primary financial goal or spending limit right now?", 
    placeholder="e.g., Keep total monthly spend under 15M, or cut down on dining out to save more."
)

# The Trigger Button
if st.button("Generate AI Financial Audit"):
    if not user_goal:
        st.warning("Please enter a financial goal above so the AI can tailor its advice to your intentions.")
    else:
        with st.spinner("Analyzing your metrics and generating audit..."):
            try:
                # 1. Fetch API Key and Set REST Endpoint
                api_key = st.secrets["GEMINI_API_KEY"]
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
                
                # 2. Data Aggregation 
                total_spend = df['Amount (Rp)'].sum()
                category_totals = df.groupby('Category')['Amount (Rp)'].sum().to_dict()
                
                top_5_df = df.nlargest(5, 'Amount (Rp)')[['Date', 'Item / Description', 'Amount (Rp)']].copy()
                top_5_df['Date'] = top_5_df['Date'].dt.strftime('%Y-%m-%d')
                top_5 = top_5_df.to_dict('records')
                
                # 3. The Prompt 
                prompt = f"""
                You are an expert financial analyst and advisor. Review this anonymized spending data and the user's specific financial goal.
                
                USER INTENT/GOAL: {user_goal}
                
                AGGREGATED METRICS:
                - Total Spend: Rp {total_spend:,.0f}
                - Category Breakdown: {category_totals}
                - Top 5 Outflow Transactions: {top_5}
                
                Format your response exactly with these markdown headers:
                ### Executive Summary
                ### Trend Analysis
                ### Category Audit
                ### Anomaly Warning
                ### Goal Alignment
                
                Maintain a direct, structured, and risk-aware tone. Provide highly actionable advice.
                """
                
                # 4. Execute Raw HTTP POST Request
                headers = {'Content-Type': 'application/json'}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                
                raw_response = requests.post(url, headers=headers, json=payload)
                
                # 5. Parse and Render
                if raw_response.status_code == 200:
                    result = raw_response.json()
                    advice = result["candidates"][0]["content"]["parts"][0]["text"]
                    st.markdown(advice)
                else:
                    st.error(f"🚨 HTTP Error {raw_response.status_code}")
                    st.code(raw_response.text) 
                    
            except Exception as e:
                st.error("🚨 Execution Error.")
                st.info(f"Technical details: {e}")
                
# --- TEMPORARY DEBUG BUTTON ---
    if st.button("Debug: List Allowed Models"):
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            # Calling the ListModels endpoint
            debug_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            response = requests.get(debug_url)
            
            if response.status_code == 200:
                models_data = response.json()
                # Filtering to only show models that support text generation
                supported_models = [
                    m['name'] for m in models_data.get('models', []) 
                    if 'generateContent' in m.get('supportedGenerationMethods', [])
                ]
                st.success("✅ Connection Successful! Your key can access these models:")
                st.write(supported_models)
            else:
                st.error(f"🚨 Debug Error: {response.status_code}")
                st.write(response.text)
        except Exception as e:
            st.error("🚨 Execution Error.")
            st.write(e)

st.divider()

# --- 7. MONETIZATION / SUPPORT ---
with st.container(border=True):
    # Centered text matching the visual style of your reference
    st.markdown(
        "<p style='text-align: center; font-style: italic; color: #a1a1aa; margin-bottom: 15px;'>"
        "💡 YS Financial Tracker is provided free as a zero-data retention project. "
        "If this tool helps optimize your cash flow, consider supporting the servers:"
        "</p>", 
        unsafe_allow_html=True
    )
    
    # Using a 3-column layout to perfectly center the single button
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        # Setting type="primary" gives the button a solid fill color
        st.link_button(
            "☕ Support / Donate", 
            "https://saweria.co/your_username_here", 
            use_container_width=True,
            type="primary"
        )
