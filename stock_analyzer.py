import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

class StockDataFetcher:
    """מחלקה לאיסוף נתוני מניות מ-finance-query.com API"""
    
    def __init__(self, config_path='config.json'):
        self.base_url = 'https://finance-query.com/v2'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FinanceQueryPython/1.0',
            'Accept': 'application/json'
        })
        print("✅ StockDataFetcher initialized with finance-query.com")

    def _get(self, endpoint, params=None):
        """פונקציית עזר לביצוע בקשות GET"""
        url = f"{self.base_url}/{endpoint}"
        try:
            r = self.session.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            else:
                print(f"❌ API Error ({r.status_code}) for {endpoint}: {r.text}")
        except Exception as e:
            print(f"❌ Connection Error for {endpoint}: {e}")
        return None

    def get_stock_data(self, symbol, range='2y', interval='1d'):
        """קבלת נתוני מחירים היסטוריים (Candles)"""
        print(f"Fetching chart for {symbol}...")
        res = self._get(f"chart/{symbol}", params={'range': range, 'interval': interval})
        
        if res and 'candles' in res:
            df = pd.DataFrame(res['candles'])
            if not df.empty:
                # המרה של timestamp (שניות) לתאריך
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df.set_index('timestamp', inplace=True)
                # הבטחת שמות עמודות תואמים למנתח הטכני
                df = df[['open', 'high', 'low', 'close', 'volume']]
                print(f"✅ Chart fetched from finance-query for {symbol}")
                return df
                
        print(f"❌ Failed to fetch chart for {symbol}")
        return None

    def get_company_overview(self, symbol):
        """קבלת מידע פונדמנטלי (Quote Data)"""
        print(f"Fetching info for {symbol}...")
        res = self._get(f"quote/{symbol}") # /quote/ usually has summary info in finance-query
        if res:
            # המרה למבנה ש-StockAnalyzer מצפה לו (מתואם לשדות של finance-query/Yahoo)
            return {
                'Name': res.get('longName', res.get('shortName', symbol)),
                'Symbol': symbol,
                'Description': res.get('longBusinessSummary', 'N/A'),
                'Sector': res.get('sector', 'N/A'),
                'Industry': res.get('industry', 'N/A'),
                'MarketCapitalization': res.get('marketCap', 'N/A'),
                'PERatio': res.get('trailingPE', 'N/A'),
                'Beta': res.get('beta', 'N/A'),
                'DividendYield': res.get('dividendYield', 'N/A'),
                'ProfitMargin': res.get('profitMargins', 'N/A'),
                'FiftyTwoWeekHigh': res.get('fiftyTwoWeekHigh', 'N/A'),
                'FiftyTwoWeekLow': res.get('fiftyTwoWeekLow', 'N/A')
            }
        return {'Name': symbol, 'Symbol': symbol}

    def get_stock_news(self, symbol):
        """קבלת חדשות אחרונות"""
        print(f"Fetching news for {symbol}...")
        res = self._get(f"news/{symbol}")
        formatted_news = []
        
        if res and isinstance(res, list):
            for item in res[:5]: # 5 כתבות ראשונות
                story = item.get('content', item)
                title = story.get('title', 'No Title')
                
                # תאריך (יכול להיות ISO או Timestamp)
                published_at = story.get('pubDate', story.get('providerPublishTime', ''))
                if isinstance(published_at, int):
                    published_at = datetime.fromtimestamp(published_at).strftime('%Y-%m-%d %H:%M')
                
                formatted_news.append({
                    'title': title,
                    'publisher': story.get('provider', {}).get('displayName', 'Market News'),
                    'link': story.get('clickThroughUrl', {}).get('url', story.get('link', '#')),
                    'published': published_at,
                    'type': 'STORY'
                })
        return formatted_news

    def get_batch_quotes(self, symbols):
        """קבלת מחירים בזמן אמת עבור קבוצת מניות (מעולה לסריקת שוק)"""
        if isinstance(symbols, list):
            symbols_str = ",".join(symbols)
        else:
            symbols_str = symbols
            
        res = self._get(f"quote/{symbols_str}")
        if res:
            # אם זה סמל יחיד, המערכת מחזירה אובייקט, אם כמה - רשימה
            if isinstance(res, dict):
                return [res]
            return res
        return []

    def get_market_summary(self):
        """סיכום מצב השוק העולמי"""
        return self._get("market")

    
class TechnicalAnalyzer:
    """ניתוח טכני בסיסי"""
    
    def calculate_indicators(self, df):
        """חישוב אינדיקטורים טכניים"""
        if df is None or len(df) < 20:
            return df
            
        try:
            # ממוצעים נעים
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD (פשוט)
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_diff'] = df['macd'] - df['macd_signal']
            
            # רמות תמיכה והתנגדות בסיסיות (פיבוט)
            df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
            df['r1'] = 2 * df['pivot'] - df['low']
            df['s1'] = 2 * df['pivot'] - df['high']
            
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            
        return df

    def get_trend_signal(self, df):
        if df is None or len(df) < 50: return "Unknown"
        last = df.iloc[-1]
        
        # Check for NaN and handle
        try:
            if pd.isna(last['sma_20']) or pd.isna(last['sma_50']):
                return "Neutral"
                
            if last['close'] > last['sma_20'] > last['sma_50']: return "Strong Uptrend"
            if last['close'] > last['sma_20']: return "Uptrend"
            if last['close'] < last['sma_20'] < last['sma_50']: return "Strong Downtrend"
            if last['close'] < last['sma_20']: return "Downtrend"
        except: pass
        return "Neutral"

    def get_momentum_signal(self, df):
        if df is None or 'rsi' not in df.columns: return "Unknown"
        rsi = df['rsi'].iloc[-1]
        if pd.isna(rsi): return "Neutral"
        if rsi > 70: return "Overbought"
        if rsi < 30: return "Oversold"
        return "Neutral"

class FundamentalAnalyzer:
    """ניתוח פונדמנטלי מהיר"""
    def analyze_fundamentals(self, overview):
        score = 0
        pe = overview.get('PERatio')
        try:
            pe_val = float(pe) if pe and pe != 'N/A' else None
            if pe_val:
                if pe_val < 15: score += 2
                elif pe_val < 25: score += 1
                elif pe_val > 50: score -= 1
        except: pass
        
        return {
            "score": score,
            "pe_rating": "Good" if score > 0 else "Fair",
            "market_cap": overview.get('MarketCapitalization', 'N/A')
        }

class RecommendationEngine:
    """מנוע המלצות חכם"""
    def generate_recommendation(self, symbol, df, overview, technical, risk, fundamental):
        # Trend score based on signal
        trend_map = {"Strong Uptrend": 2, "Uptrend": 1, "Downtrend": -1, "Strong Downtrend": -2, "Neutral": 0, "Unknown": 0}
        trend_score = trend_map.get(technical.get('trend'), 0)
        
        total_score = trend_score + fundamental.get('score', 0)
        
        rec = "Hold"
        if total_score >= 3: rec = "Strong Buy"
        elif total_score >= 1: rec = "Buy"
        elif total_score <= -2: rec = "Strong Sell"
        elif total_score <= -1: rec = "Sell"
        
        return {
            "symbol": symbol,
            "short_term": rec,
            "long_term": "Buy & Hold" if fundamental.get('score', 0) > 0 else "Hold",
            "short_term_confidence": "High" if abs(total_score) >= 2 else "Medium",
            "signal_strength": total_score
        }

    def _generate_detailed_analysis(self, symbol, df, technical, risk, fundamental):
        trend_he = {
            "Strong Uptrend": "מגמת עלייה חזקה",
            "Uptrend": "מגמת עלייה",
            "Downtrend": "מגמת ירידה",
            "Strong Downtrend": "מגמת ירידה חזקה",
            "Neutral": "דשדוש",
            "Unknown": "לא ידוע"
        }.get(technical.get('trend'), "נייטרלית")
        
        return f"ניתוח עבור {symbol}: המגמה הנוכחית היא {trend_he}. הציון הכולל מעיד על רמת סיכון {risk.get('level')}."

class RiskAssessor:
    """הערכת סיכונים"""
    def assess_risk(self, df, overview):
        if df is None: return {"level": "Unknown", "factors": []}
        try:
            volatility = df['close'].pct_change().std() * (252**0.5)
            level = "Moderate"
            if volatility > 0.4: level = "High"
            elif volatility < 0.2: level = "Low"
            
            return {
                "level": level,
                "volatility": f"{volatility*100:.1f}%",
                "factors": ["High Volatility"] if level == "High" else []
            }
        except:
            return {"level": "Moderate", "volatility": "N/A", "factors": []}

    def analyze_investment_strategy(self, df, risk):
        return {"strategy": "DCA", "recommendation_he": "מומלץ להשקיע במנות קטנות (DCA) כדי למצע מחיר בשל תנודתיות השוק."}

class StockAnalysisSystem:
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer()
        self.recommender = RecommendationEngine()
        self.risk = RiskAssessor()

    def _calculate_performance(self, df):
        if df is None or len(df) < 2: return {}
        try:
            last = df['close'].iloc[-1]
            return {
                "1m": f"{((last / df['close'].iloc[-22] - 1) * 100):.1f}%" if len(df) > 22 else "N/A",
                "1y": f"{((last / df['close'].iloc[0] - 1) * 100):.1f}%" if len(df) > 250 else "N/A"
            }
        except: return {}

    def _prepare_chart_data(self, df):
        if df is None: return []
        try:
            return [{"time": i.strftime('%Y-%m-%d'), "value": float(v)} for i, v in df['close'].tail(30).items()]
        except: return []

    def _clean_data(self, data):
        """ניקוי נתוני NaN להבטחת תאימות JSON"""
        if isinstance(data, dict):
            return {k: self._clean_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_data(i) for i in data]
        elif isinstance(data, (float, np.float64, np.float32)):
            if np.isnan(data) or np.isinf(data):
                return 0.0
            return float(data)
        return data

    def analyze_stock(self, symbol):
        """ניתוח מקיף של מניה - הכל דרך finance-query API"""
        print(f"🚀 Starting analysis for {symbol}...")
        
        try:
            # 1. איסוף נתונים
            df = self.fetcher.get_stock_data(symbol)
            if df is None or df.empty:
                return {"error": f"Could not fetch data for {symbol}. Symbol might be invalid."}
                
            overview = self.fetcher.get_company_overview(symbol)

            # 2. חישוב אינדיקטורים
            df = self.technical.calculate_indicators(df)
            
            # 3. ניתוח רכיבים
            technical_signals = {
                "trend": self.technical.get_trend_signal(df),
                "momentum": self.technical.get_momentum_signal(df)
            }
            fundamental_analysis = self.fundamental.analyze_fundamentals(overview)
            risk_assessment = self.risk.assess_risk(df, overview)
            performance = self._calculate_performance(df)
            news = self.fetcher.get_stock_news(symbol)
            investment_strategy = self.risk.analyze_investment_strategy(df, risk_assessment)

            # 4. המלצה סופית
            recommendation = self.recommender.generate_recommendation(
                symbol, df, overview, technical_signals, risk_assessment, fundamental_analysis
            )
            
            # 5. ניתוח מפורט
            detailed_explanation = self.recommender._generate_detailed_analysis(
                symbol, df, technical_signals, risk_assessment, fundamental_analysis
            )

            # 6. בניית התוצאה הסופית
            current_price = float(df['close'].iloc[-1])
            prev_close = float(df['close'].iloc[-2]) if len(df) > 1 else current_price
            change_percent = ((current_price / prev_close) - 1) * 100
            
            result = {
                "recommendation": {
                    "symbol": symbol,
                    "company_name": overview.get('Name', symbol),
                    "current_price": current_price,
                    "short_term": recommendation.get('short_term', 'Hold'),
                    "long_term": recommendation.get('long_term', 'Hold'),
                    "short_term_confidence": recommendation.get('short_term_confidence', 'Medium'),
                    "explanation": detailed_explanation,
                    "detailed_analysis_he": detailed_explanation,
                    "risk_level": risk_assessment.get('level', 'Unknown')
                },
                "risk": risk_assessment,
                "technical": technical_signals,
                "fundamental": fundamental_analysis,
                "overview": overview,
                "price_data": {
                    "current_price": current_price,
                    "change_percent": change_percent,
                    "high_52w": float(df['high'].max()),
                    "low_52w": float(df['low'].min()),
                    "volume": int(df['volume'].iloc[-1])
                },
                "performance": performance,
                "news": news,
                "investment_strategy": investment_strategy,
                "chart_data": self._prepare_chart_data(df)
            }
            
            print(f"✅ Analysis complete for {symbol}")
            return self._clean_data(result)
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR in analyze_stock for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

if __name__ == "__main__":
    system = StockAnalysisSystem()
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    result = system.analyze_stock(symbol)
    print(json.dumps(result, indent=2, ensure_ascii=False))

