import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from data_manager import DataManager
from data_collector import DataCollector
from portfolio_manager import PortfolioManager

# Page Config
st.set_page_config(page_title="ETF Portfolio Tracker", layout="wide")

# Initialize Classes
# TODO: Add logic to toggle between local/google sheets based on user config or environment
data_manager = DataManager(file_path="portfolio.xlsx") 
data_collector = DataCollector()
portfolio_manager = PortfolioManager()

# Title
st.title("📈 장&손&이 자식들 대학보내기 프로젝트")

# Sidebar
with st.sidebar:
    st.header("Settings")
    if st.button("🔄 Refresh Prices"):
        st.cache_data.clear()
        st.rerun()
    
    st.info("Edit 'portfolio.xlsx' to update holdings.")
    
    # Download Button for Manual Git Sync
    with open("portfolio.xlsx", "rb") as f:
        st.download_button(
            label="📥 Download Portfolio.xlsx",
            data=f,
            file_name="portfolio.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download the file, commit it to Git, and push to save changes permanently."
        )

# Load Data
try:
    portfolio_df = data_manager.load_portfolio()
    history_df = data_manager.load_history()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Main Logic
if not portfolio_df.empty:
    # Fetch Prices
    with st.spinner("Fetching current prices..."):
        # We cache this function to avoid spamming the API on every interaction
        # In a real app, we might use st.cache_data with a TTL
        prices = data_collector.fetch_prices_for_portfolio(portfolio_df)
    
    # Calculate Valuations
    valued_df, total_value = portfolio_manager.calculate_valuations(portfolio_df, prices)
    
    # Calculate Key Metrics
    if not history_df.empty:
        last_record = history_df.iloc[-1]
        prev_total = last_record['Total_Asset']
        daily_change = total_value - prev_total
        daily_return = (daily_change / prev_total) * 100 if prev_total > 0 else 0
    else:
        daily_change = 0
        daily_return = 0

    # --- Dashboard Layout ---

    # Top Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Asset Value", f"₩{total_value:,.0f}", f"{daily_change:,.0f} ₩")
    col2.metric("Daily Return", f"{daily_return:.2f}%")
    col3.metric("Asset Count", f"{len(portfolio_df)}")
    
    # Action Button
    if st.button("💾 Record Today's Value"):
        today = datetime.date.today().isoformat()
        # Check if today is already recorded
        if not history_df.empty and history_df.iloc[-1]['Date'] == today:
             st.warning("Today's record already exists.")
        else:
            data_manager.append_history(today, total_value, daily_return, "Manual Record")
            st.success("Recorded successfully!")
            st.rerun()

    # Charts & Tables
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("Portfolio Allocation")
        fig_pie = px.pie(valued_df, values='Current_Value', names='Category', title='By Category', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_right:
        st.subheader("Asset History")
        if not history_df.empty:
            # Convert Date to datetime for better plotting
            plot_history = history_df.copy()
            plot_history['Date'] = pd.to_datetime(plot_history['Date'])
            fig_line = px.line(plot_history, x='Date', y='Total_Asset', title='Total Asset Value Trend')
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No history data available yet.")

    # Detailed Table
    st.subheader("Holdings Detail")
    
    # Formatting for display
    display_df = valued_df[['Ticker', 'Name', 'Category', 'Quantity', 'Current_Price', 'Current_Value', 'Current_Weight', 'Target_Weight']].copy()
    display_df['Current_Weight'] = display_df['Current_Weight'].map('{:.2%}'.format)
    display_df['Target_Weight'] = display_df['Target_Weight'].map('{:.2%}'.format)
    display_df['Current_Price'] = display_df['Current_Price'].map('₩{:,.0f}'.format)
    display_df['Current_Value'] = display_df['Current_Value'].map('₩{:,.0f}'.format)
    
    st.dataframe(display_df, use_container_width=True)

    # Rebalancing Section
    st.markdown("---")
    st.subheader("⚖️ Rebalancing Simulation")
    
    with st.expander("Show Rebalancing Plan"):
        invest_amount = st.number_input("Aditional Investment Amount (₩)", min_value=0, value=0, step=10000)
        
        rebal_df = portfolio_manager.calculate_rebalancing(valued_df, total_value, invest_amount)
        
        # Filter only needed columns
        rebal_display = rebal_df[['Ticker', 'Name', 'Target_Weight', 'Current_Value', 'Target_Value', 'Difference', 'Action', 'Units_To_Trade']]
        
        # Styling
        def color_action(val):
            color = 'green' if val == 'BUY' else ('red' if val == 'SELL' else 'black')
            return f'color: {color}; font-weight: bold'
            
        st.dataframe(
            rebal_display.style.applymap(color_action, subset=['Action'])
            .format({
                'Current_Value': '₩{:,.0f}', 
                'Target_Value': '₩{:,.0f}',
                'Difference': '₩{:,.0f}',
                'Units_To_Trade': '{:.2f}'
            }),
            use_container_width=True
        )

else:
    st.warning("Portfolio is empty. Please add assets to 'portfolio.xlsx'.")
