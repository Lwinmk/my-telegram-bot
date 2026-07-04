import telebot
import sqlite3
import threading
import os
from flask import Flask

app = Flask('')
@app.route('/')
def home():
    return "Rain Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- TOKEN ထည့်ပြီးပါပြီ ---
API_TOKEN = '8666581291:AAEJgXWQUwsOdO0yT4-AFEqIj73z7arnrCM'  
bot = telebot.TeleBot(API_TOKEN)

# --- DATABASE SYSTEM ---
DB_PATH = os.path.join(os.path.dirname(__file__), 'rain_bot.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS filters (keyword TEXT PRIMARY KEY, reply TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()
init_db()

def db_action(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetchone: res = cursor.fetchone()
    elif fetchall: res = cursor.fetchall()
    conn.commit()
    conn.close()
    return res

def is_admin(message):
    try:
        status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return status in ['creator', 'administrator']
    except:
        return False

# --- COMMANDS ---
def set_bot_commands():
    try:
        commands = [
            telebot.types.BotCommand("start", "Rain Bot ကို စတင်အသုံးပြုရန်"),
            telebot.types.BotCommand("all", "Group ထဲရှိ လူအားလုံးကို Mention ခေါ်ရန်"),
            telebot.types.BotCommand("word", "ရိုင်းစိုင်းသော စကားလုံး ပိတ်ရန်"),
            telebot.types.BotCommand("unword", "ပိတ်ထားသော စကားလုံး ပြန်ဖွင့်ရန်"),
            telebot.types.BotCommand("filter", "စကားလုံး Auto ပြန်ဖြေရန်"),
            telebot.types.BotCommand("stop", "Filter ဖျက်ရန်")
        ]
        bot.set_my_commands(commands)
    except: pass

@bot.message_handler(commands=['start', 'help'])
def send_help(message):
    bot.reply_to(message, "👋 Rain Bot အဆင်သင့်ဖြစ်ပါပြီ။ Admin များအတွက် Commands များ - /word, /unword, /filter, /all")

@bot.message_handler(commands=['word'])
def add_bad_word(message):
    if is_admin(message):
        word = message.text.replace('/word', '').strip().lower()
        if word:
            db_action('INSERT OR REPLACE INTO bad_words (word) VALUES (?)', (word,))
            bot.reply_to(message, f"🚫 စကားလုံး *'{word}'* ကို တားမြစ်လိုက်ပါပြီ။")

@bot.message_handler(commands=['unword'])
def remove_bad_word(message):
    if is_admin(message):
        word = message.text.replace('/unword', '').strip().lower()
        if word:
            db_action('DELETE FROM bad_words WHERE word=?', (word,))
            bot.reply_to(message, f"✅ စကားလုံး *'{word}'* ကို ပြန်ဖွင့်ပေးလိုက်ပါပြီ။")

@bot.message_handler(commands=['all'])
def mention_all(message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        text = "📢 **Attention Everyone!**\n" + "".join([f"[{a.user.first_name}](tg://user?id={a.user.id}) " for a in admins if not a.user.is_bot])
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except: bot.reply_to(message, "❌ မရပါဘူး။")

@bot.message_handler(commands=['filter'])
def add_filter(message):
    if is_admin(message):
        args = message.text.replace('/filter', '').strip().split(' ', 1)
        if len(args) == 2:
            db_action('INSERT OR REPLACE INTO filters (keyword, reply) VALUES (?, ?)', (args[0].lower(), args[1]))
            bot.reply_to(message, f"✅ *{args[0]}* ရိုက်ရင် *{args[1]}* ဟု ပြန်ပါမည်။")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = (message.text or "").lower()
    
    # Bad Words Check
    blocked = db_action('SELECT word FROM bad_words', fetchall=True)
    if blocked:
        for row in blocked:
            if row[0] in text:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    return
                except: pass

    # Filter Check
    res = db_action('SELECT reply FROM filters WHERE keyword=?', (text,), fetchone=True)
    if res: bot.reply_to(message, res[0])

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.remove_webhook()
    set_bot_commands()
    bot.infinity_polling(skip_pending=True)
    
