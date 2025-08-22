import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import math
import numpy as np

# Set the title and a short description for the app
st.title("Momentum Timer")
st.markdown("This application calculates momentum for a list of stocks to help with trading decisions.")

def get_momentum_data(tickers, period, progress_bar):
    """
    Fetches historical stock data for a list of tickers, handling potential errors.

    Args:
        tickers (list): A list of stock ticker symbols.
        period (str): The time period for historical data (e.g., '1y', '6mo').
        progress_bar: A Streamlit progress bar object for visual feedback.

    Returns:
        pandas.DataFrame: A DataFrame containing the 'Adj Close' prices for all tickers,
                          or an empty DataFrame if data fetching fails.
    """
    try:
        # Download data for the list of tickers
        data = yf.download(tickers, period=period, progress=False)

        # Check if the returned DataFrame has a MultiIndex (for multiple tickers)
        if isinstance(data.columns, pd.MultiIndex):
            # If so, select the 'Adj Close' column for all tickers
            data = data['Adj Close']
        else:
            # If not, it's a single ticker, so we access 'Adj Close' directly
            # This is a fallback for when the multi-ticker download fails to find data
            data = data['Adj Close']
            data = pd.DataFrame(data)
            
        # Drop any rows with NaN values that might have been caused by missing data
        data.dropna(inplace=True)

    except (KeyError, IndexError) as e:
        # Handle cases where the 'Adj Close' column is missing or data is not found
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
        period_str = f"{months_momentum * 4}mo"  # Use a longer period to ensure enough data

        # Use a progress bar for visual feedback
        progress_bar = st.progress(0)
        progress_bar.progress(20)

        # Get the historical data
        with st.spinner("Fetching data..."):
            historical_data = get_momentum_data(tickers_list, period_str, progress_bar)
        
        progress_bar.progress(50)

        if not historical_data.empty:
            # Calculate the number of days in the specified period
            days_in_period = months_momentum * 21  # Approx 21 trading days per month
            
            # Check if there's enough data for the calculation
            if len(historical_data) >= days_in_period:
                # Calculate the momentum
                momentum_data = historical_data.pct_change(days_in_period).iloc[-1].sort_values(ascending=False)
                
                progress_bar.progress(80)

                st.subheader(f"Momentum Scores (Last {months_momentum} Months)")
                # Convert the momentum series to a DataFrame for display
                momentum_df = momentum_data.to_frame(name="Momentum Score")
                st.dataframe(momentum_df.style.format({"Momentum Score": "{:.2%}"}), use_container_width=True)
                
                # --- Trading Signal and Recommendation ---
                st.subheader("Trading Signal")
                
                # Top 3 based on momentum
                top_performers = momentum_data.head(3)
                
                # Plot the top performers using a line chart
                st.subheader("Top Performers Chart")
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
            # The error message is already handled in the get_momentum_data function
            progress_bar.empty()
