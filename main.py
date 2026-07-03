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
API_TOKEN = '8666581291:AAEJgXWQUwsOdO0yT4-AFEqIj73z7arnrCM'  
bot = telebot.TeleBot(API_TOKEN)

# --- DATABASE SYSTEM ---
def init_db():
    conn = sqlite3.connect('rose_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS knowledge (question TEXT PRIMARY KEY, answer TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS filters (keyword TEXT PRIMARY KEY, reply TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, chat_id INTEGER, count INTEGER, PRIMARY KEY (user_id, chat_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT)')
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

# --- NEW /START & HELP COMMAND LIST ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome_and_commands(message):
    if not message.from_user.is_bot:
        db_action('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)', 
                  (message.from_user.id, message.from_user.username, message.from_user.first_name))
        
    help_text = (
        f"👋 **မင်္ဂလာပါ {message.from_user.first_name} ရေ...**\n"
        "ကျွန်တော်ကတော့ Group မန်နေဂျာ Rose Bot ဖြစ်ပါတယ်ဗျာ။ ✨\n\n"
        "🤖 **အသုံးပြုနိုင်သော Commands များ စာရင်း-**\n\n"
        "ℹ️ **အထွေထွေသုံးရန်-**\n"
        "• `/start` သို့မဟုတ် `/help` - ဤလမ်းညွှန်ချက်ကို ကြည့်ရန်\n"
        "• `/rules` - Group ရဲ့ စည်းကမ်းချက်များကို ကြည့်ရန်\n"
        "• `/all` - Group ထဲရှိ လူအားလုံးကို Attention ပေးရန်\n\n"
        "🛡️ **Admin များအတွက်သာ (Group စီမံခန့်ခွဲရန်)-**\n"
        "• `/setrules [စာသား]` - Group စည်းကမ်းချက် သတ်မှတ်ရန်\n"
        "• `/setwelcome [စာသား]` - အဖွဲ့ဝင်သစ် ကြိုဆိုစာ သတ်မှတ်ရန်\n"
        "• `/ban` - (Reply ပေးပြီးသုံးရန်) လူကို အပြီးပိတ်ပစ်ရန်\n"
        "• `/kick` - (Reply ပေးပြီးသုံးရန်) လူကို Group ထဲက မောင်းထုတ်ရန်\n"
        "• `/mute` - (Reply ပေးပြီးသုံးရန်) လူကို စာရိုက်ခွင့် ပိတ်ရန်\n"
        "• `/unmute` - (Reply ပေးပြီးသုံးရန်) စာရိုက်ခွင့် ပြန်ဖွင့်ပေးရန်\n"
        "• `/warn` - (Reply ပေးပြီးသုံးရန်) သတိပေးရန် (၃ ကြိမ်ပြည့်လျှင် Auto Ban)\n"
        "• `/pin` - (Reply ပေးပြီးသုံးရန်) စာကို Pin ချိတ်ထားရန်\n\n"
        "⚙️ **စကားလုံး Filter & Auto Learn စနစ်-**\n"
        "• `/filter [စကားလုံး] [ပြန်ဖြေမည့်စာ]` - ၎င်းစာလုံးရိုက်ရင် Auto စာပြန်ခိုင်းရန်\n"
        "• `/stop [စကားလုံး]` - သတ်မှတ်ထားသော Filter ကို ပြန်ဖျက်ရန်\n\n"
        "📢 **ပိုင်ရှင် / Admin အတွက် စာဖြန့်ဝေခြင်း-**\n"
        "• `/broadcast [ပို့ချင်တဲ့စာ]` - Bot ကိုသုံးဖူးသမျှ လူအကုန်လုံးဆီသို့ တစ်ပြိုင်နက် Auto စာလှမ်းပို့ရန်\n"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

# --- AUTO BROADCAST TO ALL USERS ---
@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if is_admin(message):
        text_to_send = message.text.replace('/broadcast', '').strip()
        if not text_to_send:
            bot.reply_to(message, "⚠️ သုံးနည်း - `/broadcast [ပို့ချင်တဲ့စာ]` လို့ ရိုက်ပါဗျာ။", parse_mode="Markdown")
            return
            
        all_users = db_action('SELECT user_id FROM users', fetchall=True)
        if not all_users:
            bot.reply_to(message, "❌ Database ထဲမှာ စာပို့စရာ User တစ်ယောက်မှ မရှိသေးပါဘူး။")
            return
            
        success_count = 0
        fail_count = 0
        
        for user in all_users:
            try:
                bot.send_message(user[0], text_to_send)
                success_count += 1
            except:
                fail_count += 1
                
        bot.reply_to(message, f"📢 **Broadcast ဖြန့်ဝေပြီးပါပြီ။**\n\n✅ အောင်မြင် - {success_count} ဦး\n❌ ကျရှုံး - {fail_count} ဦး", parse_mode="Markdown")

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

# --- 🌟 ONE AND ONLY ALL-MESSAGE HANDLER (AUTO SPAM & AUTO-LEARNING & USER DB LOG) 🌟 ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    # စာလာရိုက်သူကို Database ထဲ Auto မှတ်မယ်
    if not message.from_user.is_bot:
        db_action('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)', 
                  (message.from_user.id, message.from_user.username, message.from_user.first_name))

    # Render Logs မှာ လှမ်းပြမယ်
    print(f"[💬 Message] From: {message.from_user.first_name} (ID: {message.from_user.id}) | Text: {message.text}")

    user_text = message.text or ""
    
    # Auto Spam Link Filter
    if "http" in user_text.lower() or "t.me/" in user_text.lower():
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.restrict_chat_member(message.chat.id, message.from_user.id, permissions=telebot.types.ChatPermissions(can_send_messages=False))
            bot.send_message(message.chat.id, f"⚠️ {message.from_user.first_name} was auto-muted for sending links.")
            return
        except: pass

    # Word Filter
    filter_res = db_action('SELECT reply FROM filters WHERE keyword=?', (user_text.lower(),), fetchone=True)
    if filter_res:
        bot.reply_to(message, filter_res[0])
        return

    # Auto Learn & Reply System
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
    threading.Thread(target=run_flask).start()
    print("[🚀] Server & Bot are running perfectly...")
    bot.infinity_polling()
