import yfinance as yf
import pandas as pd

symbol = "NVDA"
print(f"Testing yfinance for {symbol}...")
try:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period='2y', auto_adjust=True)
    print(f"Dataframe empty: {df.empty}")
    if not df.empty:
        print(f"Columns: {list(df.columns)}")
        print(f"Tail:\n{df.tail()}")
    else:
        print("Data is EMPTY")
except Exception as e:
    print(f"Error: {e}")
