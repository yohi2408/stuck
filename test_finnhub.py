import finnhub
import json

def test_key(key):
    try:
        client = finnhub.Client(api_key=key)
        res = client.quote('AAPL')
        if 'c' in res and res['c'] > 0:
            print(f"✅ Key {key} is VALID! Price: {res['c']}")
            return True
        else:
            print(f"❌ Key {key} returned invalid response: {res}")
    except Exception as e:
        print(f"❌ Key {key} error: {e}")
    return False

# Test the parts of the key we found in config.json
keys_to_test = [
    "d63mif9r01ql6dj0l350",
    "d63mif9r01ql6dj0l35g",
    "d63mif9r01ql6dj0l350d63mif9r01ql6dj0l35g"
]

for k in keys_to_test:
    test_key(k)
