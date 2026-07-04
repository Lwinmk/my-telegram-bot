import telebot
import sqlite3
import threading
from flask import Flask

app = Flask('')
@app.route('/')
def home():
    return "Rain Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

API_TOKEN = '8666581291:AAEJgXWQUwsOdO0yT4-AFEqIj73z7arnrCM'  
bot = telebot.TeleBot(API_TOKEN)

# --- DATABASE SYSTEM ---
def init_db():
    conn = sqlite3.connect('rain_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS filters (keyword TEXT PRIMARY KEY, reply TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    # 🌟 ရိုင်းစိုင်းသော စကားလုံးများ သိမ်းရန် Table အသစ် 🌟
    cursor.execute('CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()
init_db()

def db_action(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect('rain_bot.db')
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

# --- AUTO COMMANDS MENU SET ---
def set_bot_commands():
    try:
        commands = [
            telebot.types.BotCommand("start", "Rain Bot ကို စတင်အသုံးပြုရန် 🚀"),
            telebot.types.BotCommand("help", "အသုံးပြုနိုင်သော Commands များ ကြည့်ရန် ℹ️"),
            telebot.types.BotCommand("all", "Group ထဲရှိ လူအားလုံးကို Mention (Tag) ခေါ်ရန် 📢"),
            telebot.types.BotCommand("rules", "Group ရဲ့ စည်းကမ်းချက်များကို ကြည့်ရန် 📋"),
            telebot.types.BotCommand("setrules", "Group စည်းကမ်းချက် သတ်မှတ်ရန် (Admin သာ) 🛡️"),
            telebot.types.BotCommand("setwelcome", "အဖွဲ့ဝင်သစ် ကြိုဆိုစာ သတ်မှတ်ရန် (Admin သာ) ⚙️"),
            telebot.types.BotCommand("word", "ရိုင်းစိုင်းသော စကားလုံး ပိတ်ရန် /word [စာလုံး] 🚫"),
            telebot.types.BotCommand("unword", "ပိတ်ထားသော စကားလုံး ပြန်ဖွင့်ရန် /unword [စာလုံး] 🔊"),
            telebot.types.BotCommand("filter", "စကားလုံး Auto ပြန်ဖြေမည့်စနစ် ထည့်ရန် 💬"),
            telebot.types.BotCommand("stop", "သတ်မှတ်ထားသော Filter ကို ပြန်ဖျက်ရန် ❌")
        ]
        bot.set_my_commands(commands)
    except Exception as e:
        print(f"Failed to set bot commands: {e}")

# --- 🌟 BAD WORD MANAGEMENT COMMANDS (မင်းအခုလိုချင်တဲ့စနစ်) 🌟 ---

# သုံးနည်း - /word fuck
@bot.message_handler(commands=['word'])
def add_bad_word(message):
    if is_admin(message):
        word_to_block = message.text.replace('/word', '').strip().lower()
        if not word_to_block:
            bot.reply_to(message, "⚠️ သုံးနည်း - `/word [တားမြစ်ချင်တဲ့စာလုံး]` ဟု ရိုက်ပါဗျာ။", parse_mode="Markdown")
            return
        
        db_action('INSERT OR REPLACE INTO bad_words (word) VALUES (?)', (word_to_block,))
        bot.reply_to(message, f"🚫 စကားလုံး *'{word_to_block}'* ကို တားမြစ်စာရင်းထဲ ထည့်လိုက်ပါပြီ။ ရေးလာရင် Auto ဖျက်ပါမယ်။", parse_mode="Markdown")

# သုံးနည်း - /unword fuck
@bot.message_handler(commands=['unword'])
def remove_bad_word(message):
    if is_admin(message):
        word_to_remove = message.text.replace('/unword', '').strip().lower()
        if not word_to_remove:
            bot.reply_to(message, "⚠️ သုံးနည်း - `/unword [ပြန်ဖွင့်ချင်တဲ့စာလုံး]` ဟု ရိုက်ပါဗျာ။", parse_mode="Markdown")
            return
        
        db_action('DELETE FROM bad_words WHERE word=?', (word_to_remove,))
        bot.reply_to(message, f"✅ စကားလုံး *'{word_to_remove}'* ကို တားမြစ်စာရင်းထဲကနေ ပြန်ဖျက်ပေးလိုက်ပါပြီ။", parse_mode="Markdown")

# --- OTHER COMMANDS ---
@bot.message_handler(commands=['start', 'help'])
def send_help(message):
    help_text = (
        "👋 *Rain Bot မှ ကြိုဆိုပါတယ်ဗျာ!*\n\n"
        "🤖 *အသုံးပြုနိုင်သော Commands များ-*\n"
        "• `/word [စာလုံး]` - ရိုင်းစိုင်းသော စကားလုံး အသစ်ပိတ်ရန် 🚫\n"
        "• `/unword [စာလုံး]` - ပိတ်ထားသော စကားလုံး ပြန်ဖွင့်ရန် 🔊\n"
        "• `/all` - Group ထဲရှိ လူအားလုံးကို Mention ခေါ်ရန် 📢\n"
        "• `/rules` - စည်းကမ်းများ ကြည့်ရန် 📋\n"
        "• `/setrules [စာ]` - စည်းကမ်း သတ်မှတ်ရန် 🛡️\n"
        "• `/setwelcome [စာ]` - ကြိုဆိုစာ သတ်မှတ်ရန် ⚙️\n"
        "• `/filter [စကားလုံး] [ပြန်စာ]` - Filter ထည့်ရန် 💬\n"
        "• `/stop [စာလုံး]` - Filter ဖျက်ရန် ❌\n"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['all'])
def mention_all_users(message):
    try:
        chat_id = message.chat.id
        admins = bot.get_chat_administrators(chat_id)
        mention_text = "📢 **Attention Everyone!**\n\n"
        for admin in admins:
            if not admin.user.is_bot:
                mention_text += f"[{admin.user.first_name}](tg://user?id={admin.user.id}) "
        if message.reply_to_message:
            bot.reply_to(message.reply_to_message, mention_text, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, mention_text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Mention ခေါ်လို့မရပါဘူး။ အကြောင်းရင်း - {e}")

@bot.message_handler(commands=['setwelcome'])
def set_welcome(message):
    text = message.text.replace('/setwelcome', '').strip()
    if text:
        db_action('INSERT OR REPLACE INTO settings (key, value) VALUES ("welcome", ?)', (text,))
        bot.reply_to(message, "✅ Welcome message သတ်မှတ်ပြီးပါပြီ။")

@bot.message_handler(commands=['setrules'])
def set_rules(message):
    text = message.text.replace('/setrules', '').strip()
    if text:
        db_action('INSERT OR REPLACE INTO settings (key, value) VALUES ("rules", ?)', (text,))
        bot.reply_to(message, "✅ Group rules သတ်မှတ်ပြီးပါပြီ။")

@bot.message_handler(commands=['rules'])
def get_rules(message):
    res = db_action('SELECT value FROM settings WHERE key="rules"', fetchone=True)
    bot.reply_to(message, f"📋 *Group Rules*:\n\n{res[0] if res else 'စည်းကမ်းချက်များ မရှိသေးပါ။'}", parse_mode="Markdown")

@bot.message_handler(commands=['filter'])
def add_filter(message):
    args = message.text.replace('/filter', '').strip().split(' ', 1)
    if len(args) == 2:
        db_action('INSERT OR REPLACE INTO filters (keyword, reply) VALUES (?, ?)', (args[0].lower(), args[1]))
        bot.reply_to(message, f"✅ Added filter for: *{args[0]}*", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop_filter(message):
    keyword = message.text.replace('/stop', '').strip().lower()
    if keyword:
        db_action('DELETE FROM filters WHERE keyword=?', (keyword,))
        bot.reply_to(message, f"❌ Stopped filtering for: *{keyword}*", parse_mode="Markdown")

# --- MESSAGE HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_text = message.text or ""
    
    # 🌟 ချက်ချင်းစစ်ဆေးခြင်း - Database ထဲက ပိတ်ထားတဲ့ စကားလုံးတွေ ပါလာလား စစ်မယ် 🌟
    blocked_words = db_action('SELECT word FROM bad_words', fetchall=True)
    if blocked_words:
        for row in blocked_words:
            bad_word = row[0]
            if bad_word in user_text.lower():
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    warning_msg = bot.send_message(message.chat.id, f"⚠️ {message.from_user.first_name} ရေ... Group ထဲမှာ ပိတ်ထားတဲ့ စကားလုံး သုံးလို့ မရပါဘူးဗျာ။")
                    threading.Timer(5.0, lambda: bot.delete_message(message.chat.id, warning_msg.message_id)).start()
                    return
                except:
                    pass

    # စကားလုံး Filter စနစ်
    filter_res = db_action('SELECT reply FROM filters WHERE keyword=?', (user_text.lower(),), fetchone=True)
    if filter_res:
        bot.reply_to(message, filter_res[0])

@bot.message_handler(content_types=['new_chat_members'])
def greeting(message):
    res = db_action('SELECT value FROM settings WHERE key="welcome"', fetchone=True)
    welcome = res[0] if res else "Welcome!"
    for member in message.new_chat_members:
        bot.send_message(message.chat.id, f"👋 Hello {member.first_name}, {welcome}")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    set_bot_commands()
    bot.infinity_polling()
                                     
