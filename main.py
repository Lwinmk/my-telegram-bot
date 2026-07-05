import telebot
import sqlite3
import threading
import time
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "Live"
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

db('CREATE TABLE IF NOT EXISTS memory (q TEXT PRIMARY KEY, a TEXT)')
db('CREATE TABLE IF NOT EXISTS bl (word TEXT PRIMARY KEY)')
db('CREATE TABLE IF NOT EXISTS members (chat_id INTEGER, user_id INTEGER, name TEXT, PRIMARY KEY(chat_id, user_id))')
db('CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY)')

def is_admin(m):
    try: return bot.get_chat_member(m.chat.id, m.from_user.id).status in ['creator', 'administrator']
    except: return True

def set_cmds():
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("start", "Start"),
            telebot.types.BotCommand("help", "Help")
        ])
    except: pass

@bot.message_handler(commands=['start', 'help'])
def help_cmd(m):
    bot.reply_to(m, "Active.")

@bot.message_handler(commands=['broadcast'])
def bc(m):
    if m.from_user.id != OWNER_ID: return
    txt = m.text.replace('/broadcast', '').strip()
    if txt:
        for row in db('SELECT chat_id FROM groups'):
            try: bot.send_message(row[0], txt)
            except: pass

@bot.message_handler(commands=['all'])
def mention(m):
    if is_admin(m):
        rows = db('SELECT user_id, name FROM members WHERE chat_id=?', (m.chat.id,))
        tags = [f"[{n}](tg://user?id={u})" for u, n in rows]
        for i in range(0, len(tags), 50):
            bot.send_message(m.chat.id, " ".join(tags[i:i+50]), parse_mode="Markdown")

@bot.message_handler(commands=['mute', 'kick', 'ban'])
def admin_acts(m):
    if is_admin(m) and m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        if 'mute' in m.text: bot.restrict_chat_member(m.chat.id, uid, until_date=time.time()+3600)
        elif 'kick' in m.text: bot.ban_chat_member(m.chat.id, uid); bot.unban_chat_member(m.chat.id, uid)
        elif 'ban' in m.text: bot.ban_chat_member(m.chat.id, uid)
        bot.reply_to(m, "Done.")

@bot.message_handler(commands=['addbl'])
def addbl(m):
    if is_admin(m):
        w = m.text.replace('/addbl', '').strip().lower()
        if w: db('INSERT OR REPLACE INTO bl VALUES (?)', (w,))

@bot.message_handler(func=lambda m: True, content_types=['text', 'new_chat_members'])
def auto(m):
    if m.chat.type != 'private':
        db('INSERT OR REPLACE INTO groups VALUES (?)', (m.chat.id,))
        if m.from_user and not m.from_user.is_bot:
            db('INSERT OR REPLACE INTO members VALUES (?,?,?)', (m.chat.id, m.from_user.id, m.from_user.first_name))
    
    if m.content_type == 'new_chat_members': return

    txt = m.text.strip()
    
    for row in db('SELECT * FROM bl'):
        if row[0] in txt.lower():
            try: bot.delete_message(m.chat.id, m.message_id)
            except: pass
            return

    if ":" in txt:
        q, a = [x.strip() for x in txt.split(":", 1)]
        db('INSERT OR REPLACE INTO memory VALUES (?,?)', (q.lower(), a))
        bot.reply_to(m, "Saved.")
        return

    res = db('SELECT a FROM memory WHERE q=?', (txt.lower(),))
    if res: bot.reply_to(m, res[0][0])

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    set_cmds()
    bot.infinity_polling()
                     
