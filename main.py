"""
Meitav Daily Report Bot
=======================
בוט טלגרם לניתוח דוחות יומיים ממיטב

שימוש:
- שלח "דוח" לקבלת הדוח האחרון
- הבוט יוריד ויניח את הדוח באופן אוטומטי
"""

import os
import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from meitav_downloader import MeitavDownloader
from excel_analyzer import ExcelAnalyzer
from gmail_handler import GmailHandler

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8556362815:AAF-qSPbXrWDAcSErRMLpYMy5vMsYDz2umU')
CHAT_ID = os.getenv('CHAT_ID', '424508467')
MEITAV_ID = os.getenv('MEITAV_ID', '066624669')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הודעת פתיחה"""
    await update.message.reply_text(
        "🏦 *בוט דוח יומי מיטב*\n\n"
        "שלח *דוח* לקבלת הדוח היומי האחרון\n"
        "שלח *עזרה* לרשימת פקודות",
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """עזרה"""
    await update.message.reply_text(
        "📋 *פקודות זמינות:*\n\n"
        "*דוח* - הורדה וניתוח הדוח האחרון\n"
        "*סטטוס* - בדיקת סטטוס המערכת\n"
        "*בדיקה* - בדיקת חיבור Gmail ומיילים\n"
        "*עזרה* - הצגת הודעה זו",
        parse_mode='Markdown'
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """בדיקת סטטוס"""
    await update.message.reply_text("🔄 בודק מערכות...")

    status_msg = "✅ *סטטוס מערכת:*\n\n🤖 בוט: פעיל\n"

    # בדיקת Gmail
    try:
        gmail = GmailHandler()
        status_msg += "📧 Gmail: ✅ מחובר\n"
    except Exception as e:
        status_msg += f"📧 Gmail: ❌ שגיאה - {str(e)}\n"
        logger.error(f"Gmail connection error: {e}")

    status_msg += "🌐 Meitav: מוכן"

    await update.message.reply_text(status_msg, parse_mode='Markdown')


async def test_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """בדיקת חיבור Gmail ומיילים"""
    chat_id = str(update.effective_chat.id)

    # בדיקת הרשאה
    if chat_id != CHAT_ID:
        await update.message.reply_text("⛔ אין לך הרשאה להשתמש בבוט זה")
        return

    await update.message.reply_text("🔍 בודק חיבור ל-Gmail...")

    try:
        gmail = GmailHandler()

        # חיפוש כל המיילים ממיטב
        query = 'from:meitavdashnoreply@meitav.co.il'
        results = gmail.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            await update.message.reply_text(
                "⚠️ *לא נמצאו מיילים ממיטב*\n\n"
                "ייתכן שהכתובת השולח שונתה או שאין מיילים בתיבה",
                parse_mode='Markdown'
            )
            return

        # הצגת פרטי המיילים האחרונים
        msg = f"📧 *נמצאו {len(messages)} מיילים ממיטב:*\n\n"

        for i, message in enumerate(messages[:5], 1):
            msg_data = gmail.service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()

            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'ללא נושא')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'ללא תאריך')

            msg += f"{i}. *{subject}*\n"
            msg += f"   📅 {date}\n\n"

        await update.message.reply_text(msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in test_gmail: {e}")
        await update.message.reply_text(f"❌ שגיאה: {str(e)}")


async def request_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הורדה וניתוח הדוח - תהליך אוטומטי מלא"""
    chat_id = str(update.effective_chat.id)

    # בדיקת הרשאה
    if chat_id != CHAT_ID:
        await update.message.reply_text("⛔ אין לך הרשאה להשתמש בבוט זה")
        return

    await update.message.reply_text("🔍 מחפש דוח חדש ממיטב...")

    try:
        # שלב 1: חיפוש המייל האחרון
        gmail = GmailHandler()
        email_data = gmail.get_latest_meitav_email()

        if not email_data:
            await update.message.reply_text(
                "❌ *לא נמצא דוח חדש ממיטב*\n\n"
                "נסה את הפעולות הבאות:\n"
                "1️⃣ שלח *בדיקה* לראות אילו מיילים קיימים\n"
                "2️⃣ וודא שיש מיילים מהיום מ-meitavdashnoreply@meitav.co.il",
                parse_mode='Markdown'
            )
            return

        download_url = email_data['download_url']
        report_date = email_data['date']

        await update.message.reply_text(
            f"📧 נמצא דוח מתאריך: *{report_date}*\n\n"
            "🔐 נכנס לאתר מיטב...",
            parse_mode='Markdown'
        )

        # שלב 2: הפעלת הדפדפן
        downloader = MeitavDownloader()
        logger.info("Created MeitavDownloader instance")

        try:
            logger.info("Starting browser...")
            await downloader.start()
            logger.info("Browser started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            await update.message.reply_text(f"❌ שגיאה באתחול הדפדפן: {str(e)}")
            return

        await update.message.reply_text("⏳ מוריד את הדוח...")

        # שלב 3: הורדת הדוח (תהליך אוטומטי - בלי OTP!)
        try:
            file_path = await downloader.download_report(download_url, MEITAV_ID)
        except Exception as e:
            logger.error(f"Error downloading report: {e}")
            await downloader.close()
            await update.message.reply_text(f"❌ שגיאה בהורדת הדוח: {str(e)}")
            return

        await downloader.close()

        if not file_path:
            await update.message.reply_text("❌ שגיאה בהורדת הקובץ - לא נמצא קובץ xlsx")
            return

        await update.message.reply_text("📊 מנתח את הדוח...")

        # שלב 4: ניתוח הקובץ
        try:
            analyzer = ExcelAnalyzer(file_path)
            report = analyzer.analyze()

            # שליחת הדוח
            await update.message.reply_text(report, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error analyzing report: {e}")
            await update.message.reply_text(f"❌ שגיאה בניתוח הדוח: {str(e)}")

        # ניקוי
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logger.error(f"Error in request_report: {e}")
        await update.message.reply_text(f"❌ שגיאה: {str(e)}")


if __name__ == '__main__':
    # פורט ל-Railway/Render
    import os
    port = int(os.environ.get('PORT', 8080))

    # הפעלת web server פשוט ברקע
    from aiohttp import web
    import asyncio

    async def health(request):
        return web.Response(text='OK')

    async def start_web_server():
        app = web.Application()
        app.router.add_get('/health', health)
        app.router.add_get('/', health)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"Health check server running on port {port}")

    # הרצת שני הדברים במקביל
    async def run_both():
        # הפעלת web server
        await start_web_server()

        # הפעלת הבוט באותו event loop
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # הוספת handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(CommandHandler("test_gmail", test_gmail))
        application.add_handler(MessageHandler(filters.Regex(r'^(עזרה|help)$'), help_command))
        application.add_handler(MessageHandler(filters.Regex(r'^(סטטוס|status)$'), status))
        application.add_handler(MessageHandler(filters.Regex(r'^(בדיקה|test)$'), test_gmail))
        application.add_handler(MessageHandler(filters.Regex(r'^(דוח|דו"ח|report)$'), request_report))

        # הפעלת הבוט
        logger.info("Starting bot...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        # שמירה על התהליך חי
        while True:
            await asyncio.sleep(3600)

    asyncio.run(run_both())
