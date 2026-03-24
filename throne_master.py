import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
import time
import json
import os

# --- KONFIGURASI TELEGRAM ---
# Menghapus spasi pada token jika ada
TOKEN = '8710550128:AAFmR0WHZplvyJquXAfrcIiTHcOkzxSNvnA'.replace(" ", "")
MY_ID = 5828061077
bot = telebot.TeleBot(TOKEN)

# --- KONFIGURASI FIRESTORE (CLOUD) ---
APP_ID = "euforia-9b0bf"

db = None
if not firebase_admin._apps:
    try:
        if os.path.exists("cloud_config.json"):
            with open("cloud_config.json", "r") as f:
                cert_data = json.load(f)
            
            if cert_data.get("type") == "service_account":
                cred = credentials.Certificate(cert_data)
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                print("✅ Firebase initialized successfully.")
            else:
                print("❌ Error: cloud_config.json format invalid.")
        else:
            print("❌ Error: cloud_config.json not found!")
    except Exception as e:
        print(f"❌ Gagal inisialisasi Firebase: {e}")
else:
    db = firestore.client()

if db:
    coll_ref = db.collection('artifacts', APP_ID, 'public', 'data', 'workers')

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
        bot.reply_to(message, "👑 **Master Throne Cloud v2.7**\nStatus: Online & Sync Polling Fixed", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.from_user.id != MY_ID: return
    if not db:
        bot.answer_callback_query(call.id, "Error: Database disconnected.")
        return
    
    if call.data == "status_all":
        try:
            docs = coll_ref.get()
            if not docs:
                bot.send_message(call.message.chat.id, "Belum ada laporan dari PC target.")
                return
            
            for doc in docs:
                data = doc.to_dict()
                node_id = doc.id
                
                try:
                    last_seen_raw = data.get('last_seen', 0)
                    last_seen = float(last_seen_raw)
                except (ValueError, TypeError):
                    last_seen = 0
                
                status_icon = "✅" if (time.time() - last_seen) < 300 else "❌"
                mining_status = data.get('mining_status', 'Unknown')
                
                row = types.InlineKeyboardMarkup()
                row.add(types.InlineKeyboardButton(f"🚀 Start", callback_data=f"single_start_{node_id}"),
                        types.InlineKeyboardButton(f"🛑 Stop", callback_data=f"single_stop_{node_id}"))
                
                bot.send_message(call.message.chat.id, 
                                 f"{status_icon} **Device: {node_id}**\nStatus: `{mining_status}`", 
                                 reply_markup=row, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"⚠️ Error: {e}")

    elif call.data == "all_start":
        set_global_command("START")
        bot.answer_callback_query(call.id, "START massal terkirim.")
    elif call.data == "all_stop":
        set_global_command("STOP")
        bot.answer_callback_query(call.id, "STOP massal terkirim.")
    elif call.data.startswith("single_"):
        p = call.data.split("_")
        if set_command(p[2], p[1].upper()):
            bot.answer_callback_query(call.id, f"{p[1].upper()} dikirim.")

if __name__ == "__main__":
    print("--- Throne Master Online ---")
    
    while True:
        try:
            # 1. Pastikan instansi lama terputus
            print("🧹 Membersihkan session (remove_webhook)...")
            bot.remove_webhook()
            time.sleep(2)
            
            # 2. Gunakan infinity_polling dengan restart_on_change=False 
            # untuk menghindari penggunaan 'threaded' argumen yang bermasalah
            print("🚀 Memulai polling (v2.7)...")
            bot.infinity_polling(timeout=60, long_polling_timeout=5)
            
        except Exception as e:
            error_msg = str(e)
            if "Conflict" in error_msg or "409" in error_msg:
                print("⚠️ Conflict 409 terdeteksi. Menunggu 15 detik...")
                time.sleep(15)
            else:
                print(f"❌ Polling Error: {e}")
                time.sleep(5)
