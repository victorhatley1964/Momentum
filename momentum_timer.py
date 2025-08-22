import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import math
import numpy as np

# Set the title and a short description for the app
st.title("Momentum Timer")
st.markdown("This application calculates momentum for a list of stocks to help with trading decisions.")

# --- Explanation Section ---
st.subheader("How the Momentum Score is Calculated")
st.markdown(
    """
    The momentum score is a measure of a stock's recent performance. It is calculated as the
    **percentage change** in the stock's closing price over the number of months you select.
    
    * **Positive Momentum:** A positive score indicates the stock's price has been
        increasing, showing upward momentum.
    * **Negative Momentum:** A negative score indicates the stock's price has been
        decreasing, showing downward momentum.

    Stocks with higher positive momentum scores are often considered to be in a strong upward trend.
    """
)

def get_momentum_data(tickers, period, progress_bar):
    """
    Fetches historical stock data for a list of tickers, handling potential errors.

    Args:
        tickers (list): A list of stock ticker symbols.
        period (str): The time period for historical data (e.g., '1y', '6mo').
        progress_bar: A Streamlit progress bar object for visual feedback.

    Returns:
        pandas.DataFrame: A DataFrame containing the 'Close' prices for all tickers,
                          or an empty DataFrame if data fetching fails.
    """
    try:
        # Download data for the list of tickers.
        # The new default auto_adjust=True means we will use the 'Close' price,
        # which is already adjusted for dividends and splits.
        data = yf.download(tickers, period=period, progress=False)

        # Check if the returned DataFrame has a MultiIndex (for multiple tickers)
        if isinstance(data.columns, pd.MultiIndex):
            # If so, select the 'Close' column for all tickers
            data = data['Close']
        else:
            # If not, it's a single ticker, so we access 'Close' directly
            # This is a fallback for when the multi-ticker download fails
            data = data['Close']
            data = pd.DataFrame(data)
            
        # Drop any rows with NaN values that might have been caused by missing data
        data.dropna(inplace=True)

    except (KeyError, IndexError) as e:
        # Handle cases where the 'Close' column is missing or data is not found.
        # This will happen if yfinance couldn't find data for a ticker.
        st.error(f"Error fetching data for one or more tickers. The data might not be available. Details: {e}")
        return pd.DataFrame()

    return data


# --- Streamlit UI Components ---
st.header("Configuration")

# User input for the number of months for the momentum calculation
months_momentum = st.slider("Number of months for momentum calculation:", min_value=1, max_value=12, value=6, step=1)

# User input for the list of tickers
ticker_string = st.text_area("Enter stock tickers (e.g., AAPL, GOOG, MSFT, TSLA):", "AAPL, GOOG, MSFT, TSLA")

# Check if the ticker input is empty
if ticker_string:
    # Convert the input string into a list of tickers
    tickers_list = [t.strip().upper() for t in ticker_string.split(',')]
else:
    st.warning("Please enter at least one stock ticker symbol.")
    tickers_list = []

# Button to trigger the analysis
if st.button("Run Momentum Analysis"):
    if not tickers_list:
        st.warning("Please enter valid ticker symbols before running the analysis.")
    else:
        # Calculate the period string for yfinance
        # Use a slightly longer period to ensure enough data
        period_str = f"{months_momentum * 4}mo"

        # Use a progress bar for visual feedback
        progress_bar = st.progress(0)
        progress_bar.progress(20)

        # Get the historical data
        with st.spinner("Fetching data..."):
            historical_data = get_momentum_data(tickers_list, period_str, progress_bar)
        
        progress_bar.progress(50)

        if not historical_data.empty:
            # --- Momentum Analysis Section ---
            days_in_period = months_momentum * 21  # Approx 21 trading days per month
            
            if len(historical_data) >= days_in_period:
                momentum_data = historical_data.pct_change(days_in_period).iloc[-1].sort_values(ascending=False)
                
                st.subheader(f"Momentum Scores (Last {months_momentum} Months)")
                momentum_df = momentum_data.to_frame(name="Momentum Score")
                st.dataframe(momentum_df.style.format({"Momentum Score": "{:.2%}"}), use_container_width=True)

                # --- Risk Analysis (Volatility) Section ---
                st.subheader("Risk Analysis (Volatility)")
                daily_returns = historical_data.pct_change()
                # Annualize the daily volatility by multiplying by the square root of 252 trading days
                volatility = daily_returns.std() * np.sqrt(252)
                volatility = volatility.sort_values(ascending=False)

                volatility_df = volatility.to_frame(name="Annualized Volatility")
                st.dataframe(volatility_df.style.format({"Annualized Volatility": "{:.2%}"}), use_container_width=True)
                
                # --- Trading Signal and Recommendation ---
                st.subheader("Trading Signal")
                
                num_tickers_to_chart = min(10, len(momentum_data))
                top_performers = momentum_data.head(num_tickers_to_chart)
                
                st.subheader(f"Top {num_tickers_to_chart} Performers Chart")
                st.line_chart(historical_data[top_performers.index])

                st.success(
                    f"Based on the last {months_momentum} months, the top performing stocks are: "
                    + ", ".join([f"**{ticker}**" for ticker in top_performers.index])
                    + ". These stocks show strong momentum."
                )

                progress_bar.progress(100)
                st.balloons()
            else:
                st.warning(f"Not enough historical data to calculate momentum for {months_momentum} months. Please try a shorter period or different tickers.")
                progress_bar.empty()
        else:
            progress_bar.empty()

