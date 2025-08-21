import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from alpaca_trade_api.rest import REST, TimeFrame
from alpaca_trade_api.stream import Stream
import asyncio
import threading

st.set_page_config(page_title="Momentum Timer", layout="wide")

st.title("📈 Momentum Timer - ETF Ranking Tool with Backtesting and Trading")

# Asset list (20 ETFs)
etfs = [
    "SPY", "QQQ", "IWM", "DIA", "EFA",
    "EEM", "VNQ", "GLD", "SLV", "DBC",
    "XLK", "XLF", "XLE", "XLV", "XLY",
    "XLI", "XLB", "XLU", "TLT", "IEF"
]

# Sidebar controls
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

# Fetch historical data for backtesting
data = yf.download(etfs, period=backtest_period)['Adj Close']
data = data.dropna()

# Calculate momentum scores
def calculate_momentum(df, lookback):
    return (df / df.shift(lookback) - 1).dropna()

momentum = calculate_momentum(data, lookback_days)
latest_momentum = momentum.iloc[-1].sort_values(ascending=False)

momentum_df = pd.DataFrame({
    'ETF': latest_momentum.index,
    f'{lookback_days}-Day Momentum': latest_momentum.values * 100
})

# Display momentum table
st.subheader(f"Top {display_count} ETFs by {lookback_days}-Day Momentum")
st.dataframe(momentum_df.head(display_count), use_container_width=True)

# Bar chart
st.subheader("Momentum Bar Chart")
st.bar_chart(momentum_df.set_index('ETF').head(display_count))

# Backtest performance of top ETFs
st.subheader("Backtest Cumulative Returns of Top ETFs")
top_etfs = latest_momentum.head(display_count).index
backtest_data = data[top_etfs].pct_change().dropna()
cum_returns = (1 + backtest_data).cumprod()
st.line_chart(cum_returns)

# ETF Screener
st.subheader("ETF Screener")
st.markdown("Select ETFs below to include in your analysis:")
selected_etfs = st.multiselect("Available ETFs", etfs, default=etfs[:10])

# Rerun analysis with selected ETFs if different from default
if selected_etfs:
    data_selected = yf.download(selected_etfs, period=backtest_period)['Adj Close'].dropna()
    momentum_selected = calculate_momentum(data_selected, lookback_days)
    latest_selected = momentum_selected.iloc[-1].sort_values(ascending=False)
    st.write(f"Top {len(selected_etfs)} ETFs by Momentum:")
    st.dataframe(latest_selected.to_frame(name='Momentum (%)').head(display_count))
    st.line_chart((1 + data_selected[selected_etfs].pct_change().dropna()).cumprod())

# Live Trading Section
if use_trading and api_key and api_secret:
    st.subheader("📤 Place Trades via Alpaca")
    try:
        alpaca = REST(api_key, api_secret, base_url=endpoint_url)
        st.success("Connected to Alpaca Paper Trading")

        allocation = 10000
        per_trade = allocation / display_count
        current_prices = yf.download(list(top_etfs), period="1d")['Adj Close'].iloc[-1]

        for etf in top_etfs:
            shares = int(per_trade / current_prices[etf])
            if shares > 0:
                alpaca.submit_order(
                    symbol=etf,
                    qty=shares,
                    side='buy',
                    type='market',
                    time_in_force='gtc',
                    order_class='bracket',
                    stop_loss={"stop_price": round(current_prices[etf] * (1 - stop_loss_pct / 100), 2)},
                    take_profit={"limit_price": round(current_prices[etf] * (1 + take_profit_pct / 100), 2)}
                )
                st.write(f"✅ Buy order with bracket placed: {shares} shares of {etf}")

        # Stream live quotes
        st.subheader("📡 Real-Time Streaming Quotes")
        live_quotes = {}

        def on_quote(q):
            live_quotes[q.symbol] = q.bid_price

        async def run_stream():
            stream = Stream(api_key, api_secret, base_url=endpoint_url, data_feed='iex')
            for symbol in top_etfs:
                stream.subscribe_quotes(on_quote, symbol)
            await stream.run()

        def start_streaming():
            asyncio.run(run_stream())

        thread = threading.Thread(target=start_streaming)
        thread.start()

    except Exception as e:
        st.error(f"Trading error: {e}")

# Last update time
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
