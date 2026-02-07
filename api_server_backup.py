import logging
import json
import os
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from stock_analyzer import StockAnalysisSystem
import yfinance as yf

app = Flask(__name__)
CORS(app)  # אפשר גישה מ-frontend

# יצירת מופע של מערכת הניתוח
analyzer = StockAnalysisSystem()

def get_market_stocks(limit=50):
    """קבלת רשימת מניות מהשוק האמריקאי"""
    try:
        # קבלת מניות מ-S&P 500
        sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        import pandas as pd
        tables = pd.read_html(sp500_url)
        sp500_table = tables[0]
        symbols = sp500_table['Symbol'].tolist()[:limit]
        
        print(f"📊 Scanning {len(symbols)} stocks from S&P 500...")
        return symbols
    except Exception as e:
        print(f"Failed to fetch S&P 500 list: {e}")
        # Fallback: רשימה מורחבת של מניות פופולריות
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B',
            'JPM', 'V', 'WMT', 'JNJ', 'PG', 'MA', 'HD', 'DIS', 'NFLX', 'ADBE',
            'CRM', 'PYPL', 'INTC', 'AMD', 'CSCO', 'PEP', 'KO', 'NKE', 'MCD',
            'COST', 'ABBV', 'TMO', 'ACN', 'LLY', 'AVGO', 'TXN', 'ORCL', 'DHR',
            'UNH', 'BAC', 'CVX', 'XOM', 'PFE', 'MRK', 'ABT', 'WFC', 'CMCSA'
        ][:limit]

@app.route('/')
def home():
    """דף בית"""
    return jsonify({
        "message": "Stock Analysis API",
        "version": "1.0",
        "endpoints": [
            "/api/analyze/<symbol>",
            "/api/compare",
            "/api/health"
        ]
    })

@app.route('/api/health')
def health():
    """בדיקת תקינות"""
    return jsonify({"status": "healthy"})

@app.route('/api/analyze/<symbol>')
def analyze_stock(symbol):
    """ניתוח מניה בודדת"""
    try:
        symbol = symbol.upper()
        result = analyzer.analyze_stock(symbol)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 404
        
        # התוצאה כבר מכילה את המבנה הנכון מ-stock_analyzer.py
        # result["price_data"] הוא מילון עם סטטיסטיקות
        # result["chart_data"] הוא מילון עם נתוני הגרף
        
        return jsonify({
            "recommendation": result["recommendation"],
            "technical": result["technical"],
            "fundamental": result["fundamental"],
            "risk": result["risk"],
            "overview": result["overview"],
            "price_data": result["price_data"],
            "chart_data": result["chart_data"],
            "performance": result["performance"] # העברת נתוני הביצועים
        })
    except Exception as e:
        print(f"Error in analyze_stock: {e}") # לוג לשגיאה
        return jsonify({"error": str(e)}), 500

@app.route('/api/price/<symbol>')
def get_live_price(symbol):
    """קבלת מחיר מניה בזמן אמת (קל ומהיר)"""
    try:
        symbol = symbol.upper()
        # שימוש ב-yfinance לקבלת נתונים מהירים
        ticker = yf.Ticker(symbol)
        # נסה לקבל נתונים מ-fast_info קודם (מהיר יותר)
        try:
            current_price = ticker.fast_info.last_price
            prev_close = ticker.fast_info.previous_close
        except:
            # Fallback ל-history אם fast_info נכשל
            df = ticker.history(period="2d")
            if len(df) < 1:
                return jsonify({"error": "No data found"}), 404
            current_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price

        change = current_price - prev_close
        change_percent = (change / prev_close) * 100
        
        return jsonify({
            "symbol": symbol,
            "price": current_price,
            "change": change,
            "change_percent": change_percent,
            "timestamp": pd.Timestamp.now().isoformat()
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
                    "score": result["recommendation"]["total_score"]
                })
        
        # מיון לפי ציון
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return jsonify({
            "comparison": results,
            "best_pick": results[0] if results else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recommendations')
def get_recommendations():
    """סריקת שוק והמלצות - טווח קצר וארוך בנפרד"""
    try:
        # קבלת מניות מהשוק
        market_stocks = get_market_stocks(limit=50)
        
        recommendations = []
        print(f"🔍 Scanning {len(market_stocks)} stocks from the market...")
        
        analyzed_count = 0
        for symbol in market_stocks:
            try:
                result = analyzer.analyze_stock(symbol)
                if "error" not in result:
                    rec = result["recommendation"]
                    recommendations.append({
                        "symbol": symbol,
                        "name": rec["company_name"],
                        "price": rec["current_price"],
                        "short_term": rec["short_term"],
                        "short_term_confidence": rec["short_term_confidence"],
                        "long_term": rec["long_term"],
                        "risk": result["risk"]["level"],
                        "score": rec["total_score"],
                        "trend": result["technical"]["trend"],
                        "sector": result["overview"].get("Sector", "N/A"),
                        "rsi": result["technical"].get("rsi", "N/A"),
                        "volatility": result["risk"]["volatility"]
                    })
                    analyzed_count += 1
                    if analyzed_count % 10 == 0:
                        print(f"✅ Analyzed {analyzed_count}/{len(market_stocks)} stocks...")
            except Exception as e:
                print(f"⚠️ Failed to analyze {symbol}: {e}")
                continue
        
        print(f"✅ Successfully analyzed {len(recommendations)} stocks")
        
        # מיון לפי ציון
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        # חלוקה לקטגוריות - טווח קצר וארוך בנפרד
        
        # טווח קצר - המלצות חמות (Strong Buy / Buy)
        short_term_hot = [
            r for r in recommendations 
            if r["short_term"] in ["Strong Buy", "Buy"]
        ][:10]
        
        # טווח קצר - בסיכון נמוך
        short_term_safe = [
            r for r in recommendations 
            if r["short_term"] in ["Strong Buy", "Buy"] and "Low" in r["risk"]
        ][:10]
        
        # טווח ארוך - המלצות מובילות
        long_term_best = [
            r for r in recommendations 
            if r["long_term"] in ["Strong Buy & Hold", "Buy & Hold"]
        ][:10]
        
        # טווח ארוך - בסיכון נמוך (להשקעה יציבה)
        long_term_stable = [
            r for r in recommendations 
            if r["long_term"] in ["Strong Buy & Hold", "Buy & Hold"] and "Low" in r["risk"]
        ][:10]
        
        # מניות בעלות פוטנציאל גבוה (מומנטום חזק)
        high_momentum = [
            r for r in recommendations 
            if r["trend"] in ["Strong Uptrend", "Uptrend"] and r["score"] > 2
        ][:10]
        
        return jsonify({
            "short_term": {
                "hot_picks": short_term_hot,
                "safe_picks": short_term_safe
            },
            "long_term": {
                "best_picks": long_term_best,
                "stable_picks": long_term_stable
            },
            "high_momentum": high_momentum,
            "total_analyzed": len(recommendations),
            "market_scanned": len(market_stocks)
        })
    except Exception as e:
        print(f"❌ Error in recommendations: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting Stock Analysis API Server...")
    print("📊 Server running on http://localhost:5000")
    print("🔍 Try: http://localhost:5000/api/analyze/AAPL")
    app.run(debug=True, port=5000)
