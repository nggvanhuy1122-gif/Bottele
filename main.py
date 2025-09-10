import aiohttp
import json
import random
import string
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import nest_asyncio
import sys

# ===== Apply nest_asyncio cho Acode/Jupyter =====
nest_asyncio.apply()

# ===== CONFIG =====
TOKEN = "8449163202:AAGcUZ4hWHtOES4Y76D9jCrOr1U38OiJMWU"
API_URL = "http://160.191.244.78:9001/api/taixiu/sunwin"
ADMINS = [7598401539, 6937728981, 7004725152]
GROUP_ID = -1002860765460
KEY_FILE = "keys.json"
BOT_ACTIVE = {}   # user_id: True/False
USER_KEYS = {}    # user_id: key

RANDOM_REASONS = [
    "Phân tích lịch sử 3 phiên gần nhất kết hợp 98% chẵn",
    "Dựa trên xu hướng 5 phiên gần đây",
    "Xét tổng điểm và tần suất xuất hiện Tài/Xỉu",
    "Soi cầu theo mô hình đặc biệt của Sunwin",
    "Dựa vào thống kê chẵn/lẻ và số xúc xắc",
    "Phân tích biến động số trước đó và xác suất",
    "Dựa vào các phiên đặc biệt tuần trước",
    "Xem xét kết quả liên tiếp của 2 phiên trước",
]

# ===== HELPER =====
def load_keys():
    try:
        with open(KEY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_keys(keys):
    with open(KEY_FILE, "w") as f:
        json.dump(keys, f, indent=4)

def generate_key(length=12):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def key_valid(key):
    keys = load_keys()
    if key in keys:
        expire = datetime.strptime(keys[key]['expire'], "%Y-%m-%d %H:%M:%S")
        return expire > datetime.now()
    return False

def format_prediction(data):
    session_id = data.get("Phien_hien_tai", "N/A")
    dice = [data.get("Xuc_xac_1","?"), data.get("Xuc_xac_2","?"), data.get("Xuc_xac_3","?")]
    total = data.get("Tong","?")
    result = data.get("Ket_qua","?")
    next_session = data.get("Phien_hien_tai", session_id + 1)
    prediction = data.get("du_doan","?")
    reason = data.get("ly_do") or random.choice(RANDOM_REASONS)

    msg = f"""💎 ♦️ SUNWIN VIP - PHÂN TÍCH CHUẨN XÁC ♦️ 💎
══════════════════════════
🆔 Phiên hiện tại: {session_id}
🎲 Xúc xắc: {dice[0]}-{dice[1]}-{dice[2]}
🧮 Tổng điểm: {total} | Kết quả: {'🔥 Tài' if result=='Tài' else '❄️ Xỉu'}
──────────────────────────
🔮 Dự đoán phiên {next_session}: {'🔥 Tài' if prediction=='Tài' else '❄️ Xỉu'}
🎯 Khuyến nghị: Đặt cược {'🔥 Tài' if prediction=='Tài' else '❄️ Xỉu'}

📶 Xu hướng: {reason}
══════════════════════════
✨ Cre: Ng Văn Huy ✨"""
    return msg

# ===== API CALL =====
async def get_prediction():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ty_le = data.get("ty_le", {})
                    tai_rate = ty_le.get("Tai", 0)
                    xiu_rate = ty_le.get("Xiu", 0)

                    prediction = "Tài" if tai_rate >= xiu_rate else "Xỉu"
                    data["du_doan"] = prediction
                    data["ly_do"] = f"Tỷ lệ: Tài {tai_rate}, Xỉu {xiu_rate}"

                    return data, format_prediction(data)
                return None, f"Lỗi API: {resp.status}"
        except Exception as e:
            return None, f"Lỗi: {str(e)}"

# ===== COMMANDS =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """💎 Chào mừng bạn đến với SUNWIN VIP 💎
══════════════════════════
🔑 Nhập key bạn đã nhận từ admin:
👉 /key <key>

📌 Các lệnh khác:
/checkkey - Kiểm tra key còn hạn không
/chaybot - Bật dự đoán tự động
/tatbot - Tạm dừng dự đoán
/help - Hướng dẫn sử dụng

✨ Cre: Ng Văn Huy ✨"""
    await update.message.reply_text(msg)

async def key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) != 1:
        await update.message.reply_text("❌ Sử dụng: /key <key>")
        return
    
    k = context.args[0]
    if key_valid(k):
        BOT_ACTIVE[user_id] = True
        USER_KEYS[user_id] = k
        await update.message.reply_text(
            "✅ Key hợp lệ! Bot đã kích hoạt dự đoán tự động.\n"
            "Sử dụng /tatbot để tạm dừng dự đoán."
        )
    else:
        BOT_ACTIVE[user_id] = False
        await update.message.reply_text("❌ Key không hợp lệ hoặc đã hết hạn.")

async def checkkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    k = USER_KEYS.get(user_id)
    if k and key_valid(k):
        await update.message.reply_text("✅ Key còn hạn.")
    else:
        await update.message.reply_text("❌ Key hết hạn hoặc chưa nhập key.")

async def taokey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ Bạn không có quyền tạo key.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("❌ Sử dụng: /taokey <số ngày> <devices>")
        return
    match = re.match(r"(\d+)", context.args[0])
    if not match:
        await update.message.reply_text("❌ Số ngày không hợp lệ")
        return
    days = int(match.group(1))
    devices = context.args[1]
    k = generate_key()
    expire = datetime.now() + timedelta(days=days)
    keys = load_keys()
    keys[k] = {"expire": expire.strftime("%Y-%m-%d %H:%M:%S"), "devices": devices}
    save_keys(keys)
    msg = f"""🔑 TẠO KEY THÀNH CÔNG
🆔 Key: {k}
📅 Hạn: {expire.strftime("%Y-%m-%d %H:%M:%S")}
📱 Thiết bị: {devices}"""
    await update.message.reply_text(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
Các lệnh bot:
/key <key> - Nhập key để kích hoạt 
/checkkey - Kiểm tra key còn hạn không
/chaybot - Bật dự đoán tự động
/tatbot - Tạm dừng dự đoán
/stop - Ngừng bot
/taokey <days> <devices> - Tạo key (admin)
/help - Hướng dẫn sử dụng
"""
    await update.message.reply_text(msg)

async def chaybot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    k = USER_KEYS.get(user_id)
    if not k or not key_valid(k):
        await update.message.reply_text("❌ Key hết hạn hoặc chưa nhập key.")
        return
    BOT_ACTIVE[user_id] = True
    await update.message.reply_text("✅ Bot đã bật dự đoán tự động.")

async def tatbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    BOT_ACTIVE[user_id] = False
    await update.message.reply_text("✅ Bot đã tạm dừng dự đoán.")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 Bot đã dừng.")
    sys.exit(0)

# ===== AUTO SEND =====
async def send_prediction_periodically(app):
    last_session = None
    while True:
        data, msg = await get_prediction()
        if not data:
            await asyncio.sleep(5)
            continue

        current_session = data.get("Phien_hien_tai")
        if current_session != last_session:
            last_session = current_session
            for user_id, active in list(BOT_ACTIVE.items()):
                if active:
                    k = USER_KEYS.get(user_id)
                    if k and key_valid(k):
                        try:
                            await app.bot.send_message(chat_id=int(user_id), text=msg)
                            print(f"✅ Gửi dự đoán cho user {user_id}")
                        except Exception as e:
                            print(f"❌ Lỗi gửi user {user_id}: {e}")
                    else:
                        BOT_ACTIVE[user_id] = False
                        try:
                            await app.bot.send_message(chat_id=int(user_id), text="❌ Key hết hạn. Vui lòng nhập key mới /key <key>")
                        except:
                            pass
            # Gửi nhóm
            try:
                if GROUP_ID:
                    await app.bot.send_message(chat_id=GROUP_ID, text=msg)
                    print(f"✅ Gửi dự đoán cho nhóm {GROUP_ID}")
            except Exception as e:
                print(f"❌ Lỗi gửi nhóm {GROUP_ID}: {e}")
        await asyncio.sleep(5)

# ===== MAIN =====
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("key", key_command))
    app.add_handler(CommandHandler("checkkey", checkkey_command))
    app.add_handler(CommandHandler("taokey", taokey_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("chaybot", chaybot_command))
    app.add_handler(CommandHandler("tatbot", tatbot_command))
    app.add_handler(CommandHandler("stop", stop_command))

    asyncio.create_task(send_prediction_periodically(app))
    print("Bot đang chạy...✨")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())