"""
Meitav Downloader
=================
הורדת קבצים מאתר מיטב באמצעות Playwright
תומך בדפדפן מקומי או דפדפן מרוחק (Browserless.io)
"""

import os
import asyncio
import logging

logger = logging.getLogger(__name__)

# Browserless.io - שירות דפדפן מרוחק חינמי
BROWSERLESS_URL = os.getenv('BROWSERLESS_URL', 'wss://chrome.browserless.io')
BROWSERLESS_TOKEN = os.getenv('BROWSERLESS_TOKEN', '')


class MeitavDownloader:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.download_path = "/tmp/meitav_downloads"

    async def start(self):
        """הפעלת הדפדפן - מקומי או מרוחק"""
        os.makedirs(self.download_path, exist_ok=True)

        # Import playwright dynamically
        from playwright.async_api import async_playwright

        logger.info("Initializing Playwright...")
        pw = async_playwright()
        self.playwright = await pw.start()

        if self.playwright is None:
            raise Exception("Failed to initialize Playwright - returned None")

        logger.info("Playwright initialized successfully")

        # אם יש טוקן של Browserless - השתמש בדפדפן מרוחק
        if BROWSERLESS_TOKEN:
            browserless_ws = f"{BROWSERLESS_URL}?token={BROWSERLESS_TOKEN}"
            logger.info(f"Connecting to remote browser (Browserless.io)...")
            logger.info(f"WebSocket URL: {BROWSERLESS_URL}?token=***")
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(browserless_ws)
                logger.info("Connected to Browserless.io successfully!")
            except Exception as e:
                logger.error(f"Failed to connect to Browserless: {e}")
                raise Exception(f"Browserless connection failed: {e}")
        else:
            # דפדפן מקומי
            logger.info("No BROWSERLESS_TOKEN found, starting local browser...")
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )

        self.page = await self.browser.new_page()

        # הגדרת timeout
        await self.page.context.set_default_timeout(60000)

        logger.info("Browser started")
    
    async def navigate_and_request_otp(self, url: str, id_number: str) -> bool:
        """
        כניסה לאתר מיטב והזנת תעודת זהות
        
        Args:
            url: קישור ההורדה מהמייל
            id_number: תעודת זהות
            
        Returns:
            True אם ה-OTP נשלח בהצלחה
        """
        try:
            logger.info(f"Navigating to: {url}")
            await self.page.goto(url, wait_until='networkidle')
            
            # מחכה לטעינת הדף
            await asyncio.sleep(2)
            
            # מחפש את שדה הסיסמה (תעודת זהות)
            # האתר משתמש בשדה truePass או שדה input רגיל
            password_selectors = [
                'input[name="truePass"]',
                'input[placeholder*="סיסמה"]',
                'input[type="password"]',
                'input[type="text"]',
                '#truePass',
                '.truePass'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    field = await self.page.wait_for_selector(selector, timeout=5000)
                    if field:
                        password_field = field
                        logger.info(f"Found password field with selector: {selector}")
                        break
                except:
                    continue
            
            if not password_field:
                logger.error("Could not find password field")
                # נסה לצלם את הדף לדיבוג
                await self.page.screenshot(path="/tmp/meitav_debug.png")
                return False
            
            # הזנת תעודת הזהות
            await password_field.fill(id_number)
            logger.info("ID number entered")
            
            # לחיצה על כפתור התחברות
            submit_selectors = [
                'button:has-text("התחבר")',
                'input[type="submit"]',
                'button[type="submit"]',
                '.login-button',
                '#loginButton'
            ]
            
            for selector in submit_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info(f"Clicked submit button: {selector}")
                        break
                except:
                    continue
            
            # מחכה לשליחת ה-OTP
            await asyncio.sleep(3)
            
            # בדיקה שהדף עבר למצב המתנה ל-OTP
            page_content = await self.page.content()
            if 'OTP' in page_content or 'קוד' in page_content or 'SMS' in page_content or 'סיסמה חד' in page_content:
                logger.info("OTP requested successfully")
                return True
            
            logger.info("Assuming OTP was sent")
            return True
            
        except Exception as e:
            logger.error(f"Error in navigate_and_request_otp: {e}")
            return False
    
    async def submit_otp_and_download(self, otp_code: str) -> str:
        """
        הזנת קוד OTP והורדת הקובץ
        
        Args:
            otp_code: קוד 4 ספרות מה-SMS
            
        Returns:
            נתיב הקובץ שהורד או None
        """
        try:
            # מחפש את שדה ה-OTP
            otp_selectors = [
                'input[name="otp"]',
                'input[placeholder*="קוד"]',
                'input[placeholder*="OTP"]',
                'input[type="text"]:not([name="truePass"])',
                'input[maxlength="4"]',
                'input[maxlength="6"]'
            ]
            
            otp_field = None
            for selector in otp_selectors:
                try:
                    field = await self.page.wait_for_selector(selector, timeout=5000)
                    if field:
                        otp_field = field
                        logger.info(f"Found OTP field with selector: {selector}")
                        break
                except:
                    continue
            
            if not otp_field:
                # אולי השדה הקיים הוא שדה ה-OTP
                otp_field = await self.page.query_selector('input[type="text"]')
            
            if otp_field:
                await otp_field.fill(otp_code)
                logger.info("OTP entered")
            
            # הגדרת ציפייה להורדה
            async with self.page.expect_download(timeout=60000) as download_info:
                # לחיצה על כפתור אישור/התחברות
                submit_selectors = [
                    'button:has-text("אישור")',
                    'button:has-text("התחבר")',
                    'button:has-text("כניסה")',
                    'input[type="submit"]',
                    'button[type="submit"]'
                ]
                
                for selector in submit_selectors:
                    try:
                        button = await self.page.wait_for_selector(selector, timeout=3000)
                        if button:
                            await button.click()
                            logger.info(f"Clicked button: {selector}")
                            break
                    except:
                        continue
            
            download = await download_info.value
            
            # שמירת הקובץ
            file_name = download.suggested_filename or "meitav_report.xlsx"
            file_path = os.path.join(self.download_path, file_name)
            await download.save_as(file_path)
            
            logger.info(f"File downloaded: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error in submit_otp_and_download: {e}")
            
            # אולי הקובץ כבר הורד אוטומטית?
            files = os.listdir(self.download_path)
            xlsx_files = [f for f in files if f.endswith('.xlsx')]
            if xlsx_files:
                return os.path.join(self.download_path, xlsx_files[-1])
            
            return None
    
    async def close(self):
        """סגירת הדפדפן"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
