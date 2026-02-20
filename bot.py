from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import time
from datetime import timedelta, datetime
import re

# =============== CONFIG ===============
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found! Add it in environment variables")

YOUTUBE_CHANNEL = "http://www.youtube.com/@Sinhala_Gamingtriks"
GROUP_NAME = "Sinhala Gamingtriks Yt"
BRAND_NAME = "Sinhala_Gamingtriks"

SAFE_DOMAINS = ["youtube.com", "youtu.be", "t.me"]

MAX_WARNS = 3
MUTE_MINUTES = 30

SPAM_LIMIT = 6
SPAM_WINDOW = 5
# ======================================

warns = {}
user_message_times = {}

# ================= ADMIN CHECK =================
async def is_admin(chat_id, user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except:
        return False

# ================= BASIC COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Sinhala Gamingtriks Bot is online!\nType /help for commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start bot\n"
        "/help - Show commands\n"
        "/about - About bot\n"
        "/youtube - YouTube channel\n"
        "/subscribe - Subscribe button\n"
        "/rules - Group rules\n"
        "/stats - Group stats\n"
        "/ping - Bot status\n"
        "/info - Your info"
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Official Sinhala Gamingtriks bot 🎮\nAnti-spam • Anti-link • Group management")

# --- /youtube command ---
async def youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📺 Subscribe", url=YOUTUBE_CHANNEL)]])
    await update.message.reply_text(
        f"▶️ Sinhala Gamingtriks YouTube Channel\n{YOUTUBE_CHANNEL}",
        reply_markup=keyboard
    )

# --- /subscribe command ---
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📺 View & Subscribe", url=YOUTUBE_CHANNEL)]])
    await update.message.reply_text(
        "🔔 Subscribe to Sinhala Gamingtriks YouTube Channel!",
        reply_markup=keyboard
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 Group Rules:\n1. Be respectful\n2. No spam\n3. No unsafe links\n4. Follow admins")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Bot is ONLINE")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"👤 Your Info\nName: {user.first_name}\nUsername: @{user.username}\nID: {user.id}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("ℹ️ This command works only in groups.")
        return
    try:
        members = await context.bot.get_chat_member_count(chat.id)
        admins = await context.bot.get_chat_administrators(chat.id)
        await update.message.reply_text(f"📊 Group Stats\nGroup: {chat.title}\nMembers: {members}\nAdmins: {len(admins)}")
    except:
        await update.message.reply_text("❌ Bot must be admin to show stats.")

# ================= WELCOME =================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(f"✨ Welcome {member.first_name} to {GROUP_NAME}\n📺 YouTube: {YOUTUBE_CHANNEL}")

# ================= WARN SYSTEM =================
async def warn_user(chat_id, user, context, reason):
    warns[user.id] = warns.get(user.id, 0) + 1
    count = warns[user.id]
    if count < MAX_WARNS:
        await context.bot.send_message(chat_id, f"⚠️ Warning {user.first_name}\nReason: {reason}\n{count}/{MAX_WARNS}")
    else:
        until = datetime.now() + timedelta(minutes=MUTE_MINUTES)
        await context.bot.restrict_chat_member(chat_id, user.id, ChatPermissions(can_send_messages=False), until_date=until)
        warns[user.id] = 0
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔓 Unmute", callback_data=f"unmute:{user.id}")]])
        await context.bot.send_message(chat_id, f"🔇 {user.first_name} muted for {MUTE_MINUTES} minutes", reply_markup=keyboard)

# ================= FILTER SPAM + LINKS =================
async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    user = message.from_user
    chat_id = message.chat.id

    # Ignore admins
    if await is_admin(chat_id, user.id, context):
        return

    # Ignore commands
    if message.text and message.text.startswith("/"):
        return

    # ---- LINK CHECK ----
    text = message.text or ""
    if re.search(r"http[s]?://", text):
        if not any(domain in text for domain in SAFE_DOMAINS):
            await message.delete()
            await warn_user(chat_id, user, context, "Unsafe link")
            return

    # ---- SPAM CHECK (count ALL messages: text, photo, gif, sticker) ----
    now = time.time()
    times = user_message_times.get(user.id, [])
    times = [t for t in times if now - t < SPAM_WINDOW]
    times.append(now)
    user_message_times[user.id] = times

    if len(times) > SPAM_LIMIT:
        try:
            await message.delete()
        except:
            pass
        await warn_user(chat_id, user, context, "Spamming")

# ================= UNMUTE =================
async def unmute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    admin_id = query.from_user.id
    if not await is_admin(chat_id, admin_id, context):
        await query.answer("Admins only!", show_alert=True)
        return
    user_id = int(query.data.split(":")[1])
    await context.bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=True))
    await query.message.edit_text("✅ User unmuted")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("youtube", youtube))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("info", info))

    # Messages & Callbacks
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, filter_messages))
    app.add_handler(CallbackQueryHandler(unmute_callback, pattern="^unmute:"))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()


