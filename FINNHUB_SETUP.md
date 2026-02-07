# 🔑 איך לקבל Finnhub API Key (חינמי!)

## שלב 1: הרשמה
1. **לך ל-https://finnhub.io/register**
2. **הירשם בחינם** - אפשר עם:
   - Google Account
   - GitHub
   - או Email רגיל

## שלב 2: קבלת ה-Key
1. אחרי ההרשמה תועבר ל-Dashboard
2. תראה את ה-**API Key** שלך (מחרוזת ארוכה)
3. **העתק את ה-Key**

## שלב 3: הוספת ה-Key למערכת
1. פתח את הקובץ `config.json`
2. מצא את השורה:
   ```json
   "finnhub_key": "PUT_YOUR_FINNHUB_KEY_HERE",
   ```
3. **החלף** את `PUT_YOUR_FINNHUB_KEY_HERE` ב-key שקיבלת
4. **שמור** את הקובץ

דוגמה:
```json
{
  "api_key": "5Y77AYI6OPCNOEX5",
  "finnhub_key": "ct1abc2pr01def3ghijk",
  "api_provider": "finnhub",
  ...
}
```

## שלב 4: הרצת המערכת
1. **עצור את השרת** (Ctrl+C)
2. **הרץ מחדש**:
```powershell
C:\Users\maple\AppData\Local\Programs\Python\Python312\python.exe api_server.py
```
3. **פתח את index.html** בדפדפן
4. **נסה לנתח מניה** - תקבל נתונים אמיתיים! ✅

## מגבלות (חינם)
- ✅ **60 קריאות לדקה**
- ✅ **נתונים היסטוריים**
- ✅ **מידע על חברות**
- ✅ **מחירים בזמן אמת** (עיכוב של 15 דקות)

זה הרבה יותר מספיק לשימוש רגיל!

## אם אין לך Finnhub Key
המערכת תעבור אוטומטית ל:
1. Alpha Vantage (אם יש קריאות פנויות)
2. Yahoo Finance
3. נתוני DEMO (אם הכל נכשל)

אבל **מומלץ מאוד לקבל Finnhub key** - זה לוקח 30 שניות ונותן נתונים אמיתיים!
