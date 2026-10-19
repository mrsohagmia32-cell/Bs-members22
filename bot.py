import os
import requests
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= Credentials =================
BOT_TOKEN = "8904156081:AAFBdhBG-cIwEGDJtB0jsQfkJrwzzoCAutQ"
MIAH_API_KEY = "MIAHSMS_4FEEA0F154770AAF51F8ABA3"
GAS_WEBAPP_URL = "https://script.google.com/macros/s/AKfycby-djqeq_oaxlF4rltN5ivXLWC8Qo3nirpSeUZRvhbc40jyMIDjFNAqAGcWpWUz5WyK/exec"

MIAH_GETNUM_URL = "https://miahsms.com/bot/api/getnum"
MIAH_CONSOLE_URL = "https://miahsms.com/bot/api/live-console"

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# ================= Helper Functions =================

def fetch_admin_ranges():
    """গুগল অ্যাপ স্ক্রিপ্ট (Admin Panel) থেকে রেঞ্জগুলো নিয়ে আসে"""
    try:
        res = requests.get(f"{GAS_WEBAPP_URL}?action=get", timeout=10)
        data = res.json()
        if data.get("status") == "ok":
            return data.get("ranges", [])
    except Exception as e:
        print("Error fetching ranges:", e)
    return []

def request_number_from_miah(range_code):
    """MiahHost API-তে রেঞ্জ পাঠায় এবং নম্বর নেয়"""
    headers = {
        "X-API-Key": MIAH_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"range": range_code}
    try:
        res = requests.post(MIAH_GETNUM_URL, json=payload, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print("Error getting number:", e)
        return None

def fetch_live_otp(since_id=0):
    """লাইভ ওটিপি স্ট্রিম চেক করে"""
    headers = {"X-API-Key": MIAH_API_KEY}
    try:
        res = requests.get(f"{MIAH_CONSOLE_URL}?since={since_id}&limit=50", headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print("Error fetching OTP:", e)
        return None

# ================= Handlers =================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start কমান্ড হ্যান্ডলার"""
    user_name = update.effective_user.first_name
    welcome_msg = (
        f"👋 **হ্যালো {user_name}! ওটিপি বটে আপনাকে স্বাগতম।**\n\n"
        "অনলাইন সার্ভিস বা অ্যাপসের জন্য ফ্রি নম্বর নিতে নিচের **'🌐 Live Ranges'** বাটনে চাপ দিন।"
    )
    
    keyboard = [
        [InlineKeyboardButton("🌐 Live Ranges (রেঞ্জ থেকে নম্বর নিন)", callback_data="show_ranges")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_msg, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_msg, parse_mode="Markdown", reply_markup=reply_markup)

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বাটনে চাপ দিলে কাজ করার লজিক"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # ১. লাইভ রেঞ্জ বাটনগুলো দেখানোর মেকানিজম
    if data == "show_ranges":
        ranges = fetch_admin_ranges()
        
        if not ranges:
            keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="start_menu")]]
            await query.edit_message_text(
                "❌ **বর্তমানে কোনো রেঞ্জ এভেলেবল নেই।**\nএডমিন প্যানেল থেকে রেঞ্জ যোগ করা হলে এখানে অটোমেটিক দেখা যাবে।",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        keyboard = []
        for r in ranges:
            flag = r.get("flag", "🌐")
            country = r.get("country", "Unknown")
            operator = r.get("operator", "General")
            range_code = r.get("range", "")
            
            # প্রতিটি রেঞ্জের আলাদা বাটন
            btn_text = f"{flag} {country} ({operator}) - [{range_code}]"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"getnum_{range_code}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="start_menu")])
        
        await query.edit_message_text(
            "📋 **লাইভ রেঞ্জসমূহ:**\nযেকোনো রেঞ্জের ওপর চাপ দিলে সরাসরি ওই রেঞ্জের নম্বর পেয়ে যাবেন:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ২. নির্দিষ্ট রেঞ্জ বাটনে চাপ দিলে নম্বর দেওয়ার মেকানিজম
    elif data.startswith("getnum_"):
        range_code = data.split("_")[1]
        await query.edit_message_text(f"⏳ **[{range_code}]** রেঞ্জ থেকে নম্বর নেওয়ার জন্য প্রসেসিং হচ্ছে...")

        result = request_number_from_miah(range_code)
        
        if result and result.get("meta", {}).get("code") == 200:
            num_data = result.get("data", {})
            full_number = num_data.get("full_number", "N/A")
            country = num_data.get("country", "N/A")
            operator = num_data.get("operator", "N/A")

            msg = (
                f"✅ **আপনার নম্বর তৈরি হয়েছে!**\n\n"
                f"📞 **Number:** `{full_number}`\n"
                f"🌍 **Country:** {country} ({operator})\n"
                f"📌 **Range:** `{range_code}`\n\n"
                "⚡ **ওটিপি মেসেজের জন্য অপেক্ষা করা হচ্ছে...**\n(ওটিপি আসার সাথে সাথে এখানে পাবেন)"
            )
            
            keyboard = [
                [InlineKeyboardButton("➕ অন্য নম্বর নিন", callback_data="show_ranges")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="start_menu")]
            ]
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

            # ওটিপি ট্র্যাকিং চালু করা
            chat_id = query.message.chat_id
            asyncio.create_task(poll_otp_for_number(context, chat_id, full_number))

        elif result and result.get("meta", {}).get("code") == 2946:
            keyboard = [[InlineKeyboardButton("🔄 অন্য রেঞ্জ চেষ্টা করুন", callback_data="show_ranges")]]
            await query.edit_message_text(
                f"⚠️ **এই রেঞ্জে বর্তমানে স্টক আউট!** ({range_code})\nঅন্য রেঞ্জে চাপ দিয়ে চেষ্টা করুন।",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[InlineKeyboardButton("🔙 রেঞ্জ লিস্টে ফিরুন", callback_data="show_ranges")]]
            await query.edit_message_text(
                "❌ **নম্বর পেতে সমস্যা হয়েছে!** আবার চেষ্টা করুন।",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data == "start_menu":
        await start_command(update, context)

async def poll_otp_for_number(context, chat_id, target_number):
    """নম্বরে ওটিপি আসলে বটের চ্যাটে পাঠাবে (৫ মিনিট ব্যাকগ্রাউন্ড চেক)"""
    max_checks = 60
    last_max_id = 0
    
    for _ in range(max_checks):
        await asyncio.sleep(5)
        otp_res = fetch_live_otp(since_id=last_max_id)
        
        if otp_res and otp_res.get("meta", {}).get("code") == 200:
            otps = otp_res.get("data", {}).get("otps", [])
            last_max_id = otp_res.get("data", {}).get("max_id", last_max_id)
            
            for item in otps:
                num = item.get("number", "")
                if target_number in num or num in target_number:
                    otp_code = item.get("otp", "N/A")
                    sms_body = item.get("message", "")
                    platform = item.get("platform", "SMS")
                    
                    otp_msg = (
                        f"📩 **নতুন ওটিপি কোড এসেছে!**\n\n"
                        f"🔹 **Platform:** {platform}\n"
                        f"📞 **Number:** `{target_number}`\n"
                        f"🔑 **OTP Code:** `{otp_code}`\n"
                        f"💬 **SMS:** `{sms_body}`"
                    )
                    await context.bot.send_message(chat_id=chat_id, text=otp_msg, parse_mode="Markdown")
                    return

# Setup Handlers
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CallbackQueryHandler(button_click_handler))

# Flask Route for Vercel/Render Webhook
@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        asyncio.run(application.update_queue.put(
            Update.de_json(request.get_json(force=True), application.bot)
        ))
        return "OK", 200
    return "Bot is Active!", 200

if __name__ == "__main__":
    application.run_polling()
