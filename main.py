import requests
import json
import os
import asyncio
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN_BOT = os.environ.get("TOKEN_BOT")
CHAT_ID = os.environ.get("CHAT_ID")
CHECK_INTERVAL = 15
MT_STATUS_FILE = "mt_status.json"

def get_pairs():
    url = "https://indodax.com/api/pairs"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def load_last_status():
    if os.path.exists(MT_STATUS_FILE):
        with open(MT_STATUS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_last_status(data):
    with open(MT_STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def send_telegram(text):
    bot = Bot(token=TOKEN_BOT)
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

async def maintenance_loop():
    print("🚀 Indodax Maintenance Notifier started.")
    last_status = load_last_status()
    while True:
        try:
            pairs = get_pairs()
            mt_now = {}
            for pair in pairs:
                symbol = pair["symbol"]
                is_mt = int(pair.get("is_maintenance", 0))
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                prev = last_status.get(symbol, 0)
                if isinstance(prev, dict):
                    prev_status = prev.get("status", 0)
                else:
                    prev_status = prev

                if is_mt == 1 and prev_status != 1:
                    msg = f"⚠️ <b>{symbol}</b> masuk maintenance pada {now}"
                    print(msg)
                    await send_telegram(msg)
                    mt_now[symbol] = {"status": 1, "since": now}
                elif is_mt == 0 and prev_status == 1:
                    msg = f"✅ <b>{symbol}</b> keluar dari maintenance pada {now}"
                    print(msg)
                    await send_telegram(msg)
                elif is_mt == 1 and prev_status == 1:
                    mt_now[symbol] = last_status[symbol]
            save_last_status(mt_now)
            last_status = mt_now
        except Exception as e:
            print(f"❌ Error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(MT_STATUS_FILE):
        await update.message.reply_text("Belum ada data maintenance. Jalankan monitor dulu.")
        return
    with open(MT_STATUS_FILE, "r") as f:
        mt_last = json.load(f)
    koin_mt = [
        (symbol, info.get('since', '-')) 
        for symbol, info in mt_last.items()
        if (isinstance(info, dict) and info.get("status") == 1)
    ]
    if not koin_mt:
        await update.message.reply_text("Tidak ada koin yang sedang maintenance.")
        return
    koin_mt.sort(key=lambda x: x[1])
    pesan = "Koin yang sedang maintenance:\n"
    for nomor, (symbol, since) in enumerate(koin_mt, 1):
        pesan += f"{nomor}. {symbol} (sejak {since})\n"
    await update.message.reply_text(pesan)

async def main():
    app = ApplicationBuilder().token(TOKEN_BOT).build()
    app.add_handler(CommandHandler("maintenance", maintenance_command))
    asyncio.create_task(maintenance_loop())
    print("Bot Telegram siap. Kirim /maintenance ke bot untuk cek koin maintenance.")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    asyncio.run(main())
