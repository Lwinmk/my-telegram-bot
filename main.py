import os
import time
import sqlite3
import threading
import telebot
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Telegram Bot is Live and Running on Render!"

def run_flask():
    try:
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Flask Server Error: {e}")

API_TOKEN = '8666581291:AAEJgXWQUwsOdO0yT4-AFEqIj73z7arnrCM'
bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=10)
DB_PATH = 'data.db'
OWNER_ID = 5915848053 

def db(q, p=()):
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute(q, p)
        res = c.fetchall()
        conn.commit()
        conn.close()
        return res
    except Exception as e:
        print(f"Database Error: {e}")
        return []

db('CREATE TABLE IF NOT EXISTS memory (q TEXT PRIMARY KEY, a TEXT, is_sticker INTEGER DEFAULT 0)')
db('CREATE TABLE IF NOT EXISTS bl (word TEXT PRIMARY KEY)')
db('CREATE TABLE IF NOT EXISTS members (chat_id INTEGER, user_id INTEGER, name TEXT, PRIMARY KEY(chat_id, user_id))')
db('CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY)')
db('CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER, PRIMARY KEY(chat_id, user_id))')

def is_admin(m):
    try: 
        return bot.get_chat_member(m.chat.id, m.from_user.id).status in ['creator', 'administrator']
    except: 
        return True

@bot.message_handler(commands=['start', 'help'])
def start_cmd(m):
    if m.chat.type == 'private':
        cmds_text = (
            "📌 **Available Commands:**\n\n"
            "▫️ /id - Target Id View\n"
            "▫️ /mute - Member mute (Reply)\n"
            "▫️ /unmute - Mute release (Reply)\n"
            "▫️ /kick - Kick user from group (Reply)\n"
            "▫️ /ban - Ban user from group (Reply)\n"
            "▫️ /warn - Warning 3 times auto mute (Reply)\n"
            "▫️ /pin - Message reply pin (Reply)\n"
            "▫️ /unpin - Unpin message\n"
            "▫️ /filter - Add word to bad word list"
        )
        bot.reply_to(m, cmds_text, parse_mode="Markdown")
    else:
        bot.reply_to(m, "Hello My Friend")

@bot.message_handler(commands=['id'])
def get_id(m):
    try:
        if m.reply_to_message:
            target = m.reply_to_message.from_user
            bot.reply_to(m, f"👤 Name: {target.first_name}\n🆔 User ID: `{target.id}`", parse_mode="Markdown")
        else:
            bot.reply_to(m, f"👥 Chat ID: `{m.chat.id}`\n👤 Your ID: `{m.from_user.id}`", parse_mode="Markdown")
    except:
        pass

@bot.message_handler(commands=['status'])
def status_cmd(m):
    if m.from_user.id != OWNER_ID: return
    g = len(db('SELECT * FROM groups'))
    u = len(db('SELECT DISTINCT user_id FROM members'))
    bot.reply_to(m, f"📊 Bot Statistics:\nGroups: {g}\nUsers: {u}")

@bot.message_handler(commands=['broadcast'])
def bc(m):
    if m.from_user.id != OWNER_ID: return
    txt = m.text.replace('/broadcast', '').strip()
    if txt:
        for row in db('SELECT chat_id FROM groups'):
            try: bot.send_message(row[0], txt)
            except: pass
        bot.reply_to(m, "Broadcast done.")

@bot.message_handler(commands=['mute', 'unmute', 'kick', 'ban'])
def admin_acts(m):
    if is_admin(m) and m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        try:
            if 'unmute' in m.text:
                bot.restrict_chat_member(
                    m.chat.id, uid, 
                    permissions=telebot.types.ChatPermissions(
                        can_send_messages=True, 
                        can_send_media_messages=True, 
                        can_send_other_messages=True
                    )
                )
                bot.reply_to(m, "✅ Unmuted.")
            elif 'kick' in m.text:
                bot.ban_chat_member(m.chat.id, uid)
                bot.unban_chat_member(m.chat.id, uid)
                bot.reply_to(m, "👢 Kicked.")
            elif 'ban' in m.text:
                bot.ban_chat_member(m.chat.id, uid)
                bot.reply_to(m, "🚫 Banned.")
            else:
                bot.restrict_chat_member(
                    m.chat.id, uid, 
                    permissions=telebot.types.ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False
                    ),
                    until_date=int(time.time() + 3600)
                )
                bot.reply_to(m, "🔇 Muted for 1 Hour.")
        except Exception as e:
            bot.reply_to(m, f"❌ Admin Error: {e}")

@bot.message_handler(commands=['pin', 'unpin'])
def pin_acts(m):
    if is_admin(m):
        try:
            if 'unpin' in m.text: 
                bot.unpin_chat_message(m.chat.id)
            elif m.reply_to_message: 
                bot.pin_chat_message(m.chat.id, m.reply_to_message.message_id)
            bot.reply_to(m, "Done.")
        except: 
            pass

@bot.message_handler(commands=['warn'])
def warn_user(m):
    if is_admin(m) and m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        try:
            res = db('SELECT count FROM warns WHERE chat_id=? AND user_id=?', (m.chat.id, uid))
            count = (res[0][0] if res else 0) + 1
            if count >= 3:
                bot.restrict_chat_member(
                    m.chat.id, uid,
                    permissions=telebot.types.ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False
                    ),
                    until_date=int(time.time() + 86400)
                )
                db('DELETE FROM warns WHERE chat_id=? AND user_id=?', (m.chat.id, uid))
                bot.reply_to(m, "🔇 Auto Muted 24 Hours (3/3 Warns).")
            else:
                db('INSERT OR REPLACE INTO warns VALUES (?,?,?)', (m.chat.id, uid, count))
                bot.reply_to(m, f"⚠️ Warned ({count}/3)")
        except Exception as e:
            bot.reply_to(m, f"❌ Error: {e}")

@bot.message_handler(commands=['addbl', 'quick', 'filter'])
def add_filters(m):
    if is_admin(m):
        cmd = '/addbl' if '/addbl' in m.text else ('/quick' if '/quick' in m.text else '/filter')
        w = m.text.replace(cmd, '').strip().lower()
        if w: 
            db('INSERT OR REPLACE INTO bl VALUES (?)', (w,))
            bot.reply_to(m, f"Added '{w}' to Filter list.")

@bot.message_handler(func=lambda m: True, content_types=['text', 'sticker', 'new_chat_members', 'left_chat_member'])
def auto_handlers(m):
    if m.chat.type != 'private':
        db('INSERT OR REPLACE INTO groups VALUES (?)', (m.chat.id,))
        if m.from_user and not m.from_user.is_bot:
            db('INSERT OR REPLACE INTO members VALUES (?,?,?)', (m.chat.id, m.from_user.id, m.from_user.first_name))
    
    if m.content_type == 'new_chat_members':
        for new_user in m.new_chat_members:
            if not new_user.is_bot:
                bot.send_message(m.chat.id, f"Welcome {new_user.first_name} to our group! 🎉")
        return

    if m.content_type == 'left_chat_member':
        if not m.left_chat_member.is_bot:
            bot.send_message(m.chat.id, f"Goodbye {m.left_chat_member.first_name}! 👋")
        return

    if m.content_type == 'text' and m.reply_to_message and m.reply_to_message.content_type == 'sticker':
        if m.text.strip().endswith(':'):
            q = m.text.replace(':', '').strip().lower()
            if q:
                db('INSERT OR REPLACE INTO memory VALUES (?,?,1)', (q, m.reply_to_message.sticker.file_id))
                bot.reply_to(m, "Sticker Saved Successful.")
                return

    if m.content_type != 'text': return
    txt = m.text.strip()

    for row in db('SELECT * FROM bl'):
        if row[0] in txt.lower():
            try: 
                bot.delete_message(m.chat.id, m.message_id)
            except: 
                pass
            return

    if ":" in txt and not txt.startswith('/'):
        q, a = [x.strip() for x in txt.split(":", 1)]
        if q and a:
            db('INSERT OR REPLACE INTO memory VALUES (?,?,0)', (q.lower(), a))
            bot.reply_to(m, "Text Auto-Response Saved.")
            return

    res = db('SELECT a, is_sticker FROM memory WHERE q=?', (txt.lower(),))
    if res:
        if res[0][1] == 1: 
            bot.send_sticker(m.chat.id, res[0][0], reply_to_message_id=m.message_id)
        else: 
            bot.reply_to(m, res[0][0])
        return

    if not txt.startswith('/'):
        try: 
            bot.set_message_reaction(m.chat.id, m.message_id, [telebot.types.ReactionTypeEmoji(emoji="👍")])
        except: 
            pass

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"Bot Connection Lost, Reconnecting... Error: {e}")
            time.sleep(5)
        
