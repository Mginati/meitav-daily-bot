"""
סקריפט לבדיקת משתני סביבה
===============================
משמש לוודא שכל המשתנים הדרושים קיימים
"""

import os

def check_env():
    """בדיקת כל משתני הסביבה הדרושים"""

    required_vars = {
        'TELEGRAM_TOKEN': 'טוקן הבוט מ-@BotFather',
        'CHAT_ID': 'מזהה הצ\'אט המורשה',
        'MEITAV_ID': 'מספר ת.ז. למערכת מיטב',
        'GMAIL_CLIENT_ID': 'Client ID מ-Google Cloud Console',
        'GMAIL_CLIENT_SECRET': 'Client Secret מ-Google Cloud Console',
        'GMAIL_REFRESH_TOKEN': 'Refresh Token מהרצת get_gmail_token.py'
    }

    print("🔍 בודק משתני סביבה...\n")

    all_exist = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # הצגה חלקית של הערך (מסיבות אבטחה)
            masked_value = value[:10] + '...' if len(value) > 10 else value
            print(f"✅ {var}: {masked_value}")
            print(f"   ({description})")
        else:
            print(f"❌ {var}: חסר!")
            print(f"   ({description})")
            all_exist = False
        print()

    if all_exist:
        print("🎉 כל משתני הסביבה קיימים!")
        return True
    else:
        print("⚠️ חסרים משתני סביבה. הבוט לא יפעל כראוי.")
        return False

if __name__ == '__main__':
    check_env()
