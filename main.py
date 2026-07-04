import telebot
import sqlite3
import threading
import os
from flask import Flask

app = Flask('')
@app.route('/')
def home():
    return "Rain Bot is running perfectly!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- မင်းရဲ့ TOKEN ---
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
        if message.chat.type == 'private':
            return True
        status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return status in ['creator', 'administrator']
    except:
        return False

# --- 🌟 BOT COMMANDS LIST AUTO SET SYSTEM (မင်းပြောတဲ့အတိုင်း သန့်ရှင်းရေးလုပ်ထားသည်) 🌟 ---
def set_bot_commands():
    try:
        commands = [
            telebot.types.BotCommand("start", "Rain Bot မှ ကြိုဆိုပါတယ်ဗျာ! ✨")
        ]
        bot.set_my_commands(commands)
    except: pass

# --- COMMAND HANDLERS (START နှိပ်မှ ဒီစာရင်းတွေ ပေါ်လာမည်) ---
@bot.message_handler(commands=['start', 'help'])
def send_help(message):
    help_text = (
        "👋 **Rain Bot မှ ကြိုဆိုပါတယ်ဗျာ!**\n\n"
        "🤖 **အသုံးပြုနိုင်သော Commands များ-**\n"
        "• `/word [စာလုံး]` - ရိုင်းစိုင်းသော စကားလုံး ပိတ်ရန် 🚫\n"
        "• `/unword [စာလုံး]` - ပိတ်ထားသော စကားလုံး ပြန်ဖွင့်ရန် 🔊\n"
        "• `/filter [မေးစာ] [ပြန်စာ]` - စကားလုံး Auto ပြန်ဖြေခိုင်းရန် 💬\n"
        "• `/stop [စာလုံး]` - Filter ပြန်ဖျက်ရန် ❌\n"
        "• `/all` - Group ထဲရှိ လူအားလုံးကို Tag တွဲခေါ်ရန် 📢"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['word'])
def add_bad_word(message):
    if is_admin(message):
        word = message.text.replace('/word', '').strip().lower()
        if word:
            db_action('INSERT OR REPLACE INTO bad_words (word) VALUES (?)', (word,))
            bot.reply_to(message, f"🚫 စကားလုံး *'{word}'* ကို ပိတ်လိုက်ပါပြီ။ ရေးလာရင် Auto ဖျက်ပါမယ်။", parse_mode="Markdown")

@bot.message_handler(commands=['unword'])
def remove_bad_word(message):
    if is_admin(message):
        word = message.text.replace('/unword', '').strip().lower()
        if word:
            db_action('DELETE FROM bad_words WHERE word=?', (word,))
            bot.reply_to(message, f"✅ စကားလုံး *'{word}'* ကို ပြန်ဖွင့်ပေးလိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(commands=['filter'])
def add_filter(message):
    if is_admin(message):
        args = message.text.replace('/filter', '').strip().split(' ', 1)
        if len(args) == 2:
            db_action('INSERT OR REPLACE INTO filters (keyword, reply) VALUES (?, ?)', (args[0].lower(), args[1]))
            bot.reply_to(message, f"✅ Filter ထည့်ပြီးပါပြီ။ *'{args[0]}'* လို့ ရိုက်ရင် *'{args[1]}'* ဟု ပြန်ပါမည်။", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop_filter(message):
    if is_admin(message):
        keyword = message.text.replace('/stop', '').strip().lower()
        if keyword:
            db_action('DELETE FROM filters WHERE keyword=?', (keyword,))
            bot.reply_to(message, f"❌ Filter *'{keyword}'* ကို ဖြုတ်လိုက်ပါပြီ။", parse_mode="Markdown")

@bot.message_handler(commands=['all'])
def mention_all(message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        text = "📢 **Attention Everyone!**\n\n" + "".join([f"[{a.user.first_name}](tg://user?id={a.user.id}) " for a in admins if not a.user.is_bot])
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Tag ခေါ်မရပါ။ အကြောင်းရင်း - {e}")

# --- MESSAGE HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_text = (message.text or "").strip().lower()
    
    # ၁။ Bad Words Filter
    blocked = db_action('SELECT word FROM bad_words', fetchall=True)
    if blocked:
        for row in blocked:
            if row[0] in user_text:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    return
                except: pass

    # ၂။ စကားလုံး Filter စနစ်
    filter_res = db_action('SELECT reply FROM filters WHERE keyword=?', (user_text,), fetchone=True)
    if filter_res:
        bot.reply_to(message, filter_res[0])

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.remove_webhook()
    set_bot_commands()
    print("[🚀] Rain Bot is perfectly running now...")
    bot.infinity_polling(skip_pending=True)
    
