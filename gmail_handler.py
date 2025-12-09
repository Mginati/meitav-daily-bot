"""
Gmail Handler
=============
חיבור ל-Gmail ומציאת מיילים ממיטב
"""

import os
import re
import base64
import logging
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailHandler:
    def __init__(self):
        self.service = None
        self.creds = None
        self._authenticate()
    
    def _authenticate(self):
        """אימות מול Gmail API"""
        creds = None
        
        # בדיקה אם יש token שמור
        token_path = os.getenv('GMAIL_TOKEN_PATH', 'token.pickle')
        credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # אם אין credentials תקפים
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # עבור סביבת production, נשתמש ב-environment variables
                if os.getenv('GMAIL_REFRESH_TOKEN'):
                    creds = Credentials(
                        token=None,
                        refresh_token=os.getenv('GMAIL_REFRESH_TOKEN'),
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=os.getenv('GMAIL_CLIENT_ID'),
                        client_secret=os.getenv('GMAIL_CLIENT_SECRET')
                    )
                    creds.refresh(Request())
                elif os.path.exists(credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise Exception("No Gmail credentials found. Please set up OAuth2 credentials.")
            
            # שמירת ה-token
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.creds = creds
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail authenticated successfully")
    
    async def get_latest_meitav_email(self) -> dict:
        """
        מציאת המייל האחרון ממיטב עם דוח יומי

        Returns:
            dict עם download_url ו-date, או None אם לא נמצא
        """
        try:
            # חיפוש מיילים ממיטב
            query = 'from:meitavdashnoreply@meitav.co.il subject:"דוח יומי לסוכן"'
            logger.info(f"Searching for emails with query: {query}")

            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=5
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages matching the query")

            if not messages:
                logger.warning("No Meitav emails found with the specific query")
                # ננסה חיפוש רחב יותר
                logger.info("Trying broader search...")
                query_broad = 'from:meitavdashnoreply@meitav.co.il'
                results_broad = self.service.users().messages().list(
                    userId='me',
                    q=query_broad,
                    maxResults=5
                ).execute()
                messages = results_broad.get('messages', [])
                logger.info(f"Broader search found {len(messages)} messages")

                if not messages:
                    logger.warning("No emails from Meitav found at all")
                    return None
            
            # קבלת המייל האחרון
            latest_message = self.service.users().messages().get(
                userId='me',
                id=messages[0]['id'],
                format='full'
            ).execute()
            
            # חילוץ התאריך מהכותרת
            headers = latest_message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            logger.info(f"Email subject: {subject}")
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', subject)
            report_date = date_match.group(1) if date_match else 'לא ידוע'
            
            # חילוץ תוכן המייל
            body = self._get_email_body(latest_message)
            
            # חיפוש קישור ההורדה
            download_url = self._extract_download_url(body)

            if not download_url:
                logger.warning("No URL found in text/plain body")
                logger.debug(f"Text body preview: {body[:500] if body else 'EMPTY'}")
                # נסיון לחפש ב-HTML
                html_body = self._get_email_body(latest_message, 'text/html')
                logger.info(f"HTML body length: {len(html_body) if html_body else 0}")
                logger.debug(f"HTML body preview: {html_body[:500] if html_body else 'EMPTY'}")
                download_url = self._extract_download_url(html_body)

            if download_url:
                logger.info(f"Found download URL for date: {report_date}")
                return {
                    'download_url': download_url,
                    'date': report_date,
                    'subject': subject
                }
            else:
                logger.warning("Could not find download URL in email")
                logger.error(f"Email body (text): {body[:1000] if body else 'EMPTY'}")
                logger.error(f"Email body (html): {html_body[:1000] if html_body else 'EMPTY'}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting Meitav email: {e}")
            return None
    
    def _get_email_body(self, message: dict, mime_type: str = 'text/plain') -> str:
        """חילוץ תוכן המייל"""
        try:
            payload = message['payload']
            
            # בדיקה אם יש parts
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == mime_type:
                        data = part['body'].get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
                    # בדיקה רקורסיבית
                    if 'parts' in part:
                        for subpart in part['parts']:
                            if subpart['mimeType'] == mime_type:
                                data = subpart['body'].get('data', '')
                                if data:
                                    return base64.urlsafe_b64decode(data).decode('utf-8')
            
            # אם אין parts, התוכן ישירות ב-body
            data = payload['body'].get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
            
            return ''
            
        except Exception as e:
            logger.error(f"Error getting email body: {e}")
            return ''
    
    def _extract_download_url(self, content: str) -> str:
        """חילוץ קישור ההורדה מתוכן המייל"""
        if not content:
            return None
        
        # חיפוש קישורים לאתר safemail של מיטב
        patterns = [
            r'https://safemail\.meitav\.co\.il/Safe-T/login\.aspx[^\s\'"<>]+',
            r'https://safemail\.meitav\.co\.il[^\s\'"<>]+',
            r'href=["\']?(https://safemail\.meitav\.co\.il[^"\'\s<>]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                url = match.group(1) if match.lastindex else match.group(0)
                # ניקוי ה-URL
                url = url.rstrip('>')
                url = url.replace('&amp;', '&')
                logger.info(f"Found URL: {url}")
                return url
        
        return None
