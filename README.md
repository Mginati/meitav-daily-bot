# 🏦 בוט דוח יומי מיטב

בוט טלגרם לניתוח אוטומטי של דוחות יומיים ממיטב.

## ✨ מה הבוט עושה?

1. מקבל פקודה "דוח" בטלגרם
2. נכנס ל-Gmail ומחפש את הדוח האחרון ממיטב
3. נכנס לאתר מיטב ומבקש קוד OTP
4. מחכה שתזין את הקוד
5. מוריד את קובץ ה-Excel
6. מנתח ושולח סיכום מפורט

## 📊 מה מנותח?

- 🔴 ריג'קטים בהצטרפות
- ⏳ ממתינים להפקדה ראשונה
- 📥 צפי ניוד נכנס
- 📤 ניוד יוצא
- 🆕 הצטרפויות חדשות

## 🚀 התקנה על Render

### שלב 1: העלאה ל-GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/meitav-bot.git
git push -u origin main
```

### שלב 2: הגדרת Gmail API

1. לך ל-[Google Cloud Console](https://console.cloud.google.com)
2. צור פרויקט חדש
3. הפעל את Gmail API
4. צור OAuth 2.0 credentials
5. הורד את הקובץ ושמור את:
   - Client ID
   - Client Secret
6. הרץ `python get_gmail_token.py` מקומית לקבלת Refresh Token

### שלב 3: הגדרת Render

1. לך ל-[Render Dashboard](https://dashboard.render.com)
2. לחץ "New" → "Web Service"
3. חבר את ה-GitHub repo
4. הגדר Environment Variables:

| Variable | Value |
|----------|-------|
| `TELEGRAM_TOKEN` | `8556362815:AAF-qSPbXrWDAcSErRMLpYMy5vMsYDz2umU` |
| `CHAT_ID` | `424508467` |
| `MEITAV_ID` | `066624669` |
| `GMAIL_CLIENT_ID` | (מ-Google Cloud Console) |
| `GMAIL_CLIENT_SECRET` | (מ-Google Cloud Console) |
| `GMAIL_REFRESH_TOKEN` | (מהרצה מקומית) |

5. לחץ "Create Web Service"

## 📱 שימוש

שלח לבוט בטלגרם:
- `דוח` - לקבלת הדוח האחרון
- `סטטוס` - בדיקת סטטוס
- `עזרה` - רשימת פקודות

## 🔧 פיתוח מקומי

```bash
# התקנת תלויות
pip install -r requirements.txt
playwright install chromium

# הרצה
python main.py
```

## 📝 רישיון

MIT
