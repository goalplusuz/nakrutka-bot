"""
Nakrutka Bot - pyTelegramBotAPI (telebot) versiyasi
pip install pytelegrambotapi requests
"""

import os
import logging
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─── SOZLAMALAR ───────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS  = [5111036228]  # Sizning Telegram ID ingiz

API_URL = os.environ.get("API_URL", "https://topsmm.uz/api/v2")
API_KEY = os.environ.get("API_KEY", "YOUR_API_KEY_HERE")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# ─── FOYDALANUVCHI HOLATI ────────────────────────────────────────────────────
user_state = {}   # {user_id: {"step": ..., "service": ..., "link": ...}}

# ─── RENDER WEB SERVER ───────────────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Nakrutka bot ishlayapti!")
    def log_message(self, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()

# ─── YORDAMCHI FUNKSIYALAR ───────────────────────────────────────────────────
def is_admin(uid):
    return uid in ADMIN_IDS

def api_request(action, **kwargs):
    try:
        r = requests.post(API_URL, data={"key": API_KEY, "action": action, **kwargs}, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ─── XIZMAT RO'YXATI ─────────────────────────────────────────────────────────
SERVICE_MAP = {
    "svc_tg_members":   {"id": 1001, "name": "Telegram a'zolar",      "min": 100,  "max": 100000},
    "svc_tg_views":     {"id": 1002, "name": "Telegram post ko'rish",  "min": 100,  "max": 1000000},
    "svc_tg_reactions": {"id": 1003, "name": "Telegram reaksiyalar",   "min": 10,   "max": 10000},
    "svc_tg_votes":     {"id": 1004, "name": "Telegram ovozlar",       "min": 10,   "max": 5000},
    "svc_ig_followers": {"id": 2001, "name": "Instagram followers",    "min": 100,  "max": 50000},
    "svc_ig_likes":     {"id": 2002, "name": "Instagram likes",        "min": 50,   "max": 100000},
    "svc_ig_views":     {"id": 2003, "name": "Instagram views",        "min": 100,  "max": 500000},
    "svc_ig_comments":  {"id": 2004, "name": "Instagram comments",     "min": 10,   "max": 5000},
}

# ─── KLAVIATURALAR ───────────────────────────────────────────────────────────
def main_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📱 Telegram", callback_data="platform_telegram"),
        InlineKeyboardButton("📸 Instagram", callback_data="platform_instagram"),
    )
    kb.row(
        InlineKeyboardButton("📋 Buyurtmalar", callback_data="my_orders"),
        InlineKeyboardButton("🔍 Tekshirish", callback_data="check_order"),
    )
    kb.row(
        InlineKeyboardButton("💰 Balans", callback_data="balance"),
        InlineKeyboardButton("📊 Xizmatlar", callback_data="services_list"),
    )
    kb.row(InlineKeyboardButton("ℹ️ Yordam", callback_data="help"))
    return kb

def telegram_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("👥 Kanalga a'zolar", callback_data="svc_tg_members"))
    kb.row(InlineKeyboardButton("👁 Post ko'rishlar", callback_data="svc_tg_views"))
    kb.row(InlineKeyboardButton("❤️ Reaksiyalar", callback_data="svc_tg_reactions"))
    kb.row(InlineKeyboardButton("🗳 Ovozlar", callback_data="svc_tg_votes"))
    kb.row(InlineKeyboardButton("🔙 Orqaga", callback_data="back_main"))
    return kb

def instagram_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("👥 Followers", callback_data="svc_ig_followers"))
    kb.row(InlineKeyboardButton("❤️ Likes", callback_data="svc_ig_likes"))
    kb.row(InlineKeyboardButton("👁 Views", callback_data="svc_ig_views"))
    kb.row(InlineKeyboardButton("💬 Comments", callback_data="svc_ig_comments"))
    kb.row(InlineKeyboardButton("🔙 Orqaga", callback_data="back_main"))
    return kb

def confirm_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_yes"),
        InlineKeyboardButton("❌ Bekor", callback_data="confirm_no"),
    )
    return kb

def back_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_main"))
    return kb

# ─── /start ──────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def start(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "⛔ Siz admin emassiz. Kirish taqiqlangan.")
        return
    user_state[msg.from_user.id] = {"step": "main"}
    bot.send_message(
        msg.chat.id,
        f"👋 Xush kelibsiz, <b>{msg.from_user.first_name}</b>!\n\n"
        "🤖 <b>Nakrutka Admin Panel</b>\n"
        "Telegram va Instagram nakrutka xizmatlari.\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )

# ─── CALLBACK HANDLER ────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    uid  = call.from_user.id
    data = call.data

    if not is_admin(uid):
        bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q!")
        return

    bot.answer_callback_query(call.id)

    # ── Asosiy menyu ──
    if data == "back_main":
        user_state[uid] = {"step": "main"}
        bot.edit_message_text(
            "🏠 <b>Asosiy Menyu</b>\nXizmatni tanlang:",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=main_keyboard(),
        )

    # ── Platform ──
    elif data == "platform_telegram":
        user_state[uid] = {"step": "select_service", "platform": "telegram"}
        bot.edit_message_text(
            "📱 <b>Telegram Xizmatlari</b>\nQaysi xizmat kerak?",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=telegram_keyboard(),
        )

    elif data == "platform_instagram":
        user_state[uid] = {"step": "select_service", "platform": "instagram"}
        bot.edit_message_text(
            "📸 <b>Instagram Xizmatlari</b>\nQaysi xizmat kerak?",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=instagram_keyboard(),
        )

    # ── Xizmat tanlash ──
    elif data in SERVICE_MAP:
        svc = SERVICE_MAP[data]
        user_state[uid].update({"step": "enter_link", "service": svc})
        bot.edit_message_text(
            f"✅ Tanlangan: <b>{svc['name']}</b>\n\n"
            f"📏 Min: <b>{svc['min']}</b> | Max: <b>{svc['max']}</b>\n\n"
            f"🔗 Link yuboring:\n"
            f"<i>Telegram: https://t.me/kanal_nomi\n"
            f"Instagram: https://instagram.com/username</i>",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=back_keyboard(),
        )

    # ── Balans ──
    elif data == "balance":
        res = api_request("balance")
        if "balance" in res:
            text = f"💰 <b>Balans:</b> ${res['balance']} {res.get('currency','USD')}"
        else:
            text = f"❌ Xato: {res.get('error','Noma\\'lum')}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="HTML", reply_markup=back_keyboard())

    # ── Xizmatlar ro'yxati ──
    elif data == "services_list":
        bot.edit_message_text("⏳ Yuklanmoqda...", call.message.chat.id, call.message.message_id)
        services = api_request("services")
        if isinstance(services, list) and services:
            lines = []
            for s in services[:20]:
                lines.append(
                    f"🔹 ID: <code>{s.get('service','?')}</code> — {s.get('name','?')}\n"
                    f"   Min: {s.get('min','?')} | Max: {s.get('max','?')} | ${s.get('rate','?')}/1000"
                )
            text = "📊 <b>Xizmatlar (birinchi 20):</b>\n\n" + "\n\n".join(lines)
        else:
            text = "❌ Xizmatlar olishda xato."
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="HTML", reply_markup=back_keyboard())

    # ── Buyurtmalar ──
    elif data == "my_orders":
        bot.edit_message_text("⏳ Yuklanmoqda...", call.message.chat.id, call.message.message_id)
        orders = api_request("orders")
        if isinstance(orders, list) and orders:
            lines = []
            for o in orders[:15]:
                lines.append(
                    f"📦 ID: <code>{o.get('order','?')}</code>\n"
                    f"   Miqdor: {o.get('quantity','?')} | Holat: <b>{o.get('status','?')}</b>"
                )
            text = "📋 <b>So'nggi Buyurtmalar:</b>\n\n" + "\n\n".join(lines)
        else:
            text = "📋 Buyurtmalar topilmadi."
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="HTML", reply_markup=back_keyboard())

    # ── Buyurtma tekshirish ──
    elif data == "check_order":
        user_state[uid] = {"step": "check_order"}
        bot.edit_message_text(
            "🔍 <b>Buyurtma tekshirish</b>\n\nBuyurtma ID raqamini yuboring:",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=back_keyboard(),
        )

    # ── Tasdiqlash ──
    elif data == "confirm_yes":
        state = user_state.get(uid, {})
        svc      = state.get("service", {})
        link     = state.get("link", "")
        quantity = state.get("quantity", 0)
        bot.edit_message_text("⏳ Buyurtma joylashtirilmoqda...",
                              call.message.chat.id, call.message.message_id)
        res = api_request("add", service=svc.get("id"), link=link, quantity=quantity)
        if "order" in res:
            text = (
                f"✅ <b>Buyurtma joylashtirildi!</b>\n\n"
                f"📦 ID: <code>{res['order']}</code>\n"
                f"🔧 Xizmat: <b>{svc['name']}</b>\n"
                f"📊 Miqdor: <b>{quantity:,}</b>\n"
                f"🔗 Link: <code>{link}</code>"
            )
        else:
            text = f"❌ Xato: {res.get('error','Noma\\'lum')}"
        user_state[uid] = {"step": "main"}
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="HTML", reply_markup=back_keyboard())

    elif data == "confirm_no":
        user_state[uid] = {"step": "main"}
        bot.edit_message_text(
            "❌ Bekor qilindi.\n\n🏠 Asosiy menyu:",
            call.message.chat.id, call.message.message_id,
            reply_markup=main_keyboard(),
        )

    # ── Yordam ──
    elif data == "help":
        bot.edit_message_text(
            "ℹ️ <b>Yordam</b>\n\n"
            "1️⃣ Platformani tanlang\n"
            "2️⃣ Xizmat turini tanlang\n"
            "3️⃣ Link yuboring\n"
            "4️⃣ Miqdor kiriting\n"
            "5️⃣ Tasdiqlang ✅\n\n"
            "📌 <b>Eslatma:</b>\n"
            "• Telegram: https://t.me/kanal\n"
            "• Instagram: https://instagram.com/username",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=back_keyboard(),
        )

# ─── MATN XABARLARI ──────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    uid  = msg.from_user.id
    text = msg.text.strip()

    if not is_admin(uid):
        bot.send_message(msg.chat.id, "⛔ Ruxsat yo'q.")
        return

    state = user_state.get(uid, {"step": "main"})
    step  = state.get("step", "main")

    # ── Link qabul qilish ──
    if step == "enter_link":
        if not text.startswith("http"):
            bot.send_message(msg.chat.id, "❗ http:// yoki https:// bilan boshlang:")
            return
        user_state[uid]["link"] = text
        user_state[uid]["step"] = "enter_quantity"
        svc = state.get("service", {})
        bot.send_message(
            msg.chat.id,
            f"📏 <b>Miqdor kiriting</b>\n\n"
            f"Xizmat: <b>{svc.get('name','?')}</b>\n"
            f"Min: <b>{svc.get('min',1)}</b> | Max: <b>{svc.get('max',100000)}</b>",
            parse_mode="HTML",
        )

    # ── Miqdor qabul qilish ──
    elif step == "enter_quantity":
        if not text.isdigit():
            bot.send_message(msg.chat.id, "❗ Faqat raqam kiriting:")
            return
        qty = int(text)
        svc = state.get("service", {})
        if qty < svc.get("min", 1) or qty > svc.get("max", 100000):
            bot.send_message(
                msg.chat.id,
                f"❗ {svc['min']} va {svc['max']} orasida bo'lishi kerak:"
            )
            return
        user_state[uid]["quantity"] = qty
        user_state[uid]["step"]     = "confirm"
        link = user_state[uid].get("link", "")
        bot.send_message(
            msg.chat.id,
            f"📋 <b>Buyurtmani Tasdiqlang</b>\n\n"
            f"🔧 Xizmat: <b>{svc['name']}</b>\n"
            f"🔗 Link: <code>{link}</code>\n"
            f"📊 Miqdor: <b>{qty:,}</b>\n\n"
            f"Davom etamizmi?",
            parse_mode="HTML",
            reply_markup=confirm_keyboard(),
        )

    # ── Buyurtma ID tekshirish ──
    elif step == "check_order":
        if not text.isdigit():
            bot.send_message(msg.chat.id, "❗ Faqat ID raqam kiriting:")
            return
        res = api_request("status", order=int(text))
        if "status" in res:
            holat = {
                "Pending":     "⏳ Kutilmoqda",
                "In progress": "🔄 Bajarilmoqda",
                "Completed":   "✅ Bajarildi",
                "Partial":     "⚠️ Qisman bajarildi",
                "Canceled":    "❌ Bekor qilindi",
            }.get(res["status"], res["status"])
            out = (
                f"📦 <b>Buyurtma #{text}</b>\n\n"
                f"📊 Holat: <b>{holat}</b>\n"
                f"⬆️ Boshlang'ich: {res.get('start_count','—')}\n"
                f"🔄 Qoldi: {res.get('remains','—')}"
            )
        else:
            out = f"❌ Topilmadi: {res.get('error','Noma\\'lum')}"
        user_state[uid] = {"step": "main"}
        bot.send_message(msg.chat.id, out, parse_mode="HTML", reply_markup=back_keyboard())

    else:
        bot.send_message(msg.chat.id, "❓ /start dan boshlang.", reply_markup=main_keyboard())

# ─── ISHGA TUSHIRISH ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    logger.info("🤖 Nakrutka boti ishga tushdi...")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
