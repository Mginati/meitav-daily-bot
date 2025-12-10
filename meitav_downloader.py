"""
Meitav Downloader
=================
הורדת קבצים מאתר מיטב באמצעות Pyppeteer
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
        self.browser = None
        self.page = None
        self.download_path = "/tmp/meitav_downloads"

    async def start(self):
        """הפעלת הדפדפן - מקומי או מרוחק"""
        import pyppeteer

        os.makedirs(self.download_path, exist_ok=True)

        # אם יש טוקן של Browserless - השתמש בדפדפן מרוחק
        if BROWSERLESS_TOKEN:
            browserless_ws = f"{BROWSERLESS_URL}?token={BROWSERLESS_TOKEN}"
            logger.info(f"Connecting to remote browser (Browserless.io)...")
            logger.info(f"WebSocket URL: {BROWSERLESS_URL}?token=***")
            try:
                self.browser = await pyppeteer.connect(browserWSEndpoint=browserless_ws)
                logger.info("Connected to Browserless.io successfully!")
            except Exception as e:
                logger.error(f"Failed to connect to Browserless: {e}")
                raise Exception(f"Browserless connection failed: {e}")
        else:
            # דפדפן מקומי
            logger.info("No BROWSERLESS_TOKEN found, starting local browser...")
            self.browser = await pyppeteer.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )

        self.page = await self.browser.newPage()

        # הגדרת timeout
        self.page.setDefaultNavigationTimeout(60000)

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
            await self.page.goto(url, {'waitUntil': 'networkidle0'})

            # מחכה לטעינת הדף
            await asyncio.sleep(2)

            # מחפש את שדה הסיסמה (תעודת זהות)
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
                    await self.page.waitForSelector(selector, {'timeout': 5000})
                    password_field = await self.page.querySelector(selector)
                    if password_field:
                        logger.info(f"Found password field with selector: {selector}")
                        break
                except:
                    continue

            if not password_field:
                logger.error("Could not find password field")
                await self.page.screenshot({'path': '/tmp/meitav_debug.png'})
                return False

            # הזנת תעודת הזהות
            await password_field.type(id_number)
            logger.info("ID number entered")

            # לחיצה על כפתור התחברות
            submit_selectors = [
                'button',
                'input[type="submit"]',
                '[type="submit"]',
                '.login-button',
                '#loginButton'
            ]

            for selector in submit_selectors:
                try:
                    await self.page.waitForSelector(selector, {'timeout': 3000})
                    buttons = await self.page.querySelectorAll(selector)
                    for button in buttons:
                        text = await self.page.evaluate('(el) => el.innerText || el.value || ""', button)
                        if 'התחבר' in text or 'כניסה' in text or 'login' in text.lower():
                            await button.click()
                            logger.info(f"Clicked submit button")
                            break
                    else:
                        continue
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
            # הגדרת נתיב הורדה
            await self.page._client.send('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': self.download_path
            })

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
                    await self.page.waitForSelector(selector, {'timeout': 5000})
                    otp_field = await self.page.querySelector(selector)
                    if otp_field:
                        logger.info(f"Found OTP field with selector: {selector}")
                        break
                except:
                    continue

            if not otp_field:
                otp_field = await self.page.querySelector('input[type="text"]')

            if otp_field:
                await otp_field.type(otp_code)
                logger.info("OTP entered")

            # לחיצה על כפתור אישור/התחברות
            submit_selectors = [
                'button',
                'input[type="submit"]',
                '[type="submit"]'
            ]

            for selector in submit_selectors:
                try:
                    await self.page.waitForSelector(selector, {'timeout': 3000})
                    buttons = await self.page.querySelectorAll(selector)
                    for button in buttons:
                        text = await self.page.evaluate('(el) => el.innerText || el.value || ""', button)
                        if 'אישור' in text or 'התחבר' in text or 'כניסה' in text:
                            await button.click()
                            logger.info(f"Clicked button")
                            break
                    else:
                        continue
                    break
                except:
                    continue

            # מחכה להורדה
            await asyncio.sleep(10)

            # חיפוש הקובץ שהורד
            files = os.listdir(self.download_path)
            xlsx_files = [f for f in files if f.endswith('.xlsx')]
            if xlsx_files:
                file_path = os.path.join(self.download_path, xlsx_files[-1])
                logger.info(f"File downloaded: {file_path}")
                return file_path

            logger.warning("No xlsx file found after download")
            return None

        except Exception as e:
            logger.error(f"Error in submit_otp_and_download: {e}")

            # אולי הקובץ כבר הורד?
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
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
