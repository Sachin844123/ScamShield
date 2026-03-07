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

# ─── API URL: env-var driven (localhost for dev, AWS for prod) ────────────────
API_URL = os.getenv("API_URL", "http://localhost:8000/api/analyze")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")  # for honeypot session API

# Conversation States
CHOOSING_ACTION = 1
WAITING_FOR_MESSAGE = 2
WAITING_HONEYPOT_LOG = 3

# In-memory history: { chat_id: [ {scan dict}, ... ] }
user_history = {}


def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("💬 Scan Message / URL", callback_data="scan_message")],
        [InlineKeyboardButton("📊 View Scan History", callback_data="view_history")],
        [InlineKeyboardButton("🕷️ Honeypot Dashboard", callback_data="open_dashboard")],
        [InlineKeyboardButton("ℹ️ About ScamShield", callback_data="about")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🛡️ *ScamShield* — _AI for Bharat_\n\n"
        "Powered by *AWS Bedrock (Claude 3.5 Sonnet)* 🤖\n\n"
        "I detect scams, phishing links, and psychological manipulation "
        "in *English, Hindi, Hinglish, Marathi, Tamil, Bengali* & more.\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📍 *How to use:* Send me any suspicious SMS, WhatsApp, or email message.\n"
        "I'll give you a full threat analysis in seconds."
    )

    if update.message:
        await update.message.reply_text(
            welcome_text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            welcome_text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )

    return CHOOSING_ACTION


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "scan_message":
        await query.message.edit_text(
            "📝 *Send me the message or URL you want to scan.*\n\n"
            "Supports: SMS, WhatsApp forwards, Email links, or raw URLs.\n"
            "Language-aware: Hindi, Hinglish, Marathi, Bengali, Tamil & English.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard()
        )
        return WAITING_FOR_MESSAGE

    elif query.data == "view_history":
        chat_id = query.message.chat_id
        history = user_history.get(chat_id, [])

        if not history:
            text = "📊 *Scan History*\n━━━━━━━━━━━━━━━━\nNo scans yet. Start scanning to see your history!"
        else:
            text = "📊 *Recent Scans*\n━━━━━━━━━━━━━━━━\n"
            for idx, item in enumerate(history, 1):
                risk_emoji = "🔴" if item['score'] > 70 else ("🟡" if item['score'] >= 40 else "🟢")
                text += f"{idx}. *{item['date']}*\n"
                text += f"   {risk_emoji} {item['type']} — `{item['score']}/100`\n"
                if item.get('model'):
                    text += f"   🤖 _{item['model']}_\n"
                if item.get('session_token'):
                    text += f"   🕷️ _Honeypot session logged_\n"
                text += "\n"

        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=get_back_keyboard())
        return CHOOSING_ACTION

    elif query.data == "open_dashboard":
        dashboard_url = BASE_URL.rstrip('/') + '/dashboard'
        await query.message.edit_text(
            f"🕷️ *Honeypot Dashboard*\n\nView all scammer engagement sessions at:\n"
            f"`{dashboard_url}`\n\n"
            "The dashboard shows all honeypot sessions created from high-risk scans via this bot and the web app.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
        return CHOOSING_ACTION

    elif query.data == "about":
        about_text = (
            "🛡️ *ScamShield — Technical Details*\n\n"
            "🤖 *AI Engine:* AWS Bedrock Claude 3.5 Sonnet\n"
            "🔄 *Fallback:* Groq Llama 3.3 70B\n"
            "🌍 *Language Detection:* Amazon Comprehend\n"
            "🔗 *URL Scanning:* urlscan.io integration\n"
            "📊 *Scoring:* Hybrid AI + Rule-based engine\n"
            "🏥 *Database:* Amazon RDS PostgreSQL\n"
            "☁️ *Hosted:* AWS Elastic Beanstalk\n\n"
            "Built for *AWS Hackathon 2026* 🏆"
        )
        await query.message.edit_text(about_text, parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=get_back_keyboard())
        return CHOOSING_ACTION

    elif query.data == "main_menu":
        return await start(update, context)

    return CHOOSING_ACTION


async def handle_scan_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.message.chat_id

    # 1. Processing feedback
    processing_msg = await update.message.reply_text(
        "🔍 *Scanning...*\n"
        "Running AI threat analysis via AWS Bedrock...",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        # 2. Call FastAPI Backend (local or AWS depending on API_URL env var)
        response = requests.post(
            API_URL,
            json={"message": user_message},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()

        score = result.get("risk_score", 0)
        model_used = result.get("model_used", "AI Engine")
        confidence = result.get("confidence", "")
        urlscan = result.get("urlscan_details", {})
        has_url = bool(urlscan and urlscan.get("scanned_url"))

        # Risk Mapping
        if score > 70:
            risk_emoji = "🔴⚠️"
            risk_label = "HIGH RISK"
        elif score >= 40:
            risk_emoji = "🟡"
            risk_label = "Medium Risk"
        else:
            risk_emoji = "🟢"
            risk_label = "Low Risk"

        # 3. Format Response
        reply = "━━━━━━━━━━━━━━━━\n"
        reply += "🛡️ *ScamShield Scan Report*\n\n"

        if has_url:
            reply += f"🔗 *URL:* `{urlscan.get('scanned_url', 'N/A')}`\n"
            if urlscan.get("virustotal"):
                vt = urlscan["virustotal"]
                vt_status = "🔴 MALICIOUS" if vt.get("malicious") else "🟢 Clean"
                reply += f"🛡️ *VirusTotal:* {vt_status} ({vt.get('malicious_count', 0)} flags)\n"
            
            reply += f"🔍 *urlscan.io:* {'🔴 MALICIOUS' if urlscan.get('score', 0) > 0 else '🟢 Safe'}\n"
            
            if urlscan.get("domain") and urlscan.get("domain") != "Unknown":
                reply += f"🌐 *Domain:* `{urlscan.get('domain')}`\n"
            if urlscan.get("ip") and urlscan.get("ip") != "Unknown":
                reply += f"🌍 *IP:* `{urlscan.get('ip')}`\n"
            if urlscan.get("ssl") and urlscan.get("ssl") != "Unknown":
                reply += f"🔒 *SSL:* {urlscan.get('ssl')}\n"
        else:
            reply += "📝 *Type:* Text/Message Analysis\n"

        reply += f"\n{risk_emoji} *Risk Level:* {risk_label} `({score}/100)`\n"
        if confidence:
            reply += f"📊 *AI Confidence:* {confidence}\n"
        reply += "━━━━━━━━━━━━━━━━\n\n"

        reply += f"🌐 *Language:* {result.get('language', 'N/A')}\n"
        if result.get("comprehend_language"):
            reply += f"🔬 *Comprehend Check:* {result.get('comprehend_language')}\n"
        reply += f"🏷️ *Scam Type:* {result.get('scam_type', 'N/A')}\n"
        reply += f"🧠 *Psychological Trick:* {result.get('psychological_trick', 'N/A')}\n\n"

        reply += f"📖 *Explanation:*\n{result.get('explanation', 'N/A')}\n\n"
        reply += f"🛑 *Recommendation:*\n{result.get('recommended_action', 'N/A')}"

        if score > 70:
            ai_honeypot = result.get(
                'honeypot_reply',
                'Could you please clarify this request via official mail to my registered address?'
            )
            reply += "\n\n🪤 *Safe Honeypot Reply (copy & send to scammer):*\n"
            reply += f"`{ai_honeypot}`"

        reply += f"\n\n🤖 _{model_used}_"

        if has_url and urlscan.get("screenshot_url"):
            reply += "\n📸 *Website screenshot below ↓*"

        # 4. Save to history
        if chat_id not in user_history:
            user_history[chat_id] = []

        session_token = result.get("honeypot_session_token")
        user_history[chat_id].insert(0, {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "type": "URL Analysis" if has_url else "Message Analysis",
            "risk": risk_label,
            "score": score,
            "model": model_used,
            "session_token": session_token,
        })
        user_history[chat_id] = user_history[chat_id][:10]

        # Build keyboards — add honeypot & dashboard buttons on high-risk
        if score > 70 and session_token:
            context.user_data['honeypot_token'] = session_token
            result_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🕷️ Log My Reply to Scammer", callback_data=f"honeypot_log:{session_token}")],
                [InlineKeyboardButton("📊 View Dashboard", callback_data="open_dashboard")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")],
            ])
        else:
            result_keyboard = get_back_keyboard()

        # 5. Output — with or without screenshot
        if has_url and urlscan.get("screenshot_url"):
            try:
                await update.message.reply_photo(
                    photo=urlscan["screenshot_url"],
                    caption=reply[:1024],  # Telegram caption limit
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=result_keyboard
                )
                # Send full text separately if long
                if len(reply) > 1024:
                    await update.message.reply_text(
                        reply[1024:], parse_mode=ParseMode.MARKDOWN,
                        reply_markup=result_keyboard
                    )
                await processing_msg.delete()
                return CHOOSING_ACTION
            except Exception as e:
                print(f"[Bot] Failed to send photo: {e}")

        # Fallback to text only
        await processing_msg.edit_text(
            reply, parse_mode=ParseMode.MARKDOWN,
            reply_markup=result_keyboard
        )

    except requests.Timeout:
        await processing_msg.edit_text(
            "⏱️ *Analysis timed out.*\n\nThe URL scan takes up to 15s. Please try again.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard()
        )
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ *Error:*\n`{str(e)}`\n\nEnsure the backend is running.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard()
        )

    return CHOOSING_ACTION


async def handle_honeypot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when user taps 'Log My Reply to Scammer'"""
    query = update.callback_query
    await query.answer()
    token = query.data.split(':', 1)[1]
    context.user_data['honeypot_token'] = token
    await query.message.edit_text(
        "🕷️ *Honeypot Reply Logger*\n\n"
        "Type the message you *sent to the scammer* as a reply.\n"
        "It will be logged in the honeypot session dashboard.\n\n"
        "You can also type the scammer's response — just label it `[SCAMMER]` at the start.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_keyboard()
    )
    return WAITING_HONEYPOT_LOG


async def handle_honeypot_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the text message and post it to the honeypot session API."""
    token = context.user_data.get('honeypot_token')
    if not token:
        await update.message.reply_text(
            "❌ No active honeypot session. Please scan a message first.",
            reply_markup=get_back_keyboard()
        )
        return CHOOSING_ACTION

    text = update.message.text.strip()
    sender = 'user'
    content = text
    if text.upper().startswith('[SCAMMER]'):
        sender = 'scammer'
        content = text[9:].strip()

    try:
        api_base = BASE_URL.rstrip('/')
        resp = requests.post(
            f"{api_base}/api/honeypot/session/{token}/message",
            json={'sender': sender, 'content': content},
            timeout=10
        )
        resp.raise_for_status()
        await update.message.reply_text(
            f"✅ *Message logged* as *{'you (victim reply)' if sender == 'user' else 'scammer'}*\n\n"
            f"`{content[:150]}{'...' if len(content) > 150 else ''}`\n\n"
            "Send another, or go back to menu.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🕷️ Log Another", callback_data=f"honeypot_log:{token}")],
                [InlineKeyboardButton("📊 Dashboard", callback_data="open_dashboard")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")],
            ])
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to log message: `{str(e)}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard()
        )

    return WAITING_HONEYPOT_LOG


def main():
    if not TOKEN or TOKEN == "your_telegram_bot_token_here":
        print("❌ TELEGRAM_BOT_TOKEN not found. Set it in .env")
        return

    print(f"🤖 ScamShield Bot starting... API target: {API_URL}")

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(handle_honeypot_callback, pattern=r'^honeypot_log:'),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_FOR_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_scan_request),
                CallbackQueryHandler(button_handler)
            ],
            WAITING_HONEYPOT_LOG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_honeypot_log),
                CallbackQueryHandler(handle_honeypot_callback, pattern=r'^honeypot_log:'),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)

    print("✅ ScamShield Telegram Bot is LIVE (AWS Bedrock + Groq Fallback)")
    app.run_polling()


if __name__ == "__main__":
    main()
