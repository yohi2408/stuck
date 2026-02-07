import requests
import json
import finnhub

with open('config.json', 'r') as f:
    config = json.load(f)

av_key = config['api_key']
fh_key = config['finnhub_key']

print(f"Testing Alpha Vantage with key: {av_key}...")
av_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=NVDA&apikey={av_key}"
try:
    res = requests.get(av_url)
    print(f"AV Response: {res.json()}")
except Exception as e:
    print(f"AV Error: {e}")

print(f"\nTesting Finnhub with key: {fh_key}...")
try:
    fh_client = finnhub.Client(api_key=fh_key)
    quote = fh_client.quote('NVDA')
    print(f"Finnhub Quote: {quote}")
except Exception as e:
    print(f"Finnhub Error: {e}")
