import yfinance as yf
import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

symbol = "NVDA"
print(f"Testing yfinance with session for {symbol}...")
try:
    ticker = yf.Ticker(symbol, session=session)
    df = ticker.history(period='2y', auto_adjust=True)
    print(f"Dataframe empty: {df.empty}, Rows: {len(df)}")
    if not df.empty:
        print(f"Last close: {df['Close'].iloc[-1]}")
except Exception as e:
    print(f"Error: {e}")
