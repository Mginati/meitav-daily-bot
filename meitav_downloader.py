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

        # הגדרת נתיב הורדה
        await self.page._client.send('Page.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': self.download_path
        })

        logger.info("Browser started")

    async def download_report(self, url: str, id_number: str) -> str:
        """
        הורדת הדוח מאתר מיטב

        התהליך:
        1. כניסה לקישור
        2. הזנת תעודת זהות
        3. לחיצה על התחבר
        4. לחיצה על הקובץ להורדה

        Args:
            url: קישור ההורדה מהמייל
            id_number: תעודת זהות

        Returns:
            נתיב הקובץ שהורד או None
        """
        try:
            logger.info(f"Navigating to: {url}")
            await self.page.goto(url, {'waitUntil': 'networkidle0'})

            # מחכה לטעינת הדף
            await asyncio.sleep(2)

            # שלב 1: מחפש את שדה הסיסמה (truePass)
            logger.info("Looking for password field (truePass)...")

            password_field = None
            try:
                # מחפש את השדה הספציפי של מיטב
                await self.page.waitForSelector('input[name="truePass"]', {'timeout': 10000})
                password_field = await self.page.querySelector('input[name="truePass"]')
                logger.info("Found truePass field")
            except:
                # נסיון חלופי
                try:
                    password_field = await self.page.querySelector('input[type="password"]')
                    if not password_field:
                        password_field = await self.page.querySelector('input[type="text"]')
                    logger.info("Found alternative input field")
                except:
                    pass

            if not password_field:
                logger.error("Could not find password field")
                await self.page.screenshot({'path': '/tmp/meitav_debug_step1.png'})
                return None

            # שלב 2: הזנת תעודת הזהות
            await password_field.click()
            await password_field.type(id_number)
            logger.info("ID number entered")

            await asyncio.sleep(1)

            # שלב 3: לחיצה על כפתור התחבר
            logger.info("Looking for submit button...")

            clicked = False
            # מחפש כפתור עם הטקסט "התחבר"
            buttons = await self.page.querySelectorAll('button, input[type="submit"], .btn, [type="button"]')
            for button in buttons:
                try:
                    text = await self.page.evaluate('(el) => el.innerText || el.value || ""', button)
                    if 'התחבר' in text or 'כניסה' in text or 'login' in text.lower() or 'submit' in text.lower():
                        await button.click()
                        logger.info(f"Clicked button: {text}")
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                # נסיון ללחוץ על כל כפתור
                try:
                    submit_btn = await self.page.querySelector('input[type="submit"]')
                    if submit_btn:
                        await submit_btn.click()
                        clicked = True
                        logger.info("Clicked submit input")
                except:
                    pass

            if not clicked:
                logger.error("Could not find submit button")
                await self.page.screenshot({'path': '/tmp/meitav_debug_step3.png'})
                return None

            # מחכה לטעינת הדף הבא (עמוד המסמכים)
            logger.info("Waiting for documents page...")
            await asyncio.sleep(5)

            # צילום מסך לדיבוג
            await self.page.screenshot({'path': '/tmp/meitav_debug_after_login.png'})

            # שלב 4: חיפוש קישור להורדת הקובץ
            logger.info("Looking for download link...")

            # מחפש קישור לקובץ xlsx
            download_link = None

            # נסיון 1: מחפש קישור עם xlsx בטקסט או ב-href
            links = await self.page.querySelectorAll('a')
            for link in links:
                try:
                    href = await self.page.evaluate('(el) => el.href || ""', link)
                    text = await self.page.evaluate('(el) => el.innerText || ""', link)

                    if '.xlsx' in href.lower() or '.xlsx' in text.lower() or 'דוח' in text:
                        download_link = link
                        logger.info(f"Found download link: {text}")
                        break
                except:
                    continue

            # נסיון 2: מחפש כל אלמנט שניתן ללחוץ עליו עם xlsx
            if not download_link:
                elements = await self.page.querySelectorAll('[href*=".xlsx"], [onclick*="download"], .download-link')
                if elements:
                    download_link = elements[0]
                    logger.info("Found download element by selector")

            # נסיון 3: מחפש לפי טקסט שמכיל "xlsx" או "דוח"
            if not download_link:
                all_elements = await self.page.querySelectorAll('*')
                for el in all_elements:
                    try:
                        text = await self.page.evaluate('(el) => el.innerText || ""', el)
                        tag = await self.page.evaluate('(el) => el.tagName', el)
                        if '.xlsx' in text and tag in ['A', 'SPAN', 'DIV', 'TD']:
                            download_link = el
                            logger.info(f"Found element with xlsx text: {text[:50]}")
                            break
                    except:
                        continue

            if not download_link:
                logger.error("Could not find download link")
                page_content = await self.page.content()
                logger.info(f"Page content preview: {page_content[:1000]}")
                await self.page.screenshot({'path': '/tmp/meitav_debug_no_link.png'})
                return None

            # לחיצה על הקישור להורדה
            logger.info("Clicking download link...")
            await download_link.click()

            # מחכה להורדה
            logger.info("Waiting for download to complete...")
            await asyncio.sleep(10)

            # חיפוש הקובץ שהורד
            files = os.listdir(self.download_path)
            xlsx_files = [f for f in files if f.endswith('.xlsx')]

            if xlsx_files:
                # מחזיר את הקובץ האחרון
                xlsx_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.download_path, x)), reverse=True)
                file_path = os.path.join(self.download_path, xlsx_files[0])
                logger.info(f"File downloaded: {file_path}")
                return file_path

            logger.warning("No xlsx file found after download")
            return None

        except Exception as e:
            logger.error(f"Error in download_report: {e}")
            await self.page.screenshot({'path': '/tmp/meitav_debug_error.png'})
            return None

    async def close(self):
        """סגירת הדפדפן"""
        try:
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
