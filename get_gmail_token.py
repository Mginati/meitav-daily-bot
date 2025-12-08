"""
Gmail Token Helper
==================
סקריפט לקבלת Refresh Token מ-Gmail API
הרץ את זה פעם אחת מקומית כדי לקבל את ה-Token
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_token():
    """קבלת token חדש"""
    
    print("=" * 50)
    print("Gmail Token Helper")
    print("=" * 50)
    print()
    
    # בדיקה אם יש קובץ credentials
    if not os.path.exists('credentials.json'):
        print("❌ לא נמצא קובץ credentials.json")
        print()
        print("📋 הוראות:")
        print("1. לך ל-https://console.cloud.google.com")
        print("2. צור פרויקט חדש (או בחר קיים)")
        print("3. הפעל את Gmail API")
        print("4. לך ל-Credentials → Create Credentials → OAuth 2.0 Client ID")
        print("5. בחר 'Desktop Application'")
        print("6. הורד את ה-JSON ושמור כ-credentials.json")
        print()
        return
    
    # יצירת flow
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    
    print("🌐 פותח דפדפן להתחברות...")
    print()
    
    # קבלת credentials
    creds = flow.run_local_server(port=0)
    
    # שמירה לקובץ
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
    
    print()
    print("=" * 50)
    print("✅ הצלחה!")
    print("=" * 50)
    print()
    print("📋 הפרטים שצריך להעתיק ל-Render:")
    print()
    print(f"GMAIL_CLIENT_ID = {creds.client_id}")
    print()
    print(f"GMAIL_CLIENT_SECRET = {creds.client_secret}")
    print()
    print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
    print()
    print("=" * 50)
    print()
    print("💾 נשמר גם לקובץ: token.pickle")


if __name__ == '__main__':
    get_token()
