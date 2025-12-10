"""
Meitav Downloader
=================
הורדת קבצים מאתר מיטב באמצעות Pyppeteer
תומך בדפדפן מקומי או דפדפן מרוחק (Browserless.io)
"""

import os
import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)

# Browserless.io - שירות דפדפן מרוחק חינמי
BROWSERLESS_URL = os.getenv('BROWSERLESS_URL', 'wss://chrome.browserless.io')
BROWSERLESS_TOKEN = os.getenv('BROWSERLESS_TOKEN', '')


class MeitavDownloader:
    def __init__(self):
        self.browser = None
        self.page = None
        self.download_path = "/tmp/meitav_downloads"
        self.cookies = []

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

    async def download_report(self, url: str, id_number: str) -> str:
        """
        הורדת הדוח מאתר מיטב

        התהליך:
        1. כניסה לקישור
        2. הזנת תעודת זהות
        3. לחיצה על התחבר
        4. מציאת URL של הקובץ והורדה ישירה

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
                return None

            # מחכה לטעינת הדף הבא (עמוד המסמכים)
            logger.info("Waiting for documents page...")
            await asyncio.sleep(5)

            # שומר את הקוקיז לשימוש בהורדה
            self.cookies = await self.page.cookies()
            logger.info(f"Got {len(self.cookies)} cookies")

            # שלב 4: חיפוש URL של הקובץ להורדה
            logger.info("Looking for download URL...")

            download_url = None
            file_name = None

            # מחפש קישורים עם href שמכיל xlsx או download
            links = await self.page.querySelectorAll('a')
            for link in links:
                try:
                    href = await self.page.evaluate('(el) => el.href || ""', link)
                    text = await self.page.evaluate('(el) => el.innerText || ""', link)

                    logger.info(f"Found link: href={href[:100] if href else 'none'}, text={text[:50] if text else 'none'}")

                    if href and ('.xlsx' in href.lower() or 'download' in href.lower() or 'attachment' in href.lower()):
                        download_url = href
                        file_name = text.strip() if text else "report.xlsx"
                        logger.info(f"Found download URL: {download_url}")
                        break

                    # מחפש גם לפי טקסט
                    if '.xlsx' in text.lower():
                        download_url = href
                        file_name = text.strip()
                        logger.info(f"Found xlsx by text: {text}")
                        break
                except Exception as e:
                    logger.debug(f"Error checking link: {e}")
                    continue

            # אם לא מצאנו, ננסה לחפש בכל הדף
            if not download_url:
                page_content = await self.page.content()
                logger.info(f"Page URL: {self.page.url}")

                # מחפש URL בתוכן הדף
                import re
                urls = re.findall(r'href=["\']([^"\']*(?:download|attachment|xlsx)[^"\']*)["\']', page_content, re.IGNORECASE)
                if urls:
                    download_url = urls[0]
                    if not download_url.startswith('http'):
                        # יצירת URL מלא
                        base_url = '/'.join(self.page.url.split('/')[:3])
                        download_url = base_url + download_url if download_url.startswith('/') else base_url + '/' + download_url
                    logger.info(f"Found URL in content: {download_url}")

            if not download_url:
                # ננסה גישה אחרת - ללחוץ על הקישור ולתפוס את ה-response
                logger.info("Trying click-and-intercept approach...")

                # מחפש אלמנט עם טקסט xlsx
                elements = await self.page.querySelectorAll('a, span, div, td')
                for el in elements:
                    try:
                        text = await self.page.evaluate('(el) => el.innerText || ""', el)
                        if '.xlsx' in text:
                            # מנסה לקבל את ה-onclick או href
                            onclick = await self.page.evaluate('(el) => el.onclick ? el.onclick.toString() : ""', el)
                            href = await self.page.evaluate('(el) => el.href || el.parentElement?.href || ""', el)

                            logger.info(f"Found xlsx element: text={text}, onclick={onclick[:100] if onclick else 'none'}, href={href}")

                            if href:
                                download_url = href
                                file_name = text.strip()
                                break
                    except:
                        continue

            if not download_url:
                logger.error("Could not find download URL")
                # הדפסת תוכן הדף לדיבוג
                page_content = await self.page.content()
                logger.info(f"Page content (first 2000 chars): {page_content[:2000]}")
                return None

            # שלב 5: הורדת הקובץ ישירות דרך HTTP
            logger.info(f"Downloading file from: {download_url}")

            file_path = await self._download_file(download_url, file_name)

            if file_path:
                logger.info(f"File downloaded successfully: {file_path}")
                return file_path

            logger.warning("Failed to download file")
            return None

        except Exception as e:
            logger.error(f"Error in download_report: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def _download_file(self, url: str, file_name: str = None) -> str:
        """הורדת קובץ ישירות דרך HTTP עם הקוקיז מהדפדפן"""
        try:
            # יצירת headers עם cookies
            cookie_header = '; '.join([f"{c['name']}={c['value']}" for c in self.cookies])

            headers = {
                'Cookie': cookie_header,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        # קביעת שם הקובץ
                        if not file_name or not file_name.endswith('.xlsx'):
                            # מנסה לקבל מ-Content-Disposition
                            cd = response.headers.get('Content-Disposition', '')
                            if 'filename=' in cd:
                                import re
                                match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', cd)
                                if match:
                                    file_name = match.group(1).strip()

                            if not file_name or not file_name.endswith('.xlsx'):
                                file_name = 'meitav_report.xlsx'

                        file_path = os.path.join(self.download_path, file_name)

                        # שמירת הקובץ
                        content = await response.read()
                        with open(file_path, 'wb') as f:
                            f.write(content)

                        logger.info(f"Downloaded {len(content)} bytes to {file_path}")
                        return file_path
                    else:
                        logger.error(f"Download failed with status {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None

    async def close(self):
        """סגירת הדפדפן"""
        try:
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
