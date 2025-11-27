import telebot
import requests
import time
import threading
import json
import os

CONFIG_FILE = "config.json"
DATA_FILE = "nodes.json"

# --- ЗАВАНТАЖЕННЯ КОНФІГУ ---
def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(new_config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(new_config, f, indent=4)

config = load_config()
BOT_TOKEN = config['token']
OWNER_ID = int(config['owner_id'])

bot = telebot.TeleBot(BOT_TOKEN)

# --- ЗАВАНТАЖЕННЯ/ЗБЕРЕЖЕННЯ СПИСКУ НОД ---
def load_nodes():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_nodes(nodes):
    with open(DATA_FILE, 'w') as f:
        json.dump(nodes, f, indent=4)

nodes = load_nodes()

# --- ПЕРЕВІРКА НОДИ (ФУНКЦІЯ) ---
def check_node(ip):
    try:
        url = f"http://{ip}/status"
        response = requests.get(url, timeout=3)
        data = response.json()
        
        moniker = data['result']['node_info']['moniker']
        catching_up = data['result']['sync_info']['catching_up']
        height = data['result']['sync_info']['latest_block_height']
        
        return {
            "status": "ok",
            "moniker": moniker,
            "height": height,
            "catching_up": catching_up
        }
    except:
        return {"status": "error"}

# --- КОМАНДИ БОТА ---
# --- ОНОВЛЕНИЙ ОБРОБНИК /START ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    global OWNER_ID
    
    welcome_message = (
        "👋 Вітаю! Я Ваш Stable Node Monitor Bot.\n\n"
        "🛠 *Доступні команди:*\n"
        "`/add` IP Назва  — Додати ноду \n"
        "`/del` IP        — Видалити ноду\n"
        "`/list`          — Показати список нод\n"
        "`/check`         — Перевірити статус зараз\n\n"
        "--- *Статус* ---\n"
        "🟢 *Synced* — Нода повністю синхронізована.\n"
        "🟡 *Catching Up* — Нода наздоганяє мережу.\n"
        "🔴 *OFFLINE / ERR* — Нода не відповідає або вимкнена."
    )
    
    # ЛОГІКА АВТО-РЕЄСТРАЦІЇ ВЛАСНИКА
    if OWNER_ID == 0:
        OWNER_ID = message.chat.id
        config['owner_id'] = OWNER_ID
        save_config(config)
        bot.reply_to(message, f"🎉 **Вітаю! Ви успішно авторизовані як власник.**\n\n{welcome_message}", parse_mode="Markdown")
        return

    # Якщо пише чужа людина
    if message.chat.id != OWNER_ID:
        bot.reply_to(message, "⛔️ Це приватний бот. Доступ заборонено.")
        return

    # Якщо власник пише /start вдруге
    bot.reply_to(message, welcome_message, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_node(message):
    if OWNER_ID == 0 or message.chat.id != OWNER_ID: return
    try:
        parts = message.text.split()
        ip = parts[1]

        if ":" not in ip: ip += ":26657"
        
        name = " ".join(parts[2:]) if len(parts) > 2 else ip
        
        nodes[ip] = name
        save_nodes(nodes)
        bot.reply_to(message, f"✅ Ноду {name} ({ip}) додано до моніторингу!")
    except:
        bot.reply_to(message, "⚠️ Формат: /add IP Назва")

@bot.message_handler(commands=['del'])
def delete_node(message):
    if OWNER_ID == 0 or message.chat.id != OWNER_ID: return
    try:
        ip = message.text.split()[1]
        if ":" not in ip: ip += ":26657"
        
        if ip in nodes:
            del nodes[ip]
            save_nodes(nodes)
            bot.reply_to(message, f"🗑 Ноду {ip} видалено.")
        else:
            bot.reply_to(message, "❌ Такої ноди немає в списку.")
    except:
        bot.reply_to(message, "⚠️ Формат: /del IP")

@bot.message_handler(commands=['list'])
def list_nodes(message):
    if OWNER_ID == 0 or message.chat.id != OWNER_ID: return
    msg = "📋 *Список нод:*\n"
    for ip, name in nodes.items():
        msg += f"`{ip}` - {name}\n"
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['check'])
def force_check(message):
    if OWNER_ID == 0 or message.chat.id != OWNER_ID: return
    bot.reply_to(message, "🔍 Перевіряю всі ноди...")
    report = generate_report()
    bot.send_message(OWNER_ID, report, parse_mode="Markdown")

# --- ГЕНЕРАЦІЯ ЗВІТУ ---
def generate_report():
    if not nodes: return "Список нод порожній."
    
    msg = "📊 *Статус Нод:*\n\n"
    all_ok = True
    
    for ip, name in nodes.items():
        data = check_node(ip)
        
        if data['status'] == 'error':
            msg += f"🔴 *{name}* — OFFLINE / ERR\n"
            all_ok = False
        else:
            status_icon = "🟢" if not data['catching_up'] else "🟡"
            status_text = "Synced" if not data['catching_up'] else "Catching Up"
            msg += f"{status_icon} {name} — {status_text} ({data['height']})\n"
            
    if all_ok: msg += "\n✅ _Всі системи в нормі_"
    else: msg += "\n⚠️ _Є проблеми!_"
    return msg

# --- ФОНОВИЙ МОНІТОРИНГ (Раз в 6 годин) ---
def background_monitor():
    while True:
        time.sleep(21600)

        if OWNER_ID == 0: 
            continue

        report = generate_report()
        try:
            bot.send_message(OWNER_ID, report, parse_mode="Markdown")
        except:
            pass

# --- ЗАПУСК ---
if __name__ == "__main__":
    
    t = threading.Thread(target=background_monitor)
    t.start()
    
    
    print("Bot started...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            time.sleep(15)