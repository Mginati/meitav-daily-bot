"""
Meitav Daily Report Bot
=======================
בוט טלגרם לניתוח דוחות יומיים ממיטב

שימוש:
- שלח "דוח" לקבלת הדוח האחרון
- הבוט יבקש קוד OTP מה-SMS
- לאחר הזנת הקוד, תקבל סיכום מפורט
"""

import os
import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
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

# Conversation states
WAITING_FOR_OTP = 1

# Global state
current_download_url = None
downloader = None


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
        "*דבג* - הצגת תוכן המייל האחרון (debug)\n"
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

        msg += "\n💡 כדי לראות את תוכן המייל האחרון, שלח: *דבג*"

        await update.message.reply_text(msg, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in test_gmail: {e}")
        await update.message.reply_text(f"❌ שגיאה: {str(e)}")


async def debug_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת תוכן המייל האחרון לצורך דיבאג"""
    chat_id = str(update.effective_chat.id)

    # בדיקת הרשאה
    if chat_id != CHAT_ID:
        await update.message.reply_text("⛔ אין לך הרשאה להשתמש בבוט זה")
        return

    await update.message.reply_text("🔍 מחפש את המייל האחרון...")

    try:
        gmail = GmailHandler()

        # חיפוש המייל האחרון
        query = 'from:meitavdashnoreply@meitav.co.il'
        results = gmail.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            await update.message.reply_text("❌ לא נמצאו מיילים")
            return

        # קבלת המייל
        msg_data = gmail.service.users().messages().get(
            userId='me',
            id=messages[0]['id'],
            format='full'
        ).execute()

        headers = msg_data['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'ללא נושא')

        # חילוץ תוכן
        body_text = gmail._get_email_body(msg_data, 'text/plain')
        body_html = gmail._get_email_body(msg_data, 'text/html')

        # שליחת המידע
        debug_msg = f"📧 *נושא:* {subject}\n\n"
        debug_msg += f"📝 *תוכן טקסט:*\n```\n{body_text[:500] if body_text else 'ריק'}\n```\n\n"
        debug_msg += f"🌐 *תוכן HTML (תחילת):*\n```\n{body_html[:500] if body_html else 'ריק'}\n```"

        await update.message.reply_text(debug_msg, parse_mode='Markdown')

        # חיפוש URLs
        import re
        all_urls = re.findall(r'https?://[^\s<>"]+', body_text + body_html)
        if all_urls:
            urls_msg = f"\n\n🔗 *נמצאו {len(all_urls)} קישורים:*\n"
            for i, url in enumerate(all_urls[:5], 1):
                urls_msg += f"{i}. {url[:50]}...\n"
            await update.message.reply_text(urls_msg)
        else:
            await update.message.reply_text("⚠️ לא נמצאו קישורים במייל!")

    except Exception as e:
        logger.error(f"Error in debug_email: {e}")
        await update.message.reply_text(f"❌ שגיאה: {str(e)}")


async def request_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """התחלת תהליך הדוח"""
    global current_download_url, downloader
    
    chat_id = str(update.effective_chat.id)
    
    # בדיקת הרשאה
    if chat_id != CHAT_ID:
        await update.message.reply_text("⛔ אין לך הרשאה להשתמש בבוט זה")
        return ConversationHandler.END
    
    await update.message.reply_text("🔍 מחפש דוח חדש ממיטב...")
    
    try:
        # חיפוש המייל האחרון
        gmail = GmailHandler()
        email_data = gmail.get_latest_meitav_email()
        
        if not email_data:
            await update.message.reply_text(
                "❌ *לא נמצא דוח חדש ממיטב*\n\n"
                "נסה את הפעולות הבאות:\n"
                "1️⃣ שלח *בדיקה* לראות אילו מיילים קיימים\n"
                "2️⃣ וודא שיש מיילים מהיום מ-meitavdashnoreply@meitav.co.il\n"
                "3️⃣ בדוק שהבוט מחובר ל-Gmail הנכון",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        current_download_url = email_data['download_url']
        report_date = email_data['date']
        
        await update.message.reply_text(
            f"📧 נמצא דוח מתאריך: *{report_date}*\n\n"
            "🔐 נכנס לאתר מיטב...",
            parse_mode='Markdown'
        )
        
        # התחלת הורדה
        downloader = MeitavDownloader()
        await downloader.start()
        otp_sent = await downloader.navigate_and_request_otp(current_download_url, MEITAV_ID)
        
        if otp_sent:
            await update.message.reply_text(
                "📱 *קוד OTP נשלח ל-SMS!*\n\n"
                "שלח לי את 4 הספרות:",
                parse_mode='Markdown'
            )
            return WAITING_FOR_OTP
        else:
            await update.message.reply_text("❌ שגיאה בכניסה לאתר מיטב")
            await downloader.close()
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error in request_report: {e}")
        await update.message.reply_text(f"❌ שגיאה: {str(e)}")
        return ConversationHandler.END


async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """קבלת קוד OTP והמשך התהליך"""
    global downloader
    
    otp_code = update.message.text.strip()
    
    # בדיקה שזה 4 ספרות
    if not otp_code.isdigit() or len(otp_code) != 4:
        await update.message.reply_text("⚠️ נא להזין 4 ספרות בלבד")
        return WAITING_FOR_OTP
    
    await update.message.reply_text("⏳ מוריד את הקובץ...")
    
    try:
        # הורדת הקובץ
        file_path = await downloader.submit_otp_and_download(otp_code)
        await downloader.close()
        
        if not file_path:
            await update.message.reply_text("❌ שגיאה בהורדת הקובץ")
            return ConversationHandler.END
        
        await update.message.reply_text("📊 מנתח את הדוח...")
        
        # ניתוח הקובץ
        analyzer = ExcelAnalyzer(file_path)
        report = analyzer.analyze()
        
        # שליחת הדוח
        await update.message.reply_text(report, parse_mode='Markdown')
        
        # ניקוי
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in receive_otp: {e}")
        await update.message.reply_text(f"❌ שגיאה: {str(e)}")
        if downloader:
            await downloader.close()
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ביטול התהליך"""
    global downloader
    
    if downloader:
        await downloader.close()
    
    await update.message.reply_text("❌ התהליך בוטל")
    return ConversationHandler.END


def main():
    """הפעלת הבוט"""
    # יצירת האפליקציה
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversation handler לתהליך הדוח
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^(דוח|דו"ח|report)$'), request_report)
        ],
        states={
            WAITING_FOR_OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            MessageHandler(filters.Regex(r'^(ביטול|cancel)$'), cancel)
        ],
    )
    
    # הוספת handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("test_gmail", test_gmail))
    application.add_handler(CommandHandler("debug", debug_email))
    application.add_handler(MessageHandler(filters.Regex(r'^(עזרה|help)$'), help_command))
    application.add_handler(MessageHandler(filters.Regex(r'^(סטטוס|status)$'), status))
    application.add_handler(MessageHandler(filters.Regex(r'^(בדיקה|test)$'), test_gmail))
    application.add_handler(MessageHandler(filters.Regex(r'^(דבג|debug)$'), debug_email))
    application.add_handler(conv_handler)
    
    # הפעלה
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
