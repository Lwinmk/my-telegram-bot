import telebot
import sqlite3
import threading
import time
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "Bot is Live"
def run_flask(): app.run(host='0.0.0.0', port=8080)

API_TOKEN = '8666581291:AAEJgXWQUwsOdO0yT4-AFEqIj73z7arnrCM'
bot = telebot.TeleBot(API_TOKEN)
DB_PATH = 'data.db'
OWNER_ID = 5915848053 

def db(q, p=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(q, p)
    res = c.fetchall()
    conn.commit()
    conn.close()
    return res

db('CREATE TABLE IF NOT EXISTS memory (q TEXT PRIMARY KEY, a TEXT, is_sticker INTEGER DEFAULT 0)')
db('CREATE TABLE IF NOT EXISTS bl (word TEXT PRIMARY KEY)')
db('CREATE TABLE IF NOT EXISTS members (chat_id INTEGER, user_id INTEGER, name TEXT, PRIMARY KEY(chat_id, user_id))')
db('CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY)')
db('CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER, PRIMARY KEY(chat_id, user_id))')

def is_admin(m):
    try: return bot.get_chat_member(m.chat.id, m.from_user.id).status in ['creator', 'administrator']
    except: return True

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
        if 'unmute' in m.text:
            bot.restrict_chat_member(m.chat.id, uid, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
            bot.reply_to(m, "Unmuted.")
        elif 'kick' in m.text:
            bot.ban_chat_member(m.chat.id, uid)
            bot.unban_chat_member(m.chat.id, uid)
            bot.reply_to(m, "Kicked.")
        elif 'ban' in m.text:
            bot.ban_chat_member(m.chat.id, uid)
            bot.reply_to(m, "Banned.")
        else:
            bot.restrict_chat_member(m.chat.id, uid, until_date=time.time()+3600)
            bot.reply_to(m, "Muted.")

@bot.message_handler(commands=['pin', 'unpin'])
def pin_acts(m):
    if is_admin(m) and m.reply_to_message:
        if 'unpin' in m.text: bot.unpin_chat_message(m.chat.id)
        else: bot.pin_chat_message(m.chat.id, m.reply_to_message.message_id)

@bot.message_handler(commands=['warn'])
def warn_user(m):
    if is_admin(m) and m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        res = db('SELECT count FROM warns WHERE chat_id=? AND user_id=?', (m.chat.id, uid))
        count = (res[0][0] if res else 0) + 1
        if count >= 3:
            bot.restrict_chat_member(m.chat.id, uid, until_date=time.time()+86400)
            db('DELETE FROM warns WHERE chat_id=? AND user_id=?', (m.chat.id, uid))
            bot.reply_to(m, "Muted 24h (3/3 Warns).")
        else:
            db('INSERT OR REPLACE INTO warns VALUES (?,?,?)', (m.chat.id, uid, count))
            bot.reply_to(m, f"Warned ({count}/3)")

@bot.message_handler(commands=['addbl', 'quick', 'filter'])
def add_filters(m):
    if is_admin(m):
        cmd = '/addbl' if '/addbl' in m.text else ('/quick' if '/quick' in m.text else '/filter')
        w = m.text.replace(cmd, '').strip().lower()
        if w: db('INSERT OR REPLACE INTO bl VALUES (?)', (w,)); bot.reply_to(m, "Added to Filter.")

@bot.message_handler(func=lambda m: True, content_types=['text', 'sticker', 'new_chat_members'])
def auto_handlers(m):
    if m.chat.type != 'private':
        db('INSERT OR REPLACE INTO groups VALUES (?)', (m.chat.id,))
        if m.from_user and not m.from_user.is_bot:
            db('INSERT OR REPLACE INTO members VALUES (?,?,?)', (m.chat.id, m.from_user.id, m.from_user.first_name))
    
    if m.content_type == 'new_chat_members': return

    if m.content_type == 'text' and m.reply_to_message and m.reply_to_message.content_type == 'sticker':
        if m.text.strip().endswith(':'):
            q = m.text.replace(':', '').strip().lower()
            if q:
                db('INSERT OR REPLACE INTO memory VALUES (?,?,1)', (q, m.reply_to_message.sticker.file_id))
                bot.reply_to(m, "Sticker Saved.")
                return

    if m.content_type != 'text': return
    txt = m.text.strip()

    for row in db('SELECT * FROM bl'):
        if row[0] in txt.lower():
            try: bot.delete_message(m.chat.id, m.message_id)
            except: pass
            return

    if ":" in txt:
        q, a = [x.strip() for x in txt.split(":", 1)]
        db('INSERT OR REPLACE INTO memory VALUES (?,?,0)', (q.lower(), a))
        bot.reply_to(m, "Saved.")
        return

    res = db('SELECT a, is_sticker FROM memory WHERE q=?', (txt.lower(),))
    if res:
        if res[0][1] == 1: bot.send_sticker(m.chat.id, res[0][0], reply_to_message_id=m.message_id)
        else: bot.reply_to(m, res[0][0])
        return

    if not txt.startswith('/'):
        try: bot.set_message_reaction(m.chat.id, m.message_id, [telebot.types.ReactionTypeEmoji(emoji="👍")])
        except: pass

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
    
