
import yfinance as yf
import json
import datetime

def default_converter(o):
    if isinstance(o, datetime.datetime):
        return o.isoformat()
    return str(o)

symbol = "NVDA"
print(f"Fetching news for {symbol}...")
try:
    ticker = yf.Ticker(symbol)
    news = ticker.news
    print("Raw news data type:", type(news))
    print(json.dumps(news, indent=2, default=default_converter))
except Exception as e:
    print(f"Error: {e}")
