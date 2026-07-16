import os
import time
import sqlite3
import random
import threading
import telebot
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Bot is Live"

def run_flask():
    try:
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Flask Server Error: {e}")

API_TOKEN = '8666581291:AAH3j9ozaTfe44OsJ7zo7gWfipQOoHsbTV4'
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
db('CREATE TABLE IF NOT EXISTS settings (chat_id INTEGER PRIMARY KEY, rules TEXT, welcome TEXT)')

def is_admin(m):
    try: 
        return bot.get_chat_member(m.chat.id, m.from_user.id).status in ['creator', 'administrator']
    except: 
        return True

def typing_effect(chat_id, reply_to_id, full_text):
    try:
        msg = bot.send_message(chat_id, full_text[0], reply_to_message_id=reply_to_id)
        current_text = full_text[0]
        step = 3
        for i in range(1, len(full_text), step):
            current_text += full_text[i:i+step]
            try:
                bot.edit_message_text(current_text, chat_id, msg.message_id)
                time.sleep(0.2)
            except:
                pass
        if current_text != full_text:
            try: bot.edit_message_text(full_text, chat_id, msg.message_id)
            except: pass
    except:
        try: bot.send_message(chat_id, full_text, reply_to_message_id=reply_to_id)
        except: pass

@bot.message_handler(commands=['start', 'help'])
def start_cmd(m):
    if m.chat.type == 'private':
        cmds_text = (
            "📌 **Available Commands:**\n\n"
            "▫️ /id - Target Id View\n"
            "▫️ /mute [time] [reason] - Mute User (Reply)\n"
            "▫️ /unmute - Mute release (Reply)\n"
            "▫️ /kick - Kick user from group (Reply)\n"
            "▫️ /ban - Ban user from group (Reply)\n"
            "▫️ /warn - Warning 3 times auto mute (Reply)\n"
            "▫️ /rules - View Group Rules\n"
            "▫️ /setrules - Set Group Rules (Admin)\n"
            "▫️ /setwelcome - Set Welcome Message (Admin)\n"
            "▫️ /filter - Add word to bad word list (Admin)\n"
            "▫️ /status - Bot Statistics (Everyone)"
        )
        threading.Thread(target=typing_effect, args=(m.chat.id, m.message_id, cmds_text)).start()
    else:
        threading.Thread(target=typing_effect, args=(m.chat.id, m.message_id, "Hello My Friend 👋")).start()

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
    g = len(db('SELECT * FROM groups'))
    u = len(db('SELECT DISTINCT user_id FROM members'))
    bot.reply_to(m, f"📊 **Bot Statistics:**\n\n👥 Total Users: {u}\n🏠 Total Groups: {g}", parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def bc(m):
    if m.from_user.id != OWNER_ID: return
    
    if m.reply_to_message:
        for row in db('SELECT chat_id FROM groups'):
            try:
                bot.forward_message(row[0], m.chat.id, m.reply_to_message.message_id)
            except:
                pass
        bot.reply_to(m, "Broadcast (Forwarded) done.")
    else:
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
                        can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True
                    )
                )
                bot.reply_to(m, "✅ Unmuted.")
            elif 'kick' in m.text:
                bot.ban_chat_member(m.chat.id, uid)
                bot.unban_chat_member(m.chat.id, uid)
                bot.reply_to(m, "👢 Kicked.")
            elif 'ban' in m.text:
                bot.ban_chat_member(m.chat.id, uid)
                bot.unban_chat_member(m.chat.id, uid)
                bot.reply_to(m, "🚫 Banned.")
            elif 'mute' in m.text:
                args = m.text.split()
                until_time = 0
                reason = "No reason provided"
                
                if len(args) > 1:
                    time_str = args[1]
                    unit = time_str[-1].lower()
                    if unit in ['m', 'h', 'd'] and time_str[:-1].isdigit():
                        val = int(time_str[:-1])
                        if unit == 'm': until_time = int(time.time() + val * 60)
                        elif unit == 'h': until_time = int(time.time() + val * 3600)
                        elif unit == 'd': until_time = int(time.time() + val * 86400)
                        if len(args) > 2:
                            reason = " ".join(args[2:])
                    else:
                        reason = " ".join(args[1:])
                
                bot.restrict_chat_member(
                    m.chat.id, uid, 
                    permissions=telebot.types.ChatPermissions(
                        can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False
                    ),
                    until_date=until_time if until_time > 0 else int(time.time() + 31536000)
                )
                
                duration = args[1] if (until_time > 0 and len(args) > 1) else "Forever (Until Unmuted)"
                bot.reply_to(m, f"🔇 **Muted**\n\n👤 **User:** {m.reply_to_message.from_user.first_name}\n⏳ **Duration:** {duration}\n📝 **Reason:** {reason}", parse_mode="Markdown")
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
                        can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False
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

@bot.message_handler(commands=['setrules'])
def set_rules(m):
    if is_admin(m):
        txt = m.text.replace('/setrules', '').strip()
        if txt:
            db('INSERT INTO settings (chat_id, rules) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET rules=excluded.rules', (m.chat.id, txt))
            bot.reply_to(m, "✅ Rules Saved.")

@bot.message_handler(commands=['rules'])
def view_rules(m):
    res = db('SELECT rules FROM settings WHERE chat_id=?', (m.chat.id,))
    if res and res[0][0]:
        bot.reply_to(m, f"📋 **Group Rules:**\n\n{res[0][0]}")
    else:
        bot.reply_to(m, "❌ No rules set for this group yet.")

@bot.message_handler(commands=['setwelcome'])
def set_welcome(m):
    if is_admin(m):
        txt = m.text.replace('/setwelcome', '').strip()
        if txt:
            db('INSERT INTO settings (chat_id, welcome) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET welcome=excluded.welcome', (m.chat.id, txt))
            bot.reply_to(m, "✅ Welcome Message Saved.")

@bot.message_handler(commands=['filter'])
def add_filters(m):
    if is_admin(m):
        w = m.text.replace('/filter', '').strip().lower()
        if w: 
            db('INSERT OR REPLACE INTO bl VALUES (?)', (w,))
            bot.reply_to(m, f"Added '{w}' to Filter list.")

@bot.message_handler(func=lambda m: True, content_types=['text', 'sticker', 'new_chat_members', 'left_chat_member'])
def auto_handlers(m):
    if m.chat.type != 'private':
        db('INSERT OR REPLACE INTO groups VALUES (?)', (m.chat.id,))
        if m.from_user and not m.from_user.is_bot:
            db('INSERT OR REPLACE INTO members VALUES (?,?,?)', (m.chat.id, m.from_user.id, m.from_user.first_name))
    else:
        if m.from_user and not m.from_user.is_bot:
            db('INSERT OR REPLACE INTO members VALUES (?,?,?)', (m.chat.id, m.from_user.id, m.from_user.first_name))
    
    if m.content_type == 'new_chat_members':
        res = db('SELECT welcome FROM settings WHERE chat_id=?', (m.chat.id,))
        w_text = res[0][0] if res and res[0][0] else "Welcome {name} to our group! 🎉"
        for new_user in m.new_chat_members:
            if not new_user.is_bot:
                formatted_text = w_text.replace("{name}", new_user.first_name)
                bot.send_message(m.chat.id, formatted_text)
        return

    if m.content_type == 'left_chat_member':
        if not m.left_chat_member.is_bot:
            bot.send_message(m.chat.id, f"Goodbye {m.left_chat_member.first_name}! 👋")
        return

    if m.reply_to_message and not m.from_user.is_bot:
        if m.reply_to_message.content_type == 'text':
            q_text = m.reply_to_message.text.strip().lower()
            if q_text and not q_text.startswith('/'):
                if m.content_type == 'sticker':
                    db('INSERT OR REPLACE INTO memory VALUES (?,?,1)', (q_text, m.sticker.file_id))
                elif m.content_type == 'text':
                    a_text = m.text.strip()
                    if a_text and not a_text.startswith('/'):
                        db('INSERT OR REPLACE INTO memory VALUES (?,?,0)', (q_text, a_text))

    if m.content_type == 'sticker' and not m.from_user.is_bot:
        pass

    if m.content_type != 'text': return
    txt = m.text.strip()

    for row in db('SELECT * FROM bl'):
        if row[0] in txt.lower():
            try: bot.delete_message(m.chat.id, m.message_id)
            except: pass
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
            emo_list = ["👍", "❤️", "🔥", "🎉", "👏", "🤔", "😂", "🥰", "⚡"]
            bot.set_message_reaction(m.chat.id, m.message_id, [telebot.types.ReactionTypeEmoji(emoji=random.choice(emo_list))])
        except: 
            pass

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
        
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            time.sleep(5)
                
