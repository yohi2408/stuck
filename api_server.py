import logging
import json
import os
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from stock_analyzer import StockAnalysisSystem

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # אפשר גישה מ-frontend

# יצירת מופע של מערכת הניתוח
analyzer = StockAnalysisSystem()

def get_market_stocks(limit=50):
    """קבלת רשימת מניות מהשוק האמריקאי"""
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "JPM", "V"][:limit]

@app.route('/')
def home():
    """הגשת דף הבית (Frontend)"""
    return send_from_directory('.', 'index.html')

@app.route('/api/health')
def health():
    """בדיקת תקינות המערכת"""
    return jsonify({
        "status": "healthy",
        "message": "Stock Analysis API is running",
        "version": "1.0"
    })

@app.route('/api/analyze/<symbol>')
def analyze_stock(symbol):
    """ניתוח מניה בודדת"""
    try:
        symbol = symbol.upper()
        result = analyzer.analyze_stock(symbol)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 404
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in analyze_stock: {e}") 
        return jsonify({"error": str(e)}), 500

@app.route('/api/price/<symbol>')
def get_live_price(symbol):
    """קבלת מחיר מניה בזמן אמת (קל ומהיר דרך finance-query)"""
    try:
        symbol = symbol.upper()
        quotes = analyzer.fetcher.get_batch_quotes([symbol])
        if not quotes or len(quotes) == 0:
            return jsonify({"error": "No data found"}), 404
            
        quote = quotes[0]
        current_price = quote.get('regularMarketPrice', quote.get('price', 0))
        prev_close = quote.get('regularMarketPreviousClose', current_price)
        
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100 if prev_close else 0
        
        return jsonify({
            "symbol": symbol,
            "price": current_price,
            "change": change,
            "change_percent": change_percent,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error fetching live price for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/compare', methods=['POST'])
def compare_stocks():
    """השוואה בין מספר מניות"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols or len(symbols) < 2:
            return jsonify({"error": "Please provide at least 2 symbols"}), 400
        
        results = []
        for symbol in symbols:
            symbol = symbol.upper()
            result = analyzer.analyze_stock(symbol)
            if "error" not in result:
                results.append({
                    "symbol": symbol,
                    "recommendation": result["recommendation"],
                    "risk": result["risk"]["level"],
                    "score": result["recommendation"].get("signal_strength", 0)
                })
        
        if results:
            results.sort(key=lambda x: x["score"], reverse=True)
        
        return jsonify({
            "comparison": results,
            "best_pick": results[0] if results else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recommendations')
def get_recommendations():
    """סריקת שוק והמלצות - גרסה אופטימלית ומהירה"""
    try:
        # שימוש בשיטה החדשה והמהירה שפועלת ב-Batch ועם Cache
        recommendations = analyzer.scan_market_cached(limit=40)
        
        # חלוקה לקטגוריות
        short_term_hot = [r for r in recommendations if r["score"] >= 2][:10]
        long_term_best = recommendations[:10] # Top scorers
        high_momentum = [r for r in recommendations if "Uptrend" in r["trend"]][:10]
        
        return jsonify({
            "short_term": {
                "hot_picks": short_term_hot,
                "safe_picks": [r for r in short_term_hot if r["rsi"] != "N/A" and r["rsi"] < 50][:5]
            },
            "long_term": {
                "best_picks": long_term_best,
                "stable_picks": [r for r in long_term_best if r["rsi"] != "N/A" and r["rsi"] < 45][:5]
            },
            "high_momentum": high_momentum,
            "total_analyzed": len(recommendations),
            "market_scanned": 40
        })
    except Exception as e:
        print(f"❌ Error in recommendations: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting Stock Analysis API Server...")
    print("📊 Server running on http://localhost:5000")
    print("🔍 Try: http://localhost:5000/api/analyze/AAPL")
    app.run(debug=True, port=5000)
