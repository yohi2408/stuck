
# מדריך העלאה לרשת (Deployment Guide)

כדי שלחבר שלך יהיה גישה למערכת, נשתמש בשירות אחסון חינמי ומצוין בשם **Render**.
התהליך מורכב מ-3 שלבים:

## 1. הכנת הקבצים (בוצע!)
- הכנתי לך את הקבצים הדרושים (`Procfile`, `requirements.txt`).
- **אין צורך שתתקין את gunicorn אצלך במחשב** (זה ללינוקס, והשרת של Render הוא על לינוקס).

## 2. העלאה ל-GitHub
Render עובד הכי טוב עם GitHub.
1.  פתח חשבון ב-[GitHub](https://github.com/).
2.  צור **New Repository** (מאגר חדש).
3.  העלה את כל הקבצים מתיקיית `interactive` למאגר שיצרת.
    *   הקבצים החשובים הם: `api_server.py`, `stock_analyzer.py`, `app.js`, `index.html`, `styles.css`, `requirements.txt`, `Procfile`, `config.json`.

## 3. יצירת חשבון וחיבור ב-Render
1.  הירשם ל-[Render.com](https://render.com/) (אפשר עם חשבון ה-GitHub).
2.  לחץ על **New +** ובחר **Web Service**.
3.  חבר את GitHub ובחר את ה-Repository שלך.
4.  תן שם לאפליקציה (למשל `stock-app-shlomi`).
5.  ודא שמוגדר:
    *   **Runtime**: Python 3
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `gunicorn api_server:app`
6.  לחץ **Create Web Service**.

אחרי 1-2 דקות האפליקציה תהיה באוויר ותקבל כתובת URL לשלוח לחבר.

### ⚠️ שים לב למפתחות
המפתחות ל-API (כמו Finnhub) שמורים כרגע בקובץ `config.json`. אם המאגר שלך ב-GitHub הוא ציבורי (Public), כולם יוכלו לראות אותם.
מומלץ להפוך את המאגר ל-Private, או להגדיר את המפתחות בנפרד ב-Render (אבל זה דורש שינוי קטן בקוד). לשימוש פרטי עם חבר, Private Repository זה הפתרון הכי פשוט.
