import telebot
import sqlite3
import threading
import time
import requests
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

db('CREATE TABLE IF NOT EXISTS memory (q TEXT PRIMARY KEY, a TEXT)')
db('CREATE TABLE IF NOT EXISTS bl (word TEXT PRIMARY KEY)')
db('CREATE TABLE IF NOT EXISTS members (chat_id INTEGER, user_id INTEGER, name TEXT, PRIMARY KEY(chat_id, user_id))')
db('CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY)')
db('CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER, PRIMARY KEY(chat_id, user_id))')
db('CREATE TABLE IF NOT EXISTS autotr (chat_id INTEGER PRIMARY KEY)')

def is_admin(m):
    try: return bot.get_chat_member(m.chat.id, m.from_user.id).status in ['creator', 'administrator']
    except: return True

def set_cmds():
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("start", "Start the bot"),
            telebot.types.BotCommand("id", "Target Id View"),
            telebot.types.BotCommand("translation", "Reply to translate"),
            telebot.types.BotCommand("tr", "Auto translation ON"),
            telebot.types.BotCommand("stoptr", "Auto translation OFF"),
            telebot.types.BotCommand("all", "Group member mention all"),
            telebot.types.BotCommand("mute", "Member mute"),
            telebot.types.BotCommand("unmute", "Mute release"),
            telebot.types.BotCommand("ban", "Ban user from group"),
            telebot.types.BotCommand("gpt", "AI Chat Debater"),
            telebot.types.BotCommand("topic", "Debate topics 30"),
            telebot.types.BotCommand("tiktok", "TikTok video download"),
            telebot.types.BotCommand("warn", "Warning 3 times auto mute"),
            telebot.types.BotCommand("pin", "Message reply pin"),
            telebot.types.BotCommand("unpin", "Unpin message")
        ])
    except: pass

@bot.message_handler(commands=['start', 'help'])
def help_cmd(m):
    bot.reply_to(m, "Hello My Friend")

@bot.message_handler(commands=['id'])
def id_cmd(m):
    uid = m.reply_to_message.from_user.id if m.reply_to_message else m.chat.id
    bot.reply_to(m, f"ID: {uid}")

@bot.message_handler(commands=['status'])
def status_cmd(m):
    if m.from_user.id != OWNER_ID: return
    g = len(db('SELECT * FROM groups'))
    u = len(db('SELECT DISTINCT user_id FROM members'))
    bot.reply_to(m, f"Total Groups: {g}\nTotal Users: {u}")

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

@bot.message_handler(commands=['mute', 'unmute', 'ban'])
def admin_acts(m):
    if is_admin(m) and m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        if 'unmute' in m.text:
            bot.restrict_chat_member(m.chat.id, uid, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
            bot.reply_to(m, "Unmuted.")
        elif 'ban' in m.text:
            bot.ban_chat_member(m.chat.id, uid)
            bot.reply_to(m, "Banned from the group.")
        else:
            bot.restrict_chat_member(m.chat.id, uid, until_date=time.time()+3600)
            bot.reply_to(m, "Muted 1 Hour.")

@bot.message_handler(commands=['warn'])
def warn_user(m):
    if is_admin(m) and m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        res = db('SELECT count FROM warns WHERE chat_id=? AND user_id=?', (m.chat.id, uid))
        count = (res[0][0] if res else 0) + 1
        if count >= 3:
            bot.restrict_chat_member(m.chat.id, uid, until_date=time.time()+86400)
            db('DELETE FROM warns WHERE chat_id=? AND user_id=?', (m.chat.id, uid))
            bot.reply_to(m, "Auto Muted 24 Hours (3/3 Warns).")
        else:
            db('INSERT OR REPLACE INTO warns VALUES (?,?,?)', (m.chat.id, uid, count))
            bot.reply_to(m, f"Warned ({count}/3)")

@bot.message_handler(commands=['pin', 'unpin'])
def pin_acts(m):
    if is_admin(m):
        try:
            if 'unpin' in m.text: bot.unpin_chat_message(m.chat.id)
            elif m.reply_to_message: bot.pin_chat_message(m.chat.id, m.reply_to_message.message_id)
            bot.reply_to(m, "Done.")
        except: pass

@bot.message_handler(commands=['gpt'])
def gpt_chat(m):
    q = m.text.replace('/gpt', '').strip()
    if not q: return
    try:
        url = f"https://open-api.my.id/api/v1/chat/gpt-3.5-turbo?prompt={requests.utils.quote(q)}"
        res = requests.get(url).json()
        bot.reply_to(m, res.get('reply', 'AI Connection Error.'))
    except: bot.reply_to(m, "Error connecting to AI.")

@bot.message_handler(commands=['topic'])
def debate_topics(m):
    topics = "🔥 **Top Debate Topics** 🔥\n\n"
    topics += "1. Is AI good for humans?\n2. Social media vs Real life\n3. Money vs Happiness\n4. Crypto vs Fiat Currency\n5. Online learning vs Classroom"
    bot.reply_to(m, topics, parse_mode="Markdown")

@bot.message_handler(commands=['tiktok'])
def tiktok_dl(m):
    link = m.text.replace('/tiktok', '').strip()
    if not link: 
        bot.reply_to(m, "Usage: /tiktok [TikTok Link]")
        return
    try:
        url = f"https://api.tiklydown.eu.org/api/download?url={link}"
        res = requests.get(url).json()
        video_url = res['video']['noWatermark']
        bot.send_video(m.chat.id, video_url, reply_to_message_id=m.message_id)
    except:
        bot.reply_to(m, "Failed to download video.")

@bot.message_handler(commands=['translation'])
def translate_reply(m):
    if m.reply_to_message and m.reply_to_message.text:
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={requests.utils.quote(m.reply_to_message.text)}"
            res = requests.get(url).json()
            bot.reply_to(m, f"📝 Translated (EN):\n{res[0][0][0]}")
        except: pass

@bot.message_handler(commands=['tr'])
def tr_on(m):
    if is_admin(m): db('INSERT OR REPLACE INTO autotr VALUES (?)', (m.chat.id,)); bot.reply_to(m, "Auto Translate ON.")

@bot.message_handler(commands=['stoptr'])
def tr_off(m):
    if is_admin(m): db('DELETE FROM autotr WHERE chat_id=?', (m.chat.id,)); bot.reply_to(m, "Auto Translate OFF.")

@bot.message_handler(commands=['addbl', 'quick', 'filter'])
def add_filters(m):
    if is_admin(m):
        cmd = '/addbl' if '/addbl' in m.text else ('/quick' if '/quick' in m.text else '/filter')
        w = m.text.replace(cmd, '').strip().lower()
        if w: db('INSERT OR REPLACE INTO bl VALUES (?)', (w,)); bot.reply_to(m, "Added.")

@bot.message_handler(func=lambda m: True, content_types=['text', 'new_chat_members'])
def auto_handlers(m):
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
    if res: 
        bot.reply_to(m, res[0][0])
        return

    if db('SELECT * FROM autotr WHERE chat_id=?', (m.chat.id,)):
        if not txt.startswith('/'):
            try:
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={requests.utils.quote(txt)}"
                translated = requests.get(url).json()[0][0][0]
                if translated.lower().strip() != txt.lower().strip():
                    bot.reply_to(m, f"🌐 {translated}")
            except: pass

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    set_cmds()
    bot.infinity_polling()
    
