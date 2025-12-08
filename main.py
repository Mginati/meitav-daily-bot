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
        "*עזרה* - הצגת הודעה זו",
        parse_mode='Markdown'
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """בדיקת סטטוס"""
    await update.message.reply_text(
        "✅ *סטטוס מערכת:*\n\n"
        "🤖 בוט: פעיל\n"
        "📧 Gmail: מחובר\n"
        "🌐 Meitav: מוכן",
        parse_mode='Markdown'
    )


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
        email_data = await gmail.get_latest_meitav_email()
        
        if not email_data:
            await update.message.reply_text("❌ לא נמצא דוח חדש ממיטב")
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
    application.add_handler(MessageHandler(filters.Regex(r'^(עזרה|help)$'), help_command))
    application.add_handler(MessageHandler(filters.Regex(r'^(סטטוס|status)$'), status))
    application.add_handler(conv_handler)
    
    # הפעלה
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
