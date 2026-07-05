import telebot
import sqlite3
import threading
import os
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "Rain Bot is fully active!"
def run_flask(): app.run(host='0.0.0.0', port=8080)

# --- BOT TOKEN ---
API_TOKEN = '8666581291:AAEJgXWQUwsOdO0yT4-AFEqIj73z7arnrCM'
bot = telebot.TeleBot(API_TOKEN)
DB_PATH = 'rain_bot_global.db'

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS memory (q TEXT PRIMARY KEY, a TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS blacklist (word TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS members (chat_id INTEGER, user_id INTEGER, name TEXT, PRIMARY KEY(chat_id, user_id))')
    # 📢 Group Chat IDs များကို မှတ်ရန် Table အသစ် 📢
    c.execute('CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()
init_db()

def db_action(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchone() if fetchone else (c.fetchall() if fetchall else None)
    conn.commit()
    conn.close()
    return res

def is_admin(m):
    try: 
        if m.chat.type == 'private': return True
        return bot.get_chat_member(m.chat.id, m.from_user.id).status in ['creator', 'administrator']
    except: return False

# --- COMMANDS ---
def set_cmds():
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("start", "Rain Bot ကို စတင်ရန် 🚀"),
            telebot.types.BotCommand("addbl", "ဆဲစာလုံးပိတ်ရန် /addbl [စာ] 🚫"),
            telebot.types.BotCommand("rmbl", "ဆဲစာလုံးပြန်ဖွင့်ရန် /rmbl [စာ] 🔊"),
            telebot.types.BotCommand("all", "Group ရှိ လူအားလုံးကို Tag ခေါ်ရန် (Admin သာ) 📢"),
            telebot.types.BotCommand("warn", "အဖွဲ့ဝင်ကို သတိပေးရန် ⚠️")
        ])
    except: pass

@bot.message_handler(commands=['start'])
def help_cmd(m):
    bot.reply_to(m, "👋 Rain Bot အဆင်သင့်ဖြစ်ပါပြီဗျာ။\n\n🤖 `မေးခွန်း : အဖြေ` ပုံစံနဲ့ သင်ပေးထားရင် ဘယ် Group မှာမဆို အော်တို ဝင်ဖြေပေးမှာ ဖြစ်ပါတယ်!")

# 📢 🌟 🌟 🌟 BROADCAST SYSTEM (ကြော်ငြာထည့်မည့်စနစ်) 🌟 🌟 🌟 📢
# Bot ထဲမှာ /broadcast [စာသား] ဟု ရိုက်၍ သုံးရပါမည်။
@bot.message_handler(commands=['broadcast'])
def broadcast_ad(m):
    if is_admin(m):
        ad_text = m.text.replace('/broadcast', '').strip()
        if not ad_text:
            bot.reply_to(m, "⚠️ သုံးနည်း - `/broadcast [မင်းထည့်ချင်တဲ့ ကြော်ငြာစာ]` ဟု ရိုက်ပါဗျာ။")
            return
            
        # ဘော့ရှိနေတဲ့ Group ID အကုန်လုံးကို Database ထဲက ဆွဲထုတ်မယ်
        group_list = db_action('SELECT chat_id FROM groups', fetchall=True)
        
        if not group_list:
            bot.reply_to(m, "⚠️ ဘော့ထဲမှာ မှတ်ထားတဲ့ Group စာရင်း မရှိသေးပါဘူးဗျာ။ (ဘော့ရှိတဲ့ Group ထဲ လူတွေစာရိုက်ရင် Auto မှတ်သွားပါလိမ့်မယ်။)")
            return
            
        success_count = 0
        for row in group_list:
            try:
                bot.send_message(row[0], f"📢 **[ကြော်ငြာစာစောင်]**\n\n{ad_text}")
                success_count += 1
            except:
                pass
                
        bot.reply_to(m, f"✅ Group ပေါင်း ({success_count}) ခုဆီကို ကြော်ငြာ ပို့ပေးလိုက်ပါပြီဗျာ။")

@bot.message_handler(commands=['addbl'])
def add_bl(m):
    if is_admin(m):
        word = m.text.replace('/addbl', '').strip().lower()
        if word:
            db_action('INSERT OR REPLACE INTO blacklist (word) VALUES (?)', (word,))
            bot.reply_to(m, f"🚫 '{word}' ကို ပိတ်လိုက်ပါပြီ။")

@bot.message_handler(commands=['rmbl'])
def rm_bl(m):
    if is_admin(m):
        word = m.text.replace('/rmbl', '').strip().lower()
        if word:
            db_action('DELETE FROM blacklist WHERE word=?', (word,))
            bot.reply_to(m, f"✅ '{word}' ကို ပြန်ဖွင့်ပေးလိုက်ပါပြီ။")

@bot.message_handler(commands=['all'])
def tag_all_members(m):
    if is_admin(m):
        if m.chat.type == 'private': return
        rows = db_action('SELECT user_id, name FROM members WHERE chat_id=?', (m.chat.id,), fetchall=True)
        if not rows:
            bot.reply_to(m, "📢 **Attention Everyone!**\n\n⚠️ လူစာရင်းမရှိသေးပါ။")
            return
        mention_text = "📢 **Attention Everyone!**\n\n"
        chunk_size = 50
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i+chunk_size]
            tags = [f"[{name}](tg://user?id={user_id})" for user_id, name in chunk]
            bot.send_message(m.chat.id, mention_text + " ".join(tags), parse_mode="Markdown")

@bot.message_handler(commands=['warn'])
def warn_cmd(m):
    if is_admin(m) and m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        row = db_action('SELECT count FROM warns WHERE chat_id=? AND user_id=?', (m.chat.id, uid), fetchone=True)
        count = (row[0] if row else 0) + 1
        if count >= 3:
            try: bot.ban_chat_member(m.chat.id, uid); bot.reply_to(m, "🚨 Kick ထုတ်လိုက်ပါပြီ။")
            except: pass
        else:
            db_action('INSERT OR REPLACE INTO warns (chat_id, user_id, count) VALUES (?, ?, ?)', (m.chat.id, uid, count))
            bot.reply_to(m, f"⚠️ သတိပေးချက် ({count}/3)")

# --- MAIN LOGIC (Global Learning + Auto Reply + Group & Member Collector) ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'new_chat_members'])
def main_logic(m):
    # Group ID ကို အော်တိုမှတ်သားခြင်း (ကြော်ငြာပို့ရန်အတွက်)
    if m.chat.type != 'private':
        db_action('INSERT OR REPLACE INTO groups (chat_id) VALUES (?)', (m.chat.id,))

    # လူသစ်ဝင်လာရင် နာမည်မှတ်ခြင်း
    if m.content_type == 'new_chat_members':
        for member in m.new_chat_members:
            if not member.is_bot:
                db_action('INSERT OR REPLACE INTO members (chat_id, user_id, name) VALUES (?, ?, ?)', (m.chat.id, member.id, member.first_name))
        return

    # ပုံမှန်စာရိုက်သူများကို မှတ်ခြင်း
    if m.chat.type != 'private' and m.from_user and not m.from_user.is_bot:
        db_action('INSERT OR REPLACE INTO members (chat_id, user_id, name) VALUES (?, ?, ?)', (m.chat.id, m.from_user.id, m.from_user.first_name))

    text = (m.text or "").strip()
    
    # ၁။ Bad Words Check
    bls = db_action('SELECT word FROM blacklist', fetchall=True)
    if bls:
        for row in bls:
            if row[0] in text.lower():
                try: bot.delete_message(m.chat.id, m.message_id)
                except: pass
                return

    # ၂။ Global Learning (မေးခွန်း : အဖြေ) - နေရာလွတ်နှင့် စာလုံးကြီးသေး အမှားနည်းအောင် ပြင်ဆင်ထားသည်
    if ":" in text:
        parts = text.split(":", 1)
        q = parts[0].strip().lower()
        a = parts[1].strip()
        if q and a:
            db_action('INSERT OR REPLACE INTO memory (q, a) VALUES (?, ?)', (q, a))
            bot.reply_to(m, f"✅ သင်ပေးတာ မှတ်ထားလိုက်ပြီဗျာ!\n\n💡 စမ်းသပ်ရန် - `{q}` ဟု ရိုက်ကြည့်ပါ။")
            return

    # ၃။ Global Auto Reply - အောက်က စာလုံးအကြီးအသေး သေချာစစ်အောင် .lower() ထည့်ထားသည်
    res = db_action('SELECT a FROM memory WHERE q=?', (text.lower(),), fetchone=True)
    if res: 
        bot.reply_to(m, res[0])

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.remove_webhook()
    set_cmds()
    bot.infinity_polling(skip_pending=True)
    
