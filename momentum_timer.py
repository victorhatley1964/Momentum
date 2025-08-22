import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np

# Note: Alpaca imports are commented out for local testing without credentials.
# from alpaca_trade_api.rest import REST
# from alpaca.data.live import StockDataStream
# import asyncio
# import threading

# --- Page Configuration ---
st.set_page_config(page_title="Momentum Timer", layout="wide")

st.title("📈 Momentum Timer - ETF Ranking Tool with Backtesting and Trading")

# --- Global Settings & Assets ---
ETFS = [
    "SPY", "QQQ", "IWM", "DIA", "EFA",
    "EEM", "VNQ", "GLD", "SLV", "DBC",
    "XLK", "XLF", "XLE", "XLV", "XLY",
    "XLI", "XLB", "XLU", "TLT", "IEF"
]

# --- Core Functions ---
@st.cache_data(show_spinner="Fetching historical data from Yahoo Finance...")
def get_historical_data(tickers, period):
    """
    Fetches and caches historical stock data for a given list of tickers
    and a time period.
    """
    try:
        data = yf.download(tickers, period=period, progress=False)['Adj Close']
        return data.dropna()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame() # Return an empty DataFrame on error

def calculate_momentum(df, lookback):
    """
    Calculates momentum based on a lookback period by comparing the
    latest price to the price 'lookback' days ago.
    """
    # The .shift() function is used to get the price from 'lookback' days ago.
    # The result is a DataFrame where each value is the percentage change.
    return (df / df.shift(lookback) - 1).dropna()

def display_momentum_analysis(momentum_df, lookback_days, display_count):
    """
    Displays the momentum table and bar chart for the top ETFs.
    """
    st.subheader(f"Top {display_count} ETFs by {lookback_days}-Day Momentum")
    st.dataframe(momentum_df.head(display_count), use_container_width=True)

    st.subheader("Momentum Bar Chart")
    st.bar_chart(momentum_df.set_index('ETF').head(display_count))

def display_backtest_chart(data, top_etfs):
    """
    Displays a cumulative returns line chart for a list of top ETFs.
    """
    st.subheader("Backtest Cumulative Returns of Top ETFs")
    
    # Calculate daily percentage change and then cumulative product
    backtest_data = data[top_etfs].pct_change().dropna()
    
    if not backtest_data.empty:
        cum_returns = (1 + backtest_data).cumprod()
        st.line_chart(cum_returns)
    else:
        st.info("Not enough data to perform backtesting for the top ETFs.")


# --- Sidebar UI Controls ---
st.sidebar.header("Settings")
lookback_days = st.sidebar.slider("Lookback Period (Days)", 5, 90, 21)
display_count = st.sidebar.slider("Top N Assets to Display", 5, 20, 10)
backtest_period = st.sidebar.selectbox("Backtest Period", ["3mo", "6mo", "1y", "2y"], index=2)

# Alpaca API Credentials
st.sidebar.header("Alpaca Trading")
use_trading = st.sidebar.checkbox("Enable Live Trading (Paper Account Recommended)")
api_key = st.sidebar.text_input("Alpaca API Key", type="password")
api_secret = st.sidebar.text_input("Alpaca Secret Key", type="password")
endpoint_url = "https://paper-api.alpaca.markets"

# Risk Management
st.sidebar.header("Risk Management")
stop_loss_pct = st.sidebar.slider("Stop-Loss (%)", 1, 20, 5)
take_profit_pct = st.sidebar.slider("Take-Profit (%)", 1, 50, 10)


# --- Main Application Logic ---
# Fetch and analyze data for the main list of ETFs
data = get_historical_data(ETFS, backtest_period)

if not data.empty:
    momentum = calculate_momentum(data, lookback_days)

    # CRITICAL FIX: Gracefully handle an empty momentum DataFrame.
    # This prevents the "IndexError: single positional indexer is out-of-bounds"
    if not momentum.empty:
        latest_momentum = momentum.iloc[-1].sort_values(ascending=False)
        momentum_df = pd.DataFrame({
            'ETF': latest_momentum.index,
            f'{lookback_days}-Day Momentum': latest_momentum.values * 100
        })

        # Display the main results
        display_momentum_analysis(momentum_df, lookback_days, display_count)
        top_etfs = latest_momentum.head(display_count).index
        display_backtest_chart(data, top_etfs)
    else:
        st.warning("Not enough data to calculate momentum. Please adjust the lookback period or backtest period.")
else:
    st.error("No historical data available. Please check the selected period and try again.")


# --- ETF Screener Section ---
st.subheader("ETF Screener")
st.markdown("Select ETFs below to include in your analysis:")
selected_etfs = st.multiselect("Available ETFs", ETFS, default=ETFS[:10])

if selected_etfs:
    data_selected = get_historical_data(selected_etfs, backtest_period)
    if not data_selected.empty:
        momentum_selected = calculate_momentum(data_selected, lookback_days)
        if not momentum_selected.empty:
            latest_selected = momentum_selected.iloc[-1].sort_values(ascending=False)
            st.write(f"Top {len(selected_etfs)} ETFs by Momentum:")
            st.dataframe(latest_selected.to_frame(name='Momentum (%)').head(display_count))
            display_backtest_chart(data_selected, latest_selected.head(len(selected_etfs)).index)
        else:
            st.warning("Not enough data to calculate momentum for selected ETFs. Please reduce the lookback period.")
    else:
        st.error("No historical data available for the selected ETFs.")

# --- Live Trading Section (Future Feature) ---
# This section is currently commented out for safety and to focus on the core functionality.
# You can uncomment and use it with your Alpaca API credentials.
# Note: You will need to install the Alpaca SDK: `pip install alpaca-trade-api`
#
# if use_trading:
#     st.subheader("📤 Place Trades via Alpaca")
#     if not api_key or not api_secret:
#         st.warning("Please enter your Alpaca API keys in the sidebar to enable trading.")
#     else:
#         try:
#             alpaca = REST(api_key, api_secret, base_url=endpoint_url)
#             st.success("Connected to Alpaca Paper Trading")
#
#             allocation = 10000
#             per_trade = allocation / display_count
#             current_prices = yf.download(list(top_etfs), period="1d")['Adj Close'].iloc[-1]
#
#             for etf in top_etfs:
#                 shares = int(per_trade / current_prices[etf])
#                 if shares > 0:
#                     alpaca.submit_order(
#                         symbol=etf,
#                         qty=shares,
#                         side='buy',
#                         type='market',
#                         time_in_force='gtc',
#                         order_class='bracket',
#                         stop_loss={"stop_price": round(current_prices[etf] * (1 - stop_loss_pct / 100), 2)},
#                         take_profit={"limit_price": round(current_prices[etf] * (1 + take_profit_pct / 100), 2)}
#                     )
#                     st.write(f"✅ Buy order with bracket placed: {shares} shares of {etf}")
#
#         except Exception as e:
#             st.error(f"Trading error: {e}")


# --- Footer ---
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
