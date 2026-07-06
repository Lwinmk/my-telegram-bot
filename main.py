import sqlite3
import logging
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================
# CONFIG
# ==========================

BOT_TOKEN = "8666581291:AAEJgXWQUwsOdO0yT4-AFEqIj73z7arnrCM"
OWNER_ID = 5915848053

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

# ==========================
# DATABASE
# ==========================

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS groups(
chat_id INTEGER PRIMARY KEY,
title TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS filters(
word TEXT PRIMARY KEY
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS autoreply(
word TEXT PRIMARY KEY,
reply TEXT
)
""")

db.commit()

# ==========================
# FUNCTIONS
# ==========================

def save_group(chat_id, title):
    cur.execute(
        "INSERT OR IGNORE INTO groups VALUES(?,?)",
        (chat_id, title)
    )
    db.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type != "private":
        save_group(
            update.effective_chat.id,
            update.effective_chat.title
        )

    await update.message.reply_text(
        "✅ Group Manager Bot Online"
    )


async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"""
Chat ID:
{update.effective_chat.id}

User ID:
{update.effective_user.id}
"""
    )


async def joined(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_group(
        update.effective_chat.id,
        update.effective_chat.title
    )

# ==========================
# PART 2 HERE
# ==========================# ==========================
# ADMIN CHECK
# ==========================

async def is_admin(update: Update):
    chat = update.effective_chat.id
    user = update.effective_user.id

    member = await update.get_bot().get_chat_member(chat, user)
    return member.status in ["administrator", "creator"]

# ==========================
# BAN USER
# ==========================

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to user to ban.")
        return

    target = update.message.reply_to_message.from_user.id

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target)
        await update.message.reply_text("🚫 User Banned")
    except Exception as e:
        await update.message.reply_text(str(e))

# ==========================
# KICK USER
# ==========================

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to user to kick.")
        return

    target = update.message.reply_to_message.from_user.id

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target)
        await context.bot.unban_chat_member(update.effective_chat.id, target)
        await update.message.reply_text("👢 User Kicked")
    except Exception as e:
        await update.message.reply_text(str(e))

# ==========================
# MUTE USER
# ==========================

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to user to mute.")
        return

    target = update.message.reply_to_message.from_user.id

    permissions = ChatPermissions(
        can_send_messages=False
    )

    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target,
            permissions
        )
        await update.message.reply_text("🔇 User Muted")
    except Exception as e:
        await update.message.reply_text(str(e))

# ==========================
# UNMUTE USER
# ==========================

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to user to unmute.")
        return

    target = update.message.reply_to_message.from_user.id

    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_invite_users=True
    )

    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target,
            permissions
        )
        await update.message.reply_text("🔊 User Unmuted")
    except Exception as e:
        await update.message.reply_text(str(e))
# ==========================
# AUTO REPLY + FILTER CHECK (MESSAGE HANDLER)
# ==========================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text
    if not text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # ==========================
    # WORD FILTER
    # ==========================

    cur.execute("SELECT word FROM filters")
    bad_words = [i[0] for i in cur.fetchall()]

    for w in bad_words:
        if w.lower() in text.lower():
            try:
                await update.message.delete()
                await update.message.reply_text("🚫 Word not allowed")
                return
            except:
                return

    # ==========================
    # AUTO REPLY
    # ==========================

    cur.execute("SELECT word, reply FROM autoreply")
    replies = cur.fetchall()

    for trigger, reply in replies:
        if trigger.lower() in text.lower():
            await update.message.reply_text(reply)
            return

# ==========================
# BROADCAST (OWNER ONLY)
# ==========================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast message")
        return

    msg = " ".join(context.args)

    cur.execute("SELECT chat_id FROM groups")
    groups = cur.fetchall()

    sent = 0

    for g in groups:
        try:
            await context.bot.send_message(g[0], msg)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ Sent to {sent} groups")
# ==========================
# MESSAGE HANDLER REGISTER
# ==========================

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", chatid))

    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))

    app.add_handler(CommandHandler("broadcast", broadcast))

    # Auto message handler (filter + auto reply)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # New group detect
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, joined))

    print("🤖 Bot is running...")
    app.run_polling()


# ==========================
# START BOT
# ==========================

if __name__ == "__main__":
    main()
