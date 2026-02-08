import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import yfinance as yf
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import finnhub
import xml.etree.ElementTree as ET

class StockDataFetcher:
    """מחלקה לאיסוף נתוני מניות מ-Finnhub, Alpha Vantage ו-Yahoo Finance"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.api_key = self.config['api_key']
        self.base_url = 'https://www.alphavantage.co/query'
        
        # Finnhub client - Fix duplicate key issue
        self.finnhub_key = self.config.get('finnhub_key', '').strip()
        if len(self.finnhub_key) > 35 and self.finnhub_key[:len(self.finnhub_key)//2] == self.finnhub_key[len(self.finnhub_key)//2:]:
            # It's a duplicate paste (common issue)
            self.finnhub_key = self.finnhub_key[:len(self.finnhub_key)//2]
            
        if self.finnhub_key and "PUT_YOUR" not in self.finnhub_key:
            self.finnhub_client = finnhub.Client(api_key=self.finnhub_key)
        else:
            self.finnhub_client = None
            
        # Requests Session with browser headers to avoid blocks
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def get_stock_data(self, symbol, outputsize='full'):
        """קבלת נתוני מחירים יומיים - גרסת PROD ללא דמו"""
        
        # 1. Try Finnhub
        if self.finnhub_client:
            try:
                df = self._get_finnhub_data(symbol)
                if df is not None and not df.empty:
                    print(f"✅ Data from Finnhub for {symbol}")
                    return df
            except Exception as e:
                print(f"Finnhub failed: {e}")
        
        # 2. Try Alpha Vantage
        try:
            params = {'function': 'TIME_SERIES_DAILY', 'symbol': symbol, 'apikey': self.api_key}
            r = requests.get(self.base_url, params=params, timeout=5)
            data = r.json()
            if "Note" in data and "rate limit" in str(data).lower():
                print(f"⚠️ Alpha Vantage Rate Limit for {symbol}")
            elif 'Time Series (Daily)' in data:
                df = pd.DataFrame.from_dict(data['Time Series (Daily)'], orient='index')
                df.columns = ['open', 'high', 'low', 'close', 'volume']
                df.index = pd.to_datetime(df.index)
                df = df.sort_index().astype(float)
                print(f"✅ Data from Alpha Vantage for {symbol}")
                return df
            elif 'Error Message' in data:
                print(f"❌ Alpha Vantage Error: {data['Error Message']}")
        except Exception as e:
            print(f"Alpha Vantage failed: {e}")

        # 3. Try Yahoo Finance (Enhanced for Production)
        df = self._get_yfinance_data(symbol)
        if df is not None and not df.empty:
            return df
            
        # 4. Final Fail
        print(f"⛔ CRITICAL: No real data could be fetched for {symbol} after all attempts.")
        return None
    
    def _get_finnhub_data(self, symbol):
        """קבלת נתונים מ-Finnhub"""
        try:
            # Get data for the last 2 years
            end_date = int(datetime.now().timestamp())
            start_date = int((datetime.now() - timedelta(days=730)).timestamp())
            
            # Fetch candle data
            res = self.finnhub_client.stock_candles(symbol, 'D', start_date, end_date)
            
            if res['s'] == 'ok':
                df = pd.DataFrame({
                    'open': res['o'],
                    'high': res['h'],
                    'low': res['l'],
                    'close': res['c'],
                    'volume': res['v']
                })
                df.index = pd.to_datetime(res['t'], unit='s')
                return df
            else:
                print(f"Finnhub returned status: {res['s']}")
                return None
        except Exception as e:
            print(f"Finnhub error: {e}")
            return None
    
    def _get_yfinance_data(self, symbol):
                    df = df.rename(columns=rename_map)
                    present_cols = [col for col in required_cols if col in df.columns]
                    if len(present_cols) >= 4: # Minimum usable data
                        return df[present_cols]
            
            print(f"Yahoo Finance returned empty data for {symbol}")
            return None # Real data only
        except Exception as e:
            err_msg = str(e)
            if "Too Many Requests" in err_msg or "Rate limited" in err_msg:
                 print(f"❌ Yahoo Finance Rate Limit: {err_msg}")
            else:
                 print(f"Yahoo Finance failed for {symbol}: {e}")
            return None

    def _generate_mock_data(self, symbol):
        """ייצור נתוני דמו כספק אחרון בהחלט כשהכל חסום"""
        print(f"⚠️ GENERIC FALLBACK: Generating demo data for {symbol} due to API blocks")
        dates = pd.date_range(end=datetime.now(), periods=100)
        base_price = 150.0 # Default
        if symbol == 'NVDA': base_price = 185.0
        elif symbol == 'AAPL': base_price = 220.0
        
        # Random walk
        prices = [base_price]
        for _ in range(99):
            prices.append(prices[-1] * (1 + np.random.uniform(-0.02, 0.02)))
            
        df = pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': [int(1000000 * np.random.uniform(0.5, 2.0)) for _ in prices]
        }, index=dates)
        return df

    def get_batch_yfinance_data(self, symbols, period='2y'):
        """קבלת נתונים לקבוצת מניות בבת אחת - יעיל מאוד למניעת חסימות"""
        try:
            print(f"🔍 Batch fetching {len(symbols)} stocks from Yahoo Finance...")
            # yf.download is much better for large batches
            data = yf.download(symbols, period=period, interval='1d', group_by='ticker', session=self.session)
            return data
        except Exception as e:
            print(f"Batch fetch failed: {e}")
            return None
    
    def get_company_overview(self, symbol):
        """קבלת מידע פונדמנטלי על החברה"""
        
        # Try Finnhub first
        if self.finnhub_client:
            try:
                print(f"Trying Finnhub overview for {symbol}...")
                profile = self.finnhub_client.company_profile2(symbol=symbol)
                
                if profile and 'name' in profile:
                    print(f"✅ Got real overview from Finnhub for {symbol}")
                    return {
                        'Symbol': symbol,
                        'Name': profile.get('name', 'N/A'),
                        'MarketCapitalization': profile.get('marketCapitalization', 0) * 1000000,  # Finnhub returns in millions
                        'PERatio': 'N/A',  # Will get from quote
                        'DividendYield': 'N/A',
                        'Beta': 'N/A',
                        'Sector': profile.get('finnhubIndustry', 'N/A'),
                        'Description': f"{profile.get('name', '')} - {profile.get('exchange', '')} listed company"
                    }
            except Exception as e:
                print(f"Finnhub overview failed: {e}")
        
        # Try Alpha Vantage
        try:
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            if 'Symbol' in data:
                print(f"✅ Got real overview from Alpha Vantage for {symbol}")
                return data
            
            # Fallback to yfinance
            print(f"Alpha Vantage overview failed for {symbol}, using Yahoo Finance...")
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'Symbol': symbol,
                'Name': info.get('longName', 'N/A'),
                'MarketCapitalization': info.get('marketCap', 'N/A'),
                'PERatio': info.get('trailingPE', 'N/A'),
                'DividendYield': info.get('dividendYield', 'N/A'),
                'Beta': info.get('beta', 'N/A'),
                'Sector': info.get('sector', 'N/A'),
                'Description': info.get('longBusinessSummary', 'N/A')
            }
        except Exception as e:
            print(f"Yahoo Finance overview failed: {e}")
            return {} # Real data only
            
    def get_stock_news(self, symbol):
        """קבלת חדשות אחרונות על המניה"""
        # Try Google News RSS first as it allows specific query "SYMBOL stock"
        # which yields more relevant results than generic Yahoo ticker news
        google_news = self._fetch_google_news_rss(symbol)
        if google_news:
            return google_news

        try:
            print(f"Google RSS empty, falling back to Yahoo Finance for {symbol}...")
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            # Debug print
            print(f"DEBUG: Yahoo News raw data for {symbol}: {len(news) if news else 'None'}")
            
            formatted_news = []
            if news and len(news) > 0:
                for item in news[:5]: # Take top 5
                    try:
                        # Handle struct: item can be the story itself or nested under 'content'
                        story = item.get('content', item)
                        
                        # Title
                        title = story.get('title', 'No Title')
                        
                        # Date
                        # Try 'pubDate' (ISO format) or 'providerPublishTime' (timestamp)
                        pub_date_str = story.get('pubDate')
                        if pub_date_str:
                            try:
                                dt = datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%M:%SZ")
                                published = dt
                            except:
                                published = datetime.now()
                        else:
                            ts = story.get('providerPublishTime', 0)
                            published = datetime.fromtimestamp(ts)

                        # Link
                        # Try clickThroughUrl -> url, or canonicalUrl -> url
                        link = '#'
                        if 'clickThroughUrl' in story and story['clickThroughUrl']:
                            link = story['clickThroughUrl'].get('url', '#')
                        elif 'canonicalUrl' in story and story['canonicalUrl']:
                            link = story['canonicalUrl'].get('url', '#')
                        elif 'link' in story:
                            link = story['link']
                        
                        # Publisher
                        publisher = 'Yahoo Finance'
                        if 'provider' in story and story['provider']:
                             publisher = story['provider'].get('displayName', 'Yahoo Finance')

                        formatted_news.append({
                            'title': title,
                            'publisher': publisher,
                            'link': link,
                            'published': published.strftime('%Y-%m-%d %H:%M'),
                            'type': 'STORY'
                        })
                    except Exception as e:
                        print(f"Error parsing news item: {e}")
                        continue
                
                if formatted_news:
                    return formatted_news
            
            return []
            
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            return []

    def _fetch_google_news_rss(self, symbol):
        """גיבוי: משיכת חדשות מ-Google News RSS"""
        try:
            print(f"Fetching backup news from Google RSS for {symbol}...")
            url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                news_items = []
                for item in root.findall('.//item')[:5]:
                    try:
                        title = item.find('title').text if item.find('title') is not None else 'No Title'
                        link = item.find('link').text if item.find('link') is not None else '#'
                        pubDate = item.find('pubDate').text if item.find('pubDate') is not None else datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
                        
                        # Handle source
                        source_elem = item.find('source')
                        if source_elem is not None:
                            source = source_elem.text or source_elem.get('url') or 'Google News'
                        else:
                            source = 'Google News'
                        
                        # המרת תאריך
                        try:
                            # Try multiple formats
                            try:
                                dt = datetime.strptime(pubDate, '%a, %d %b %Y %H:%M:%S %Z')
                            except:
                                dt = datetime.strptime(pubDate, '%a, %d %b %Y %H:%M:%S GMT')
                            pub_fmt = dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            pub_fmt = pubDate
                            
                        news_items.append({
                            'title': title,
                            'publisher': source,
                            'link': link,
                            'published': pub_fmt,
                            'type': 'STORY'
                        })
                    except Exception as e:
                        print(f"Error parsing RSS item: {e}")
                        continue
                        
                return news_items
        except Exception as e:
            print(f"Google RSS failed: {e}")
        return []


    
class TechnicalAnalyzer:
    """מחלקה לניתוח טכני של מניות"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.params = self.config['analysis_parameters']
    
    def calculate_indicators(self, df):
        """חישוב אינדיקטורים טכניים"""
        if df is None or len(df) < 50:
            return None
        
        indicators = {}
        
        # Moving Averages
        sma_short = SMAIndicator(close=df['close'], window=self.params['sma_short'])
        sma_long = SMAIndicator(close=df['close'], window=self.params['sma_long'])
        indicators['sma_20'] = sma_short.sma_indicator()
        indicators['sma_50'] = sma_long.sma_indicator()
        
        # EMA
        ema_12 = EMAIndicator(close=df['close'], window=12)
        indicators['ema_12'] = ema_12.ema_indicator()
        
        # RSI
        rsi = RSIIndicator(close=df['close'], window=self.params['rsi_period'])
        indicators['rsi'] = rsi.rsi()
        
        # MACD
        macd = MACD(close=df['close'], 
                    window_fast=self.params['macd_fast'],
                    window_slow=self.params['macd_slow'],
                    window_sign=self.params['macd_signal'])
        indicators['macd'] = macd.macd()
        indicators['macd_signal'] = macd.macd_signal()
        indicators['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bollinger = BollingerBands(close=df['close'], window=20, window_dev=2)
        indicators['bb_upper'] = bollinger.bollinger_hband()
        indicators['bb_middle'] = bollinger.bollinger_mavg()
        indicators['bb_lower'] = bollinger.bollinger_lband()
        
        # הוספת האינדיקטורים ל-DataFrame
        for key, value in indicators.items():
            df[key] = value
        
        return df
    
    def get_trend_signal(self, df):
        """זיהוי מגמה - עולה/יורדת/צדדית"""
        if df is None or len(df) < 50:
            return "Unknown"
        
        latest = df.iloc[-1]
        
        # בדיקת מיקום המחיר ביחס לממוצעים נעים
        if latest['close'] > latest['sma_20'] > latest['sma_50']:
            return "Strong Uptrend"
        elif latest['close'] > latest['sma_20']:
            return "Uptrend"
        elif latest['close'] < latest['sma_20'] < latest['sma_50']:
            return "Strong Downtrend"
        elif latest['close'] < latest['sma_20']:
            return "Downtrend"
        else:
            return "Sideways"
    
    def get_momentum_signal(self, df):
        """בדיקת מומנטום על בסיס RSI ו-MACD"""
        if df is None or len(df) < 50:
            return "Unknown"
        
        latest = df.iloc[-1]
        signals = []
        
        # RSI
        if latest['rsi'] < self.params['rsi_oversold']:
            signals.append("Oversold (RSI)")
        elif latest['rsi'] > self.params['rsi_overbought']:
            signals.append("Overbought (RSI)")
        
        # MACD
        if latest['macd_diff'] > 0:
            signals.append("Bullish (MACD)")
        else:
            signals.append("Bearish (MACD)")
        
        return ", ".join(signals) if signals else "Neutral"


class FundamentalAnalyzer:
    """מחלקה לניתוח פונדמנטלי"""
    
    def analyze_fundamentals(self, overview):
        """ניתוח נתונים פונדמנטליים"""
        if not overview:
            return {"score": 0, "analysis": "No data available"}
        
        analysis = {}
        score = 0
        
        # P/E Ratio
        try:
            pe = float(overview.get('PERatio', 0))
            if 0 < pe < 15:
                analysis['pe_rating'] = "Undervalued"
                score += 2
            elif 15 <= pe < 25:
                analysis['pe_rating'] = "Fair Value"
                score += 1
            elif pe >= 25:
                analysis['pe_rating'] = "Overvalued"
            else:
                analysis['pe_rating'] = "N/A"
        except:
            analysis['pe_rating'] = "N/A"
        
        # Market Cap
        try:
            market_cap = float(overview.get('MarketCapitalization', 0))
            if market_cap > 200_000_000_000:
                analysis['size'] = "Mega Cap (Very Safe)"
                score += 2
            elif market_cap > 10_000_000_000:
                analysis['size'] = "Large Cap (Safe)"
                score += 1
            elif market_cap > 2_000_000_000:
                analysis['size'] = "Mid Cap (Moderate Risk)"
            else:
                analysis['size'] = "Small Cap (High Risk)"
                score -= 1
        except:
            analysis['size'] = "Unknown"
        
        # Dividend Yield
        try:
            div_yield = float(overview.get('DividendYield', 0))
            if div_yield > 0.03:
                analysis['dividend'] = f"Good Dividend ({div_yield*100:.2f}%)"
                score += 1
            else:
                analysis['dividend'] = "Low/No Dividend"
        except:
            analysis['dividend'] = "N/A"
        
        analysis['score'] = score
        return analysis


class RiskAssessor:
    """מחלקה להערכת סיכונים"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.thresholds = self.config['risk_thresholds']
    
    def analyze_investment_strategy(self, df, risk_rec):
        """ניתוח אסטרטגיית השקעה (DCA vs Lump Sum) עם Backtest ותחזית"""
        try:
            if df is None or len(df) < 252:
                 return {
                    "strategy": "N/A",
                    "volatility": 0,
                    "recommendation_he": "אין מספיק נתונים לחישוב אסטרטגיה (נדרשת שנה לפחות)."
                }

            # 1. חישוב תנודתיות שנתית
            daily_returns = df['close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252) * 100
            
            # 2. Backtest: השוואה בין הפקדה חד פעמית לבין DCA בשנה האחרונה
            # נניח השקעה של 12,000 דולר:
            # Lump Sum: 12,000 בתחילת התקופה (לפני 252 ימי מסחר)
            # DCA: 1,000 בכל חודש (כל 21 ימי מסחר בערך)
            
            # קח את השנה האחרונה (252 ימי מסחר)
            df_last_year = df.tail(252).copy()
            start_price = df_last_year['close'].iloc[0]
            current_price = df_last_year['close'].iloc[-1]
            
            # Lump Sum calculation
            total_investment = 12000
            shares_lump_sum = total_investment / start_price
            value_lump_sum = shares_lump_sum * current_price
            return_lump_sum = ((value_lump_sum - total_investment) / total_investment) * 100
            
            # DCA calculation (12 תשלומים של 1000)
            monthly_investment = 1000
            shares_dca = 0
            # נקודות כניסה כל ~21 ימי מסחר
            for i in range(0, 252, 21):
                if i < len(df_last_year):
                    price_at_date = df_last_year['close'].iloc[i]
                    shares_dca += monthly_investment / price_at_date
            
            value_dca = shares_dca * current_price
            return_dca = ((value_dca - total_investment) / total_investment) * 100
            
            # 3. Forecast: תחזית לשנה הבאה
            # CAGR (Compound Annual Growth Rate) - תשואה שנתית ממוצעת
            # נחשב על בסיס התשואה הכוללת של השנה האחרונה
            cagr = ((current_price / start_price) - 1)
            
            # טווחי תחזית (בהתבסס על CAGR וסטיית תקן)
            # אופטימי: CAGR + חצי סטיית תקן
            # פסימי: CAGR - סטיית תקן
            # ריאלי: CAGR
            
            # המרת תנודתיות לאחוזים עשרוניים
            vol_decimal = volatility / 100
            
            # תחזית רווח על 10,000 דולר בעוד שנה
            future_investment = 10000
            
            forecast_optimistic = future_investment * (1 + cagr + (vol_decimal * 0.5))
            forecast_realistic = future_investment * (1 + cagr)
            forecast_pessimistic = future_investment * (1 + cagr - vol_decimal)
            
            # 4. המלצה וניסוח
            strategy = "DCA" if volatility > 25 or return_dca > return_lump_sum else "Lump Sum"
            
            recommendation_he = f"📊 **ניתוח היסטורי (שנה אחרונה):**\n"
            recommendation_he += f"• **הפקדה חד-פעמית (12k)**: הניבה **{return_lump_sum:.1f}%** (שווי כיום: ${value_lump_sum:.0f})\n"
            recommendation_he += f"• **הוראת קבע (1k/חודש)**: הניבה **{return_dca:.1f}%** (שווי כיום: ${value_dca:.0f})\n\n"
            
            if return_lump_sum > return_dca:
                recommendation_he += f"💡 **מסקנה**: השקעה חד-פעמית ניצחה בשנה החולפת בפער של {(return_lump_sum - return_dca):.1f}%.\n"
            else:
                recommendation_he += f"💡 **מסקנה**: פיזור השקעות (DCA) השתלם יותר והקטין סיכונים.\n"
                
            recommendation_he += f"\n🔮 **תחזית לשנה הקרובה (עבור 10,000$):**\n"
            recommendation_he += f"• **תרחיש אופטימי**: ${forecast_optimistic:.0f} (תשואה: {((forecast_optimistic/10000)-1)*100:.1f}%)\n"
            recommendation_he += f"• **תרחיש ריאלי**: ${forecast_realistic:.0f} (תשואה: {((forecast_realistic/10000)-1)*100:.1f}%)\n"
            recommendation_he += f"• **תרחיש פסימי**: ${forecast_pessimistic:.0f} (תשואה: {((forecast_pessimistic/10000)-1)*100:.1f}%)\n"
            
            if volatility > 30:
                recommendation_he += "\n⚠️ **הערה**: התנודתיות גבוהה, הטווחים עשויים להיות רחבים יותר."

            return {
                "strategy": f"{strategy} Recommended",
                "volatility": round(volatility, 2),
                "recommendation_he": recommendation_he,
                "backtest": {
                    "lump_sum_return": round(return_lump_sum, 2),
                    "dca_return": round(return_dca, 2),
                    "winner": "Lump Sum" if return_lump_sum > return_dca else "DCA"
                },
                "forecast": {
                    "optimistic": round(forecast_optimistic, 2),
                    "realistic": round(forecast_realistic, 2),
                    "pessimistic": round(forecast_pessimistic, 2)
                }
            }
        except Exception as e:
            print(f"Error in strategy analysis: {e}")
            return {
                "strategy": "N/A",
                "volatility": 0,
                "recommendation_he": "לא ניתן לחשב אסטרטגיה בשל שגיאה בנתונים."
            }

    def assess_risk(self, df, overview):
        """הערכת רמת סיכון"""
        if df is None or len(df) < 30:
            return {"level": "Unknown", "score": 5, "factors": []}
        
        risk_score = 0
        factors = []
        
        # Volatility (סטיית תקן של תשואות יומיות)
        returns = df['close'].pct_change().dropna()
        volatility = returns.std()
        
        if volatility < self.thresholds['low_volatility']:
            factors.append("Low Volatility (Good)")
            risk_score -= 1
        elif volatility > self.thresholds['high_volatility']:
            factors.append("High Volatility (Risky)")
            risk_score += 2
        else:
            factors.append("Moderate Volatility")
            risk_score += 1
        
        # Beta
        try:
            beta = float(overview.get('Beta', 1.0))
            if beta < self.thresholds['low_beta']:
                factors.append(f"Low Beta ({beta:.2f}) - Less volatile than market")
                risk_score -= 1
            elif beta > self.thresholds['high_beta']:
                factors.append(f"High Beta ({beta:.2f}) - More volatile than market")
                risk_score += 1
            else:
                factors.append(f"Average Beta ({beta:.2f})")
        except:
            factors.append("Beta N/A")
        
        # Price trend (ירידה חדה = סיכון)
        recent_change = (df['close'].iloc[-1] / df['close'].iloc[-30] - 1) * 100
        if recent_change < -15:
            factors.append(f"Sharp Decline ({recent_change:.1f}% in 30 days)")
            risk_score += 2
        elif recent_change > 15:
            factors.append(f"Sharp Rise ({recent_change:.1f}% in 30 days)")
            risk_score += 1
        
        # קביעת רמת סיכון
        if risk_score <= 0:
            level = "Low Risk"
        elif risk_score <= 2:
            level = "Moderate Risk"
        else:
            level = "High Risk"
        
        return {
            "level": level,
            "score": risk_score,
            "factors": factors,
            "volatility": f"{volatility*100:.2f}%"
        }




class RecommendationEngine:
    """מנוע המלצות משולב"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
    
    def generate_recommendation(self, symbol, df, overview, technical_signals, risk_assessment, fundamental_analysis):
        """יצירת המלצה מקיפה"""
        
        recommendation = {
            "symbol": symbol,
            "company_name": overview.get('Name', symbol),
            "current_price": float(df['close'].iloc[-1]) if df is not None else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # ניקוד כולל
        total_score = 0
        
        # ניתוח טכני (40%)
        if technical_signals.get('trend') in ['Strong Uptrend', 'Uptrend']:
            total_score += 2
        elif technical_signals.get('trend') in ['Strong Downtrend', 'Downtrend']:
            total_score -= 2
        
        if 'Oversold' in technical_signals.get('momentum', ''):
            total_score += 1  # הזדמנות קנייה
        elif 'Overbought' in technical_signals.get('momentum', ''):
            total_score -= 1
        
        # ניתוח פונדמנטלי (30%)
        total_score += fundamental_analysis.get('score', 0) * 0.75
        
        # סיכון (30%)
        risk_score = risk_assessment.get('score', 3)
        total_score -= risk_score * 0.5
        
        # המלצה לטווח קצר (1-3 חודשים)
        if total_score >= 3:
            recommendation['short_term'] = "Strong Buy"
            recommendation['short_term_confidence'] = "High"
        elif total_score >= 1.5:
            recommendation['short_term'] = "Buy"
            recommendation['short_term_confidence'] = "Medium"
        elif total_score >= 0:
            recommendation['short_term'] = "Hold"
            recommendation['short_term_confidence'] = "Medium"
        elif total_score >= -1.5:
            recommendation['short_term'] = "Sell"
            recommendation['short_term_confidence'] = "Medium"
        else:
            recommendation['short_term'] = "Strong Sell"
            recommendation['short_term_confidence'] = "High"
        
        # המלצה לטווח ארוך (6-12 חודשים) - דגש על פונדמנטלים
        long_term_score = fundamental_analysis.get('score', 0) * 1.5 - risk_score * 0.3
        
        if long_term_score >= 2:
            recommendation['long_term'] = "Strong Buy & Hold"
        elif long_term_score >= 1:
            recommendation['long_term'] = "Buy & Hold"
        elif long_term_score >= -1:
            recommendation['long_term'] = "Hold"
        else:
            recommendation['long_term'] = "Avoid"
        
        # סיכום
        recommendation['risk_level'] = risk_assessment.get('level', 'Unknown')
        recommendation['total_score'] = round(total_score, 2)
        recommendation['technical_trend'] = technical_signals.get('trend', 'Unknown')
        recommendation['fundamental_rating'] = fundamental_analysis.get('pe_rating', 'N/A')
        
        # הסבר
        explanation = []
        explanation.append(f"Trend: {technical_signals.get('trend', 'Unknown')}")
        explanation.append(f"Momentum: {technical_signals.get('momentum', 'Unknown')}")
        explanation.append(f"Risk: {risk_assessment.get('level', 'Unknown')}")
        explanation.append(f"Valuation: {fundamental_analysis.get('pe_rating', 'N/A')}")
        
        recommendation['explanation'] = " | ".join(explanation)
        
        # הוספת ניתוח מפורט בעברית
        recommendation['detailed_analysis_he'] = self._generate_detailed_analysis(
            symbol, df, technical_signals, risk_assessment, fundamental_analysis
        )
        
        return recommendation
    
    def _generate_detailed_analysis(self, symbol, df, technical_signals, risk_assessment, fundamental_analysis):
        """יצירת ניתוח מפורט בעברית עם תחזית וניתוח טכני מתקדם"""
        if df is None or len(df) < 30:
            return "אין מספיק נתונים לניתוח מפורט"
        
        analysis_parts = []
        
        # כותרת
        analysis_parts.append(f"📊 ניתוח מעמיק של {symbol}")
        analysis_parts.append("")
        
        # נתונים בסיסיים
        latest_price = df['close'].iloc[-1]
        sma_20 = df['sma_20'].iloc[-1] if 'sma_20' in df.columns else None
        sma_50 = df['sma_50'].iloc[-1] if 'sma_50' in df.columns else None
        high_52w = df['high'].tail(252).max() if len(df) >= 252 else df['high'].max()
        low_52w = df['low'].tail(252).min() if len(df) >= 252 else df['low'].min()
        
        # חישוב תמיכה והתנגדות
        recent_highs = df['high'].tail(30).nlargest(5).mean()
        recent_lows = df['low'].tail(30).nsmallest(5).mean()
        resistance_1 = recent_highs
        support_1 = recent_lows
        resistance_2 = high_52w
        support_2 = low_52w
        
        # חישוב רמות פיבונאצ'י
        price_range = high_52w - low_52w
        fib_236 = low_52w + (price_range * 0.236)
        fib_382 = low_52w + (price_range * 0.382)
        fib_500 = low_52w + (price_range * 0.500)
        fib_618 = low_52w + (price_range * 0.618)
        
        # ניתוח נפח
        avg_volume = df['volume'].tail(30).mean()
        recent_volume = df['volume'].tail(5).mean()
        volume_trend = "עולה" if recent_volume > avg_volume * 1.2 else "יורד" if recent_volume < avg_volume * 0.8 else "יציב"
        
        # 1. ניתוח המגמה הכללית
        trend = technical_signals.get('trend', 'Unknown')
        
        analysis_parts.append("🔍 **מגמה כללית:**")
        if trend == "Strong Uptrend":
            analysis_parts.append(f"המניה נמצאת במגמת עלייה חזקה. המחיר (${latest_price:.2f}) נסחר מעל שני הממוצעים הנעים, כאשר הממוצע הקצר (SMA-20: ${sma_20:.2f}) נמצא מעל הממוצע הארוך (SMA-50: ${sma_50:.2f}). זהו סימן חיובי המעיד על כוח קונים.")
        elif trend == "Uptrend":
            analysis_parts.append(f"המניה במגמת עלייה מתונה. המחיר (${latest_price:.2f}) נסחר מעל הממוצע הקצר (${sma_20:.2f}), אך קרוב לממוצע הארוך. יש פוטנציאל להמשך עלייה אם תישמר התמיכה.")
        elif trend == "Downtrend":
            analysis_parts.append(f"המניה במגמת ירידה. המחיר (${latest_price:.2f}) נסחר מתחת לממוצע הנע הקצר (${sma_20:.2f}). זהו סימן לחולשה, ומומלץ להמתין לסימני התאוששות לפני כניסה.")
        elif trend == "Strong Downtrend":
            analysis_parts.append(f"המניה במגמת ירידה חדה. המחיר (${latest_price:.2f}) נמצא מתחת לשני הממוצעים הנעים, עם הממוצע הקצר מתחת לארוך. זהו מצב שלילי המצביע על לחץ מכירות.")
        else:
            analysis_parts.append(f"המניה נעה בטווח צדדי ללא מגמה ברורה. המחיר (${latest_price:.2f}) מתנדנד סביב הממוצעים הנעים.")
        analysis_parts.append("")
        
        # 2. רמות תמיכה והתנגדות קריטיות
        analysis_parts.append("📏 **רמות תמיכה והתנגדות:**")
        analysis_parts.append(f"• **התנגדות ראשונה**: ${resistance_1:.2f} - רמה זו נוצרה מממוצע השיאים האחרונים. פריצה מעליה תאשר המשך עלייה.")
        analysis_parts.append(f"• **התנגדות שנייה**: ${resistance_2:.2f} - שיא 52 שבועות. פריצה מעל רמה זו תהיה אות חזק מאוד.")
        analysis_parts.append(f"• **תמיכה ראשונה**: ${support_1:.2f} - רמת תמיכה מרכזית. שמירה מעליה חיונית.")
        analysis_parts.append(f"• **תמיכה שנייה**: ${support_2:.2f} - שפל 52 שבועות. ירידה מתחת לרמה זו תהיה שלילית מאוד.")
        
        # מרחק מרמות
        dist_to_resistance = ((resistance_1 - latest_price) / latest_price * 100)
        dist_to_support = ((latest_price - support_1) / latest_price * 100)
        analysis_parts.append(f"• **מיקום נוכחי**: המחיר נמצא {dist_to_support:.1f}% מעל התמיכה ו-{dist_to_resistance:.1f}% מתחת להתנגדות.")
        analysis_parts.append("")
        
        # 3. רמות פיבונאצ'י
        analysis_parts.append("🔢 **רמות פיבונאצ'י (מבוססות על טווח 52 שבועות):**")
        analysis_parts.append(f"• Fib 23.6%: ${fib_236:.2f}")
        analysis_parts.append(f"• Fib 38.2%: ${fib_382:.2f}")
        analysis_parts.append(f"• Fib 50.0%: ${fib_500:.2f} - רמת איזון מרכזית")
        analysis_parts.append(f"• Fib 61.8%: ${fib_618:.2f} - רמת פיבונאצ'י הזהב")
        
        # זיהוי רמת פיבונאצ'י הקרובה
        fib_levels = [
            (fib_236, "23.6%"),
            (fib_382, "38.2%"),
            (fib_500, "50.0%"),
            (fib_618, "61.8%")
        ]
        closest_fib = min(fib_levels, key=lambda x: abs(x[0] - latest_price))
        analysis_parts.append(f"• **המחיר הנוכחי קרוב לרמת Fib {closest_fib[1]}** (${closest_fib[0]:.2f})")
        analysis_parts.append("")
        
        # 4. ניתוח מומנטום
        rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else None
        macd_diff = df['macd_diff'].iloc[-1] if 'macd_diff' in df.columns else None
        
        analysis_parts.append("⚡ **מומנטום ואינדיקטורים:**")
        if rsi is not None:
            if rsi < 30:
                analysis_parts.append(f"• **RSI: {rsi:.1f}** - המניה במצב oversold (מכירת יתר). זו הזדמנות קנייה פוטנציאלית! המחיר עשוי להתאושש בקרוב.")
            elif rsi > 70:
                analysis_parts.append(f"• **RSI: {rsi:.1f}** - המניה במצב overbought (קנייה מוגזמת). סיכון גבוה לתיקון מחירים. שקול לקחת רווחים.")
            else:
                analysis_parts.append(f"• **RSI: {rsi:.1f}** - אזור נייטרלי. המניה לא קיצונית, מה שמאפשר תנועה לשני הכיוונים.")
        
        if macd_diff is not None:
            if macd_diff > 0:
                analysis_parts.append(f"• **MACD**: חיובי ({macd_diff:.2f}) - קו ה-MACD מעל קו האות. מומנטום עולה, פוטנציאל להמשך עלייה.")
            else:
                analysis_parts.append(f"• **MACD**: שלילי ({macd_diff:.2f}) - קו ה-MACD מתחת לקו האות. מומנטום יורד, לחץ מכירות.")
        analysis_parts.append("")
        
        # 5. ניתוח נפח מסחר
        analysis_parts.append("📊 **ניתוח נפח מסחר:**")
        analysis_parts.append(f"• **נפח ממוצע (30 יום)**: {avg_volume:,.0f} מניות")
        analysis_parts.append(f"• **נפח אחרון (5 ימים)**: {recent_volume:,.0f} מניות")
        analysis_parts.append(f"• **מגמת נפח**: {volume_trend}")
        
        if volume_trend == "עולה":
            analysis_parts.append("• **פרשנות**: עלייה בנפח מצביעה על עניין גובר במניה. אם המחיר עולה - זה חיובי. אם יורד - זה שלילי.")
        elif volume_trend == "יורד":
            analysis_parts.append("• **פרשנות**: ירידה בנפח עשויה להצביע על חוסר עניין. תנועות מחיר בנפח נמוך פחות אמינות.")
        else:
            analysis_parts.append("• **פרשנות**: נפח יציב מעיד על מסחר רגיל ללא אירועים חריגים.")
        analysis_parts.append("")
        
        # 6. זיהוי דפוסי גרף
        analysis_parts.append("🎯 **זיהוי דפוסי גרף:**")
        
        # בדיקת דפוס ראש וכתפיים
        recent_prices = df['close'].tail(60)
        if len(recent_prices) >= 60:
            mid_point = len(recent_prices) // 2
            left_shoulder = recent_prices.iloc[:20].max()
            head = recent_prices.iloc[20:40].max()
            right_shoulder = recent_prices.iloc[40:].max()
            
            if head > left_shoulder * 1.05 and head > right_shoulder * 1.05:
                if abs(left_shoulder - right_shoulder) / left_shoulder < 0.05:
                    analysis_parts.append("• **⚠️ דפוס ראש וכתפיים אפשרי** - דפוס היפוך שלילי. אם המחיר ישבור את קו הצוואר, צפויה ירידה.")
                    neckline = min(recent_prices.iloc[15:25].min(), recent_prices.iloc[35:45].min())
                    target = neckline - (head - neckline)
                    analysis_parts.append(f"  - קו צוואר משוער: ${neckline:.2f}")
                    analysis_parts.append(f"  - יעד ירידה פוטנציאלי: ${target:.2f}")
        
        # בדיקת דפוס משולש
        highs_trend = df['high'].tail(30)
        lows_trend = df['low'].tail(30)
        if len(highs_trend) >= 30:
            high_slope = (highs_trend.iloc[-1] - highs_trend.iloc[0]) / len(highs_trend)
            low_slope = (lows_trend.iloc[-1] - lows_trend.iloc[0]) / len(lows_trend)
            
            if abs(high_slope) < 0.5 and abs(low_slope) < 0.5:
                if abs(high_slope - low_slope) < 0.2:
                    analysis_parts.append("• **📐 דפוס משולש סימטרי** - דפוס המשך. פריצה עשויה להיות חזקה לכיוון המגמה הקודמת.")
        
        # בדיקת ממוצעים נעים (Golden Cross / Death Cross)
        if sma_20 and sma_50:
            sma_20_prev = df['sma_20'].iloc[-5] if len(df) >= 5 else sma_20
            sma_50_prev = df['sma_50'].iloc[-5] if len(df) >= 5 else sma_50
            
            if sma_20 > sma_50 and sma_20_prev <= sma_50_prev:
                analysis_parts.append("• **✨ Golden Cross!** - הממוצע הקצר חצה את הארוך כלפי מעלה. סימן שורי חזק מאוד!")
            elif sma_20 < sma_50 and sma_20_prev >= sma_50_prev:
                analysis_parts.append("• **💀 Death Cross!** - הממוצע הקצר חצה את הארוך כלפי מטה. סימן דובי חזק!")
        
        if len(analysis_parts) == len([x for x in analysis_parts if x.startswith("🎯")]) + 1:
            analysis_parts.append("• לא זוהו דפוסי גרף מיוחדים כרגע. המניה בתנועה רגילה.")
        analysis_parts.append("")
        
        # 7. ניתוח תנודתיות וסיכון
        analysis_parts.append("⚠️ **סיכון ותנודתיות:**")
        risk_level = risk_assessment.get('level', 'Unknown')
        volatility = risk_assessment.get('volatility', 'N/A')
        
        if "Low" in risk_level:
            analysis_parts.append(f"• **רמת סיכון נמוכה** ({volatility} תנודתיות) - המניה יציבה ומתאימה למשקיעים שמרניים.")
        elif "Moderate" in risk_level:
            analysis_parts.append(f"• **רמת סיכון בינונית** ({volatility} תנודתיות) - תנודתיות סבירה, מתאים למשקיעים עם סובלנות ממוצעת.")
        else:
            analysis_parts.append(f"• **רמת סיכון גבוהה** ({volatility} תנודתיות) - המניה תנודתית מאוד! רק למשקיעים מנוסים.")
        analysis_parts.append("")
        
        # 8. ביצועים אחרונים
        change_7d = ((df['close'].iloc[-1] / df['close'].iloc[-7] - 1) * 100) if len(df) >= 7 else 0
        change_30d = ((df['close'].iloc[-1] / df['close'].iloc[-30] - 1) * 100) if len(df) >= 30 else 0
        change_90d = ((df['close'].iloc[-1] / df['close'].iloc[-90] - 1) * 100) if len(df) >= 90 else 0
        
        analysis_parts.append("📈 **ביצועים אחרונים:**")
        analysis_parts.append(f"• שבוע אחרון: {change_7d:+.2f}%")
        analysis_parts.append(f"• 30 יום: {change_30d:+.2f}%")
        analysis_parts.append(f"• 90 יום: {change_90d:+.2f}%")
        analysis_parts.append("")
        
        # 9. תחזית ויעדי מחיר
        analysis_parts.append("🎯 **תחזית ויעדי מחיר:**")
        
        # חישוב ציון תחזית
        forecast_score = 0
        if trend in ["Strong Uptrend", "Uptrend"]: forecast_score += 2
        elif trend in ["Strong Downtrend", "Downtrend"]: forecast_score -= 2
        
        if rsi and rsi < 40: forecast_score += 1
        elif rsi and rsi > 60: forecast_score -= 1
        
        if macd_diff and macd_diff > 0: forecast_score += 1
        elif macd_diff and macd_diff < 0: forecast_score -= 1
        
        if volume_trend == "עולה" and change_7d > 0: forecast_score += 1
        elif volume_trend == "עולה" and change_7d < 0: forecast_score -= 1
        
        # יעדי מחיר
        if forecast_score >= 3:
            target_high = latest_price * 1.15
            target_low = latest_price * 1.05
            analysis_parts.append("✅ **תחזית חיובית מאוד**: כל האינדיקטורים מצביעים על המשך עלייה חזקה.")
            analysis_parts.append(f"• **יעד מחיר (1-3 חודשים)**: ${target_low:.2f} - ${target_high:.2f}")
            analysis_parts.append(f"• **פוטנציאל עלייה**: 5-15%")
            analysis_parts.append(f"• **נקודת כניסה מומלצת**: ${latest_price * 0.98:.2f} - ${latest_price:.2f}")
            analysis_parts.append(f"• **Stop Loss מומלץ**: ${support_1 * 0.97:.2f} (מתחת לתמיכה)")
        elif forecast_score >= 1:
            target_high = latest_price * 1.08
            target_low = latest_price * 1.02
            analysis_parts.append("📈 **תחזית חיובית**: סיכויים טובים לעלייה מתונה.")
            analysis_parts.append(f"• **יעד מחיר (1-3 חודשים)**: ${target_low:.2f} - ${target_high:.2f}")
            analysis_parts.append(f"• **פוטנציאל עלייה**: 2-8%")
            analysis_parts.append(f"• **נקודת כניסה**: סביב המחיר הנוכחי או בתיקון קל")
        elif forecast_score >= -1:
            analysis_parts.append("➡️ **תחזית נייטרלית**: המניה צפויה לנוע בטווח. המתן לפריצה ברורה.")
            analysis_parts.append(f"• **טווח צפוי**: ${support_1:.2f} - ${resistance_1:.2f}")
            analysis_parts.append(f"• **אסטרטגיה**: קנה בתמיכה, מכור בהתנגדות")
        elif forecast_score >= -3:
            target_low = latest_price * 0.92
            target_high = latest_price * 0.98
            analysis_parts.append("📉 **תחזית שלילית**: סיכון לירידה מתונה.")
            analysis_parts.append(f"• **יעד ירידה אפשרי**: ${target_low:.2f} - ${target_high:.2f}")
            analysis_parts.append(f"• **המלצה**: שקול לקחת רווחים או להמתין מחוץ לשוק")
        else:
            target_low = latest_price * 0.85
            target_high = latest_price * 0.92
            analysis_parts.append("⛔ **תחזית שלילית מאוד**: סיכון גבוה לירידה חדה.")
            analysis_parts.append(f"• **יעד ירידה צפוי**: ${target_low:.2f} - ${target_high:.2f}")
            analysis_parts.append(f"• **המלצה**: הימנע מהמניה או שקול short")
        
        analysis_parts.append("")
        analysis_parts.append("⚠️ **אזהרה**: ניתוח זה מבוסס על נתונים טכניים והיסטוריים בלבד ואינו מהווה ייעוץ השקעות. תמיד התייעץ עם יועץ פיננסי מקצועי לפני קבלת החלטות השקעה.")
        
        return "\n".join(analysis_parts)


class StockAnalysisSystem:
    """מערכת מרכזית לניתוח מניות"""
    
    def __init__(self, config_path='config.json'):
        self.fetcher = StockDataFetcher(config_path)
        self.technical = TechnicalAnalyzer(config_path)
        self.fundamental = FundamentalAnalyzer()
        self.risk = RiskAssessor(config_path)
        self.recommender = RecommendationEngine(config_path)
    
    def scan_market_cached(self, limit=30):
        """סריקת שוק אופטימלית עם Batch Fetching וזיכרון מטמון (Cache)"""
        cache_file = 'scan_cache.json'
        symbols = self.fetcher.get_market_stocks(limit=limit)
        
        # 1. בדוק אם יש מטמון בתוקף (30 דקות)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
                    if (datetime.now() - cache_time).total_seconds() < 1800: # 30 min
                        print("📡 Using cached market scan data...")
                        return cache_data['results']
            except Exception as e:
                print(f"Cache read error: {e}")

        # 2. שליפה קבוצתית (Batch Fetch) מ-Yahoo Finance
        # זה הפתרון האמיתי לחסימות - בקשה אחת לכל המניות במקום 30 נפרדות
        batch_df = self.fetcher.get_batch_yfinance_data(symbols)
        
        recommendations = []
        if batch_df is not None and not batch_df.empty:
            print(f"✅ Batch data received for {len(symbols)} stocks")
            
            for symbol in symbols:
                try:
                    # חילוץ נתונים למניה הבודדת מתוך ה-Batch
                    if symbol in batch_df.columns.levels[0]:
                        df = batch_df[symbol].copy()
                        df = df.dropna()
                        if df.empty or len(df) < 20: continue
                        
                        # התאמת שמות עמודות ל-analyzer
                        df.columns = df.columns.str.lower()
                        
                        # ניתוח טכני בסיסי ומהיר לסריקה
                        df = self.technical.calculate_indicators(df)
                        trend = self.technical.get_trend_signal(df)
                        rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else None
                        
                        # המרת סטטיסטיקה בסיסית
                        price = float(df['close'].iloc[-1])
                        prev_price = float(df['close'].iloc[-2]) if len(df) > 1 else price
                        change = ((price / prev_price) - 1) * 100
                        
                        recommendations.append({
                            "symbol": symbol,
                            "name": symbol,
                            "price": price,
                            "change": change,
                            "trend": trend,
                            "rsi": round(rsi, 2) if rsi else "N/A",
                            "score": 2 if "Uptrend" in trend else 0 # פשטות לסריקה
                        })
                except Exception as e:
                    print(f"Error processing {symbol} in batch: {e}")
                    continue

        # מיון
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        # שמירה למטמון
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "results": recommendations
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Cache write error: {e}")

        return self._clean_data(recommendations)

    def _clean_data(self, data):
        """המרת ערכי NaN ל-None כדי שה-JSON יהיה תקני"""
        if isinstance(data, dict):
            return {k: self._clean_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_data(v) for v in data]
        elif isinstance(data, float):
            if np.isnan(data) or np.isinf(data):
                return None
        return data

    def analyze_stock(self, symbol):
        """ניתוח מקיף של מניה"""
        print(f"Analyzing {symbol}...")
        
        # איסוף נתונים
        df = self.fetcher.get_stock_data(symbol)
        overview = self.fetcher.get_company_overview(symbol)
        
        if df is None or df.empty:
            # זה לא אמור לקרות עכשיו בגלל ה-Mock, אבל רק לביטחון
            return {"error": f"Could not fetch data for {symbol} (API Blocked)"}

        if not overview:
             overview = {'Name': symbol, 'Symbol': symbol, 'Description': 'Data currently limited due to API limits.'}
        df = self.technical.calculate_indicators(df)
        technical_signals = {
            "trend": self.technical.get_trend_signal(df),
            "momentum": self.technical.get_momentum_signal(df)
        }
        
        # ניתוח פונדמנטלי
        fundamental_analysis = self.fundamental.analyze_fundamentals(overview)
        
        # הערכת סיכון
        risk_assessment = self.risk.assess_risk(df, overview)

        # חישוב ביצועים (Performance)
        performance = self._calculate_performance(df)
        
        # חדשות
        news = self.fetcher.get_stock_news(symbol)
        
        # אסטרטגיית השקעה (DCA vs Lump Sum)
        investment_strategy = self.risk.analyze_investment_strategy(df, risk_assessment)
        
        # המלצה
        recommendation = self.recommender.generate_recommendation(
            symbol, df, overview, technical_signals, risk_assessment, fundamental_analysis
        )
        
        # יצירת טקסט הסבר מפורט
        detailed_explanation = self.recommender._generate_detailed_analysis(
            symbol, df, technical_signals, risk_assessment, fundamental_analysis
        )
        recommendation["explanation"] = detailed_explanation
        
        # 6. News Analysis
        try:
            print(f"Fetching news for {symbol} (inside analyze_stock)...")
            news = self.fetcher.get_stock_news(symbol)
            if not news:
                print(f"No news found for {symbol}")
                news = [] # Real data only: empty list if no news
        except Exception as e:
            print(f"Error getting news: {e}")
            news = [] # Real data only: empty list on error

        # 7. Investment Strategy
        try:
            print("Calculating investment strategy...")
            investment_strategy = self.risk.analyze_investment_strategy(df, risk_assessment)
            print(f"Strategy calculated: {investment_strategy.get('strategy', 'Unknown')}")
        except Exception as e:
            print(f"CRITICAL ERROR calculating strategy: {e}")
            investment_strategy = {
                "strategy": "N/A",
                "volatility": 0,
                "recommendation_he": "לא ניתן לחשב אסטרטגיה כעת"
            }

        # Prepare variables for the new result structure
        current_price = float(df['close'].iloc[-1])
        change_percent = float((df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100) if len(df) > 1 else 0
        
        # Helper function for safe scalar retrieval
        def safe_get_scalar(series_value):
            try:
                return float(series_value)
            except (TypeError, ValueError):
                return None

        # Ensure compatibility
        company_overview = overview

        # Build the result dictionary
        # IMPORTANT: rec_data contains short_term, long_term, etc.
        rec_data = recommendation if isinstance(recommendation, dict) else {}
        
        result = {
            "recommendation": {
                "symbol": symbol,
                "company_name": company_overview.get('Name', symbol),
                "current_price": current_price, # Added specifically for app.js if it uses it here
                
                # Unpack recommendation data directly here
                "short_term": rec_data.get('short_term', 'Hold'),
                "long_term": rec_data.get('long_term', 'Hold'),
                "short_term_confidence": rec_data.get('short_term_confidence', 'N/A'),
                "long_term_confidence": rec_data.get('long_term_confidence', 'N/A'),
                "signal_strength": rec_data.get('signal_strength', 0),
                
                "explanation": detailed_explanation,
                "detailed_analysis_he": detailed_explanation, # Duplicate for compatibility
                "risk_level": risk_assessment.get('level'),
                "risk_details": risk_assessment.get('details')
            },
            
            # CRITICAL: RESTORE 'risk' KEY FOR API SERVER
            "risk": risk_assessment,
            
            "price_data": {
                "current_price": current_price,
                "change_percent": change_percent,
                "change_30d": ((current_price - df['close'].iloc[-22]) / df['close'].iloc[-22] * 100) if len(df) > 22 else 0,
                "high_52w": float(df['close'].max()),
                "low_52w": float(df['close'].min()),
                "volume": int(df['volume'].iloc[-1])
            },
            "technical": {
                "trend": technical_signals.get('trend'),
                "momentum": technical_signals.get('momentum'),
                "rsi": safe_get_scalar(df['rsi'].iloc[-1]) if 'rsi' in df.columns else None,
                "macd": safe_get_scalar(df['macd'].iloc[-1]) if 'macd' in df.columns else None
            },
            "fundamental": {
                "pe_rating": overview.get('PERatio', 'N/A'),
                "market_cap": overview.get('MarketCapitalization', 'N/A')
            },
            "overview": {
                "market_cap": overview.get('MarketCapitalization', 'N/A'),
                "beta": overview.get('Beta', 'N/A')
            },
            "chart_data": self._prepare_chart_data(df),
            "performance": performance,
            "news": news,
            "investment_strategy": investment_strategy
        }
        # שלב האחרון - ניקוי נתונים ל-JSON
        return self._clean_data(result)

    def _prepare_chart_data(self, df):
        """הכנת נתונים לגרף"""
        # לקחת 90 ימים אחרונים
        recent_df = df.tail(90).replace({np.nan: None})
        
        return {
            "dates": recent_df.index.strftime('%Y-%m-%d').tolist(),
            "prices": recent_df['close'].tolist(),
            "sma_20": recent_df['sma_20'].tolist() if 'sma_20' in recent_df.columns else [],
            "sma_50": recent_df['sma_50'].tolist() if 'sma_50' in recent_df.columns else [],
            "volume": recent_df['volume'].tolist()
        }

    def _calculate_performance(self, df):
        """חישוב ביצועים לטווחי זמן שונים"""
        if df is None or df.empty:
            return {}
            
        current_price = df['close'].iloc[-1]
        dates = df.index
        results = {}
        
        # Helper to find close price N days ago (nearest)
        def get_price_ago(days):
            try:
                target_date = dates[-1] - pd.Timedelta(days=days)
                # Find nearest date index
                # טריק: להשתמש ב-asof אם האינדקס ממויין, או חיפוש קרוב
                idx = df.index.get_indexer([target_date], method='nearest')[0]
                if idx < 0 or idx >= len(df):
                    return None
                return df['close'].iloc[idx]
            except:
                return None

        # 1 Day (Regular Change)
        prev_close = df['close'].iloc[-2] if len(df) > 1 else current_price
        results['1D'] = {'base': float(prev_close), 'change': float((current_price / prev_close) - 1)}
        
        # 5 Days
        price_5d = get_price_ago(5)
        if price_5d: results['5D'] = {'base': float(price_5d), 'change': float((current_price / price_5d) - 1)}
        
        # 1 Month (30 days)
        price_1m = get_price_ago(30)
        if price_1m: results['1M'] = {'base': float(price_1m), 'change': float((current_price / price_1m) - 1)}
        
        # 6 Months (180 days)
        price_6m = get_price_ago(180)
        if price_6m: results['6M'] = {'base': float(price_6m), 'change': float((current_price / price_6m) - 1)}
        
        # YTD (Start of current year)
        try:
            current_year = dates[-1].year
            start_of_year = pd.Timestamp(f"{current_year}-01-01").tz_localize(dates[-1].tz)
            # Find first trading day of year
            ytd_idx = df.index.searchsorted(start_of_year)
            if ytd_idx < len(df):
                price_ytd = df['close'].iloc[ytd_idx]
                results['YTD'] = {'base': float(price_ytd), 'change': float((current_price / price_ytd) - 1)}
        except:
            pass # YTD not available
            
        # 1 Year
        price_1y = get_price_ago(365)
        if price_1y: results['1Y'] = {'base': float(price_1y), 'change': float((current_price / price_1y) - 1)}
        
        # 5 Years
        price_5y = get_price_ago(365*5)
        if price_5y: results['5Y'] = {'base': float(price_5y), 'change': float((current_price / price_5y) - 1)}
        
        return results

    def _fetch_google_news_rss(self, symbol):
        """גיבוי: משיכת חדשות מ-Google News RSS"""
        try:
            print(f"Fetching backup news from Google RSS for {symbol}...")
            url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                news_items = []
                for item in root.findall('.//item')[:5]:
                    title = item.find('title').text
                    link = item.find('link').text
                    pubDate = item.find('pubDate').text
                    source = item.find('source').text if item.find('source') is not None else 'Google News'
                    
                    # המרת תאריך
                    try:
                        dt = datetime.strptime(pubDate, '%a, %d %b %Y %H:%M:%S %Z')
                        pub_fmt = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pub_fmt = pubDate
                        
                    news_items.append({
                        'title': title,
                        'publisher': source,
                        'link': link,
                        'published': pub_fmt,
                        'type': 'STORY'
                    })
                return news_items
        except Exception as e:
            print(f"Google RSS failed: {e}")
        return []


if __name__ == "__main__":
    # בדיקה
    system = StockAnalysisSystem()
    result = system.analyze_stock("AAPL")
    print(json.dumps(result, indent=2, default=str))
