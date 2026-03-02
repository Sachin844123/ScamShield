import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://localhost:8000/api/analyze"

# Conversation States
CHOOSING_ACTION = 1
WAITING_FOR_MESSAGE = 2

# In-memory history: { chat_id: [ {"date": "...", "type": "...", "risk": "...", "score": 85}, ... ] }
user_history = {}

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("💬 Scan Message / URL", callback_data="scan_message")],
        [InlineKeyboardButton("📊 View Scan History", callback_data="view_history")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🛡️ *ScamShield Bot*\n\n"
        "AI-powered phishing & malicious link detection system.\n"
        "Scan links and suspicious messages instantly."
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu_keyboard())

    return CHOOSING_ACTION

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "scan_message":
        await query.message.edit_text(
            "📝 *Send me the message or URL you want to scan.*\n\n"
            "I will analyze it for phishing links, obfuscated text, and psychological manipulation.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard()
        )
        return WAITING_FOR_MESSAGE
        
    elif query.data == "view_history":
        chat_id = query.message.chat_id
        history = user_history.get(chat_id, [])
        
        if not history:
            text = "📊 *Scan History*\n━━━━━━━━━━━━━━━━\nNo scans found yet. Try scanning something!"
        else:
            text = "📊 *Recent Scans*\n━━━━━━━━━━━━━━━━\n"
            for idx, item in enumerate(history, 1):
                text += f"{idx}. *{item['date']}*\n"
                text += f"   Type: {item['type']}\n"
                text += f"   Risk Level: {item['risk']} ({item['score']}/100)\n\n"
                
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_keyboard())
        return CHOOSING_ACTION

    elif query.data == "main_menu":
        return await start(update, context)

    return CHOOSING_ACTION

async def handle_scan_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    # 1. Immediate loading feedback
    processing_msg = await update.message.reply_text(
        "🔍 *Scanning...*\n"
        "Please wait while we analyze the message and external threats.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # 2. Call local FastAPI Backend
        response = requests.post(API_URL, json={"message": user_message})
        response.raise_for_status()
        result = response.json()
        
        score = result.get("risk_score", 0)
        urlscan = result.get("urlscan_details", {})
        has_url = bool(urlscan and urlscan.get("scanned_url"))
        
        # Risk Mapping
        if score > 70:
            emoji = "🔴 High Risk"
        elif score >= 40:
            emoji = "🟡 Medium Risk"
        else:
            emoji = "🟢 Low Risk"
            
        # 3. Format Response
        reply = "━━━━━━━━━━━━━━━━\n"
        reply += "🛡️ *Scan Report*\n\n"
        
        if has_url:
            reply += f"🔗 *URL:* `{urlscan.get('scanned_url', 'N/A')}`\n"
            if urlscan.get("ip") and urlscan.get("ip") != "Unknown":
                reply += f"🌍 *IP Address:* `{urlscan.get('ip')}`\n"
            if urlscan.get("domain") and urlscan.get("domain") != "Unknown":
                reply += f"🌐 *Domain:* `{urlscan.get('domain')}`\n"
            if urlscan.get("ssl") and urlscan.get("ssl") != "Unknown":
                reply += f"🔒 *SSL:* {urlscan.get('ssl')}\n"
        else:
            reply += "📝 *Type:* Text Analysis\n"
            
        reply += f"⚠️ *Risk Level:* {emoji} ({score}/100)\n"
        reply += "━━━━━━━━━━━━━━━━\n\n"
        
        reply += f"� *Language Detected:* {result.get('language', 'N/A')}\n"
        reply += f"�🏷️ *Scam Type:* {result.get('scam_type', 'N/A')}\n"
        reply += f"🧠 *Psychological Trick:* {result.get('psychological_trick', 'N/A')}\n\n"
        
        reply += f"📖 *Explanation:*\n{result.get('explanation', 'N/A')}\n\n"
        reply += f"🛑 *Recommendation:*\n{result.get('recommended_action', 'N/A')}"
        
        if score > 70:
            ai_honeypot = result.get('honeypot_reply', 'Could you please clarify this request via official mail to my registered address?')
            reply += "\n\n🪤 *Safe Honeypot Reply Suggestion:*\n"
            reply += f"`{ai_honeypot}`"
            
        if has_url and urlscan.get("screenshot_url"):
            reply += "\n\n📸 *Website Screenshot Below*"
            
        # 4. Save to history
        if chat_id not in user_history:
            user_history[chat_id] = []
            
        user_history[chat_id].insert(0, {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "type": "URL Analysis" if has_url else "Message Analysis",
            "risk": emoji,
            "score": score
        })
        # Keep only last 5
        user_history[chat_id] = user_history[chat_id][:5]

        # 5. Output Deliverables
        if has_url and urlscan.get("screenshot_url"):
            try:
                await update.message.reply_photo(
                    photo=urlscan["screenshot_url"], 
                    caption=reply,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_back_keyboard()
                )
                await processing_msg.delete()  # Clean up loading message
                return CHOOSING_ACTION
            except Exception as e:
                print(f"Failed to send photo: {e}")
                
        # Fallback to pure text if no photo or photo fails
        await processing_msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_keyboard())
        
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ *Error analyzing message:*\n`{str(e)}`\n\nEnsure backend is running.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard()
        )
        
    return CHOOSING_ACTION


def main():
    if not TOKEN or TOKEN == "your_telegram_bot_token_here":
        print("TELEGRAM_BOT_TOKEN not found in environment. Please supply one in .env.")
        return
        
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(button_handler)
            ],
            WAITING_FOR_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_scan_request),
                CallbackQueryHandler(button_handler)
            ],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    app.add_handler(conv_handler)
    
    print("🤖 Professional Telegram Bot UX with urlscan.io is LIVE...")
    app.run_polling()

if __name__ == "__main__":
    main()
