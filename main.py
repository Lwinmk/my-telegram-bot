import telebot
import sqlite3
import threading
from flask import Flask

# --- WEB SERVER FOR RENDER (KEEP BOT ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- CONFIGURATION ---
API_TOKEN = '8666581291:AAEJgXWQUwsOdO0yT4-AFEqIj73z7arnrCM'  # <--- သင့် Bot Token ကို ပြန်ထည့်ပါ
bot = telebot.TeleBot(API_TOKEN)

# --- DATABASE SYSTEM ---
def init_db():
    conn = sqlite3.connect('rose_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS knowledge (question TEXT PRIMARY KEY, answer TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS filters (keyword TEXT PRIMARY KEY, reply TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, chat_id INTEGER, count INTEGER, PRIMARY KEY (user_id, chat_id))')
    conn.commit()
    conn.close()

init_db()

def db_action(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect('rose_bot.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetchone: res = cursor.fetchone()
    elif fetchall: res = cursor.fetchall()
    conn.commit()
    conn.close()
    return res

def is_admin(message):
    status = bot.get_chat_member(message.chat.id, message.from_user.id).status
    return status in ['creator', 'administrator']

# --- ROSE BOT MANAGEMENT COMMANDS ---
@bot.message_handler(commands=['setwelcome'])
def set_welcome(message):
    if is_admin(message):
        text = message.text.replace('/setwelcome', '').strip()
        if text:
            db_action('INSERT OR REPLACE INTO settings (key, value) VALUES ("welcome", ?)', (text,))
            bot.reply_to(message, "✅ Welcome message has been updated.")

@bot.message_handler(commands=['setrules'])
def set_rules(message):
    if is_admin(message):
        text = message.text.replace('/setrules', '').strip()
        if text:
            db_action('INSERT OR REPLACE INTO settings (key, value) VALUES ("rules", ?)', (text,))
            bot.reply_to(message, "✅ Group rules have been updated.")

@bot.message_handler(commands=['rules'])
def get_rules(message):
    res = db_action('SELECT value FROM settings WHERE key="rules"', fetchone=True)
    if res: bot.reply_to(message, f"📋 *Group Rules*:\n\n{res[0]}", parse_mode="Markdown")
    else: bot.reply_to(message, "❌ No rules have been set for this group yet.")

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if is_admin(message) and message.reply_to_message:
        target = message.reply_to_message.from_user
        current = db_action('SELECT count FROM warnings WHERE user_id=? AND chat_id=?', (target.id, message.chat.id), fetchone=True)
        count = (current[0] + 1) if current else 1
        
        if count >= 3:
            bot.ban_chat_member(message.chat.id, target.id)
            db_action('DELETE FROM warnings WHERE user_id=? AND chat_id=?', (target.id, message.chat.id))
            bot.reply_to(message, f"🚫 {target.first_name} received 3 warnings and has been banned.")
        else:
            db_action('INSERT OR REPLACE INTO warnings (user_id, chat_id, count) VALUES (?, ?, ?)', (target.id, message.chat.id, count))
            bot.reply_to(message, f"⚠️ {target.first_name} has been warned ({count}/3).")

@bot.message_handler(commands=['filter'])
def add_filter(message):
    if is_admin(message):
        args = message.text.replace('/filter', '').strip().split(' ', 1)
        if len(args) == 2:
            db_action('INSERT OR REPLACE INTO filters (keyword, reply) VALUES (?, ?)', (args[0].lower(), args[1]))
            bot.reply_to(message, f"✅ Added filter for: *{args[0]}*", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop_filter(message):
    if is_admin(message):
        keyword = message.text.replace('/stop', '').strip().lower()
        if keyword:
            db_action('DELETE FROM filters WHERE keyword=?', (keyword,))
            bot.reply_to(message, f"❌ Stopped filtering for: *{keyword}*", parse_mode="Markdown")

# --- STANDARD ADMIN COMMANDS ---
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if is_admin(message) and message.reply_to_message:
        bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, f"🚫 {message.reply_to_message.from_user.first_name} has been banned.")

@bot.message_handler(commands=['kick'])
def kick_user(message):
    if is_admin(message) and message.reply_to_message:
        bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, f"🏃‍♂️ {message.reply_to_message.from_user.first_name} has been kicked.")

@bot.message_handler(commands=['mute'])
def mute_user(message):
    if is_admin(message) and message.reply_to_message:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, permissions=telebot.types.ChatPermissions(can_send_messages=False))
        bot.reply_to(message, f"🔇 {message.reply_to_message.from_user.first_name} has been muted.")

@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if is_admin(message) and message.reply_to_message:
        bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, permissions=telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
        bot.reply_to(message, f"🔊 {message.reply_to_message.from_user.first_name} has been unmuted.")

@bot.message_handler(commands=['pin'])
def pin_message(message):
    if is_admin(message) and message.reply_to_message:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 Message pinned.")

@bot.message_handler(commands=['all'])
def mention_all(message):
    bot.reply_to(message, "📢 Attention everyone! Please check this out.")

# --- NEW MEMBER GREETING ---
@bot.message_handler(content_types=['new_chat_members'])
def greeting_members(message):
    res = db_action('SELECT value FROM settings WHERE key="welcome"', fetchone=True)
    welcome_text = res[0] if res else "Welcome to the group!"
    for member in message.new_chat_members:
        bot.send_message(message.chat.id, f"👋 Hello {member.first_name}, {welcome_text}")

# --- AUTO SPAM & AUTOMATIC AUTO-LEARNING SYSTEM ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_text = message.text or ""
    if "http" in user_text.lower() or "t.me/" in user_text.lower():
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.restrict_chat_member(message.chat.id, message.from_user.id, permissions=telebot.types.ChatPermissions(can_send_messages=False))
            bot.send_message(message.chat.id, f"⚠️ {message.from_user.first_name} was auto-muted for sending links.")
            return
        except: pass

    filter_res = db_action('SELECT reply FROM filters WHERE keyword=?', (user_text.lower(),), fetchone=True)
    if filter_res:
        bot.reply_to(message, filter_res[0])
        return

    if message.reply_to_message:
        if not message.reply_to_message.from_user.is_bot and not message.from_user.is_bot:
            question = message.reply_to_message.text
            answer = message.text
            if question and answer:
                db_action('INSERT OR REPLACE INTO knowledge (question, answer) VALUES (?, ?)', (question.lower().strip(), answer.strip()))
    else:
        learn_res = db_action('SELECT answer FROM knowledge WHERE question=?', (user_text.lower().strip(),), fetchone=True)
        if learn_res:
            bot.reply_to(message, learn_res[0])

if __name__ == "__main__":
    # Web server ကို နောက်ကွယ်မှာ ခွဲပတ်ထားမယ်
    threading.Thread(target=run_flask).start()
    print("[🚀] Server & Bot are running...")
    bot.infinity_polling()
