# 🐛 מדריך פתרון בעיות - בוט דוח יומי מיטב

## בעיה: "לא נמצא דוח חדש ממיטב"

### שלב 1: בדיקת חיבור Gmail

שלח לבוט בטלגרם: `בדיקה`

הבוט יציג את המיילים שנמצאו ממיטב.

#### תוצאות אפשריות:

**א. "לא נמצאו מיילים ממיטב"**
- ✅ **פתרון:** בדוק שהגישה ל-Gmail פועלת ושיש מיילים מ-meitavdashnoreply@meitav.co.il
- ✅ **פתרון:** וודא שה-Refresh Token לא פג תוקף (הרץ שוב `python get_gmail_token.py`)

**ב. "נמצאו מיילים אבל לא עם הנושא הנכון"**
- ✅ **פתרון:** בדוק את נושא המיילים שהבוט מצא
- ✅ **פתרון:** אם הנושא שונה מ-"דוח יומי לסוכן", עדכן את הקוד:

```python
# ב-gmail_handler.py שורה 80:
query = 'from:meitavdashnoreply@meitav.co.il subject:"הנושא החדש כאן"'
```

**ג. "שגיאה בחיבור ל-Gmail"**
- ✅ **פתרון:** בדוק את משתני הסביבה ב-Render:
  - `GMAIL_CLIENT_ID`
  - `GMAIL_CLIENT_SECRET`
  - `GMAIL_REFRESH_TOKEN`

---

### שלב 2: בדיקת משתני סביבה

הרץ מקומית:
```bash
python check_env.py
```

וודא שכל המשתנים הבאים קיימים:
- ✅ `TELEGRAM_TOKEN`
- ✅ `CHAT_ID`
- ✅ `MEITAV_ID`
- ✅ `GMAIL_CLIENT_ID`
- ✅ `GMAIL_CLIENT_SECRET`
- ✅ `GMAIL_REFRESH_TOKEN`

---

### שלב 3: בדיקת לוגים

1. היכנס ל-[Render Dashboard](https://dashboard.render.com)
2. בחר את השירות שלך
3. לחץ על "Logs"
4. חפש שגיאות הקשורות ל-Gmail:
   - `Gmail authenticated successfully` - טוב! החיבור עובד
   - `Error getting Meitav email` - יש בעיה בחיבור
   - `No Meitav emails found` - אין מיילים מהיום

---

### שלב 4: בדיקת תוקף Refresh Token

אם החיבור ל-Gmail נכשל, ייתכן שה-Refresh Token פג.

**איך ליצור Refresh Token חדש:**

1. הורד את `credentials.json` מ-Google Cloud Console
2. שים אותו בתיקיית הפרויקט
3. הרץ מקומית:
```bash
python get_gmail_token.py
```
4. התחבר לחשבון Gmail שלך
5. העתק את ה-Refresh Token החדש
6. עדכן אותו ב-Render → Environment Variables → `GMAIL_REFRESH_TOKEN`
7. אתחל את השירות ב-Render (Manual Deploy)

---

## בעיות נוספות

### הבוט לא עונה בכלל

**סימפטומים:** הבוט לא משיב לפקודות

**פתרון:**
1. בדוק ב-Render Dashboard שהשירות במצב "Live" (ירוק)
2. בדוק שה-`TELEGRAM_TOKEN` נכון
3. נסה לשלוח `/start` - זה צריך לתת תשובה תמיד
4. וודא שה-`CHAT_ID` שלך נכון - ניתן לקבל אותו דרך @userinfobot

### שגיאה בהזנת OTP

**סימפטומים:** "לא הצלחתי להוריד את הקובץ"

**פתרון:**
1. וודא שהזנת בדיוק 4 ספרות
2. הקוד תקף רק כ-2 דקות - אם עבר הזמן, התחל מחדש
3. וודא שה-`MEITAV_ID` נכון במשתני הסביבה

### הבוט מוצא את המייל אבל לא מוריד את הקובץ

**סימפטומים:** "שגיאה בכניסה לאתר מיטב"

**פתרון:**
1. ייתכן שממשק האתר של מיטב השתנה
2. בדוק את הלוגים - הבוט שומר צילום מסך של השגיאה
3. ייתכן שצריך לעדכן את הסלקטורים ב-[meitav_downloader.py](meitav_downloader.py)

---

## איך לקבל עזרה

אם אף אחד מהפתרונות לא עזר:

1. **צלם את הלוגים מ-Render**
2. **שלח `בדיקה` ותצלם את התוצאה**
3. **פתח Issue ב-GitHub עם:**
   - תיאור הבעיה
   - צילום מסך של השגיאה
   - חלק מהלוגים (ללא סודות!)

---

## טיפים לדיבאג

### הפעלת לוגים מפורטים

ערוך את [main.py](main.py#L22):

```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # שינוי מ-INFO ל-DEBUG
)
```

### בדיקת Gmail API ידנית

הרץ מקומית:

```python
from gmail_handler import GmailHandler
import asyncio

async def test():
    gmail = GmailHandler()
    result = await gmail.get_latest_meitav_email()
    print(result)

asyncio.run(test())
```

---

## שאלות נפוצות

**ש: הבוט עבד אתמול, למה היום לא?**
ת: ייתכן שה-Refresh Token פג או שלא הגיע מייל מיטב היום.

**ש: אפשר להשתמש בבוט מכמה חשבונות?**
ת: כרגע הבוט מוגבל ל-`CHAT_ID` אחד. אפשר לשנות זאת בקוד.

**ש: איך לשנות את נושא המייל שהבוט מחפש?**
ת: ערוך את [gmail_handler.py](gmail_handler.py#L80) ושנה את `subject:"..."`.

**ש: הבוט יכול לעבוד עם Gmail אחר?**
ת: כן! פשוט צור Refresh Token חדש עם חשבון Gmail אחר.
