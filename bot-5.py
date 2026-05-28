"""
Nakrutka Bot - Telegram & Instagram uchun admin panel boti
Kutubxonalar: pip install python-telegram-bot requests
"""

import os
import logging
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─── SOZLAMALAR ───────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8988476578:AAFhHYl6HxT6WXqZeG73Z2Jyrz9MYwPcXlM")
ADMIN_IDS = [5111036228]   # <-- Sizning Telegram ID ingiz

API_URL = os.environ.get("API_URL", "https://topsmm.uz/api/v2")
API_KEY = os.environ.get("API_KEY", "ee66a69514f9bce940e4c8b3eea5cbb5")

# ─── HOLATLAR ────────────────────────────────────────────────────────────────
(
    MAIN_MENU,
    SELECT_PLATFORM,
    SELECT_SERVICE,
    ENTER_LINK,
    ENTER_QUANTITY,
    CONFIRM_ORDER,
    CHECK_ORDER,
    ADD_BALANCE,
) = range(8)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── RENDER UCHUN WEB SERVER (bepul tier uxlab qolmasin) ─────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Nakrutka bot ishlayapti!")

    def log_message(self, *args):
        pass  # server loglarini o'chirish


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Web server port {port} da ishga tushdi")
    server.serve_forever()


# ─── YORDAMCHI FUNKSIYALAR ───────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def api_request(action: str, **kwargs) -> dict:
    payload = {"key": API_KEY, "action": action, **kwargs}
    try:
        r = requests.post(API_URL, data=payload, timeout=15)
        return r.json()
    except Exception as e:
        logger.error(f"API xato: {e}")
        return {"error": str(e)}


def get_balance() -> str:
    res = api_request("balance")
    if "balance" in res:
        return f"💰 Balans: ${res['balance']} {res.get('currency', 'USD')}"
    return "❌ Balansni olishda xato"


def get_services_list() -> list:
    res = api_request("services")
    if isinstance(res, list):
        return res
    return []


def place_order(service_id: int, link: str, quantity: int) -> dict:
    return api_request("add", service=service_id, link=link, quantity=quantity)


def check_order_status(order_id: int) -> dict:
    return api_request("status", order=order_id)


def get_orders_list() -> dict:
    return api_request("orders")


# ─── KLAVIATURALAR ───────────────────────────────────────────────────────────

def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📱 Telegram Nakrutka", callback_data="platform_telegram"),
            InlineKeyboardButton("📸 Instagram Nakrutka", callback_data="platform_instagram"),
        ],
        [
            InlineKeyboardButton("📋 Buyurtmalar", callback_data="my_orders"),
            InlineKeyboardButton("🔍 Buyurtma tekshirish", callback_data="check_order"),
        ],
        [
            InlineKeyboardButton("💰 Balans", callback_data="balance"),
            InlineKeyboardButton("📊 Xizmatlar ro'yxati", callback_data="services_list"),
        ],
        [
            InlineKeyboardButton("ℹ️ Yordam", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def telegram_services_keyboard():
    keyboard = [
        [InlineKeyboardButton("👥 Kanalga a'zolar", callback_data="svc_tg_members")],
        [InlineKeyboardButton("👁 Post ko'rishlar", callback_data="svc_tg_views")],
        [InlineKeyboardButton("❤️ Reaksiyalar", callback_data="svc_tg_reactions")],
        [InlineKeyboardButton("🗳 So'rovnoma ovozlari", callback_data="svc_tg_votes")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def instagram_services_keyboard():
    keyboard = [
        [InlineKeyboardButton("👥 Followers (obunachilar)", callback_data="svc_ig_followers")],
        [InlineKeyboardButton("❤️ Likes (yoqtirish)", callback_data="svc_ig_likes")],
        [InlineKeyboardButton("👁 Views (ko'rishlar)", callback_data="svc_ig_views")],
        [InlineKeyboardButton("💬 Comments (izohlar)", callback_data="svc_ig_comments")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="confirm_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_main")]]
    )


# ─── XIZMAT ID XARITASI ───────────────────────────────────────────────────────
# API dagi real service ID larga moslashtiring!
SERVICE_MAP = {
    # Telegram
    "svc_tg_members":   {"id": 1001, "name": "Telegram a'zolar",     "min": 100,  "max": 100000},
    "svc_tg_views":     {"id": 1002, "name": "Telegram post ko'rish", "min": 100,  "max": 1000000},
    "svc_tg_reactions": {"id": 1003, "name": "Telegram reaksiyalar",  "min": 10,   "max": 10000},
    "svc_tg_votes":     {"id": 1004, "name": "Telegram ovozlar",      "min": 10,   "max": 5000},
    # Instagram
    "svc_ig_followers": {"id": 2001, "name": "Instagram followers",   "min": 100,  "max": 50000},
    "svc_ig_likes":     {"id": 2002, "name": "Instagram likes",       "min": 50,   "max": 100000},
    "svc_ig_views":     {"id": 2003, "name": "Instagram views",       "min": 100,  "max": 500000},
    "svc_ig_comments":  {"id": 2004, "name": "Instagram comments",    "min": 10,   "max": 5000},
}


# ─── HANDLER FUNKSIYALAR ─────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Siz admin emassiz. Kirish taqiqlangan.")
        return ConversationHandler.END

    await update.message.reply_text(
        f"👋 Xush kelibsiz, <b>{user.first_name}</b>!\n\n"
        "🤖 <b>Nakrutka Admin Panel</b>\n"
        "Telegram va Instagram uchun nakrutka xizmatlari.\n\n"
        "Pastdagi tugmalardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )
    return MAIN_MENU


async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        await query.edit_message_text(
            "🏠 <b>Asosiy Menyu</b>\nXizmatni tanlang:",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
        return MAIN_MENU

    elif data == "platform_telegram":
        ctx.user_data["platform"] = "telegram"
        await query.edit_message_text(
            "📱 <b>Telegram Xizmatlari</b>\nQaysi xizmat kerak?",
            parse_mode="HTML",
            reply_markup=telegram_services_keyboard(),
        )
        return SELECT_SERVICE

    elif data == "platform_instagram":
        ctx.user_data["platform"] = "instagram"
        await query.edit_message_text(
            "📸 <b>Instagram Xizmatlari</b>\nQaysi xizmat kerak?",
            parse_mode="HTML",
            reply_markup=instagram_services_keyboard(),
        )
        return SELECT_SERVICE

    elif data in SERVICE_MAP:
        svc = SERVICE_MAP[data]
        ctx.user_data["service_key"] = data
        ctx.user_data["service"] = svc
        await query.edit_message_text(
            f"✅ Tanlangan: <b>{svc['name']}</b>\n\n"
            f"📏 Min: <b>{svc['min']}</b> | Max: <b>{svc['max']}</b>\n\n"
            f"🔗 Endi link yuboring:\n"
            f"<i>Misol (Telegram): https://t.me/kanal_nomi</i>\n"
            f"<i>Misol (Instagram): https://instagram.com/username</i>",
            parse_mode="HTML",
            reply_markup=back_keyboard(),
        )
        return ENTER_LINK

    elif data == "balance":
        balance_text = get_balance()
        await query.edit_message_text(
            f"💰 <b>Hisob Balansi</b>\n\n{balance_text}",
            parse_mode="HTML",
            reply_markup=back_keyboard(),
        )
        return MAIN_MENU

    elif data == "services_list":
        await query.edit_message_text("⏳ Xizmatlar yuklanmoqda...", reply_markup=None)
        services = get_services_list()
        if services:
            lines = []
            for s in services[:20]:
                lines.append(
                    f"🔹 ID: <code>{s.get('service','?')}</code> — {s.get('name','?')}\n"
                    f"   Min: {s.get('min','?')} | Max: {s.get('max','?')} | Narx: ${s.get('rate','?')}/1000"
                )
            text = "📊 <b>Xizmatlar Ro'yxati</b> (birinchi 20 ta):\n\n" + "\n\n".join(lines)
        else:
            text = "❌ Xizmatlar ro'yxatini olishda xato."
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_keyboard())
        return MAIN_MENU

    elif data == "my_orders":
        await query.edit_message_text("⏳ Buyurtmalar yuklanmoqda...", reply_markup=None)
        orders = get_orders_list()
        if isinstance(orders, list) and orders:
            lines = []
            for o in orders[:15]:
                lines.append(
                    f"📦 ID: <code>{o.get('order','?')}</code>\n"
                    f"   Xizmat: {o.get('service','?')} | Miqdor: {o.get('quantity','?')}\n"
                    f"   Holat: <b>{o.get('status','?')}</b>"
                )
            text = "📋 <b>So'nggi Buyurtmalar</b>:\n\n" + "\n\n".join(lines)
        else:
            text = "📋 Buyurtmalar topilmadi yoki API xatosi."
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_keyboard())
        return MAIN_MENU

    elif data == "check_order":
        await query.edit_message_text(
            "🔍 <b>Buyurtma Tekshirish</b>\n\nBuyurtma ID raqamini yuboring:",
            parse_mode="HTML",
            reply_markup=back_keyboard(),
        )
        return CHECK_ORDER

    elif data == "confirm_yes":
        return await process_order(update, ctx)

    elif data == "confirm_no":
        ctx.user_data.clear()
        await query.edit_message_text(
            "❌ Buyurtma bekor qilindi.\n\n🏠 Asosiy menyu:",
            reply_markup=main_keyboard(),
        )
        return MAIN_MENU

    elif data == "help":
        await query.edit_message_text(
            "ℹ️ <b>Yordam</b>\n\n"
            "1️⃣ Platformani tanlang (Telegram / Instagram)\n"
            "2️⃣ Xizmat turini tanlang\n"
            "3️⃣ Link yuboring\n"
            "4️⃣ Miqdor kiriting\n"
            "5️⃣ Tasdiqlang ✅\n\n"
            "📌 <b>Eslatmalar:</b>\n"
            "• Telegram kanallar uchun: https://t.me/kanal\n"
            "• Instagram: https://instagram.com/username\n"
            "• Post uchun post linkini yuboring\n\n"
            "🛠 Muammo bo'lsa admin bilan bog'laning.",
            parse_mode="HTML",
            reply_markup=back_keyboard(),
        )
        return MAIN_MENU

    return MAIN_MENU


async def receive_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    if not link.startswith("http"):
        await update.message.reply_text(
            "❗ Noto'g'ri link. http:// yoki https:// bilan boshlang:"
        )
        return ENTER_LINK

    ctx.user_data["link"] = link
    svc = ctx.user_data.get("service", {})
    await update.message.reply_text(
        f"📏 <b>Miqdor kiriting</b>\n\n"
        f"Xizmat: <b>{svc.get('name','?')}</b>\n"
        f"Min: <b>{svc.get('min',1)}</b> | Max: <b>{svc.get('max',100000)}</b>",
        parse_mode="HTML",
    )
    return ENTER_QUANTITY


async def receive_quantity(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    svc = ctx.user_data.get("service", {})

    if not text.isdigit():
        await update.message.reply_text("❗ Faqat raqam kiriting:")
        return ENTER_QUANTITY

    qty = int(text)
    if qty < svc.get("min", 1) or qty > svc.get("max", 100000):
        await update.message.reply_text(
            f"❗ Miqdor {svc['min']} va {svc['max']} orasida bo'lishi kerak:"
        )
        return ENTER_QUANTITY

    ctx.user_data["quantity"] = qty
    link = ctx.user_data["link"]

    await update.message.reply_text(
        f"📋 <b>Buyurtmani Tasdiqlang</b>\n\n"
        f"🔧 Xizmat: <b>{svc['name']}</b>\n"
        f"🔗 Link: <code>{link}</code>\n"
        f"📊 Miqdor: <b>{qty:,}</b>\n\n"
        f"Davom etamizmi?",
        parse_mode="HTML",
        reply_markup=confirm_keyboard(),
    )
    return CONFIRM_ORDER


async def process_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("⏳ Buyurtma joylashtirilmoqda...")

    svc = ctx.user_data.get("service", {})
    link = ctx.user_data.get("link", "")
    quantity = ctx.user_data.get("quantity", 0)

    result = place_order(
        service_id=svc.get("id"),
        link=link,
        quantity=quantity,
    )

    if "order" in result:
        order_id = result["order"]
        text = (
            f"✅ <b>Buyurtma muvaffaqiyatli joylashtirildi!</b>\n\n"
            f"📦 Buyurtma ID: <code>{order_id}</code>\n"
            f"🔧 Xizmat: <b>{svc['name']}</b>\n"
            f"📊 Miqdor: <b>{quantity:,}</b>\n"
            f"🔗 Link: <code>{link}</code>\n\n"
            f"Buyurtma holatini tekshirish uchun ID raqamini saqlang."
        )
    else:
        error = result.get("error", "Noma'lum xato")
        text = f"❌ <b>Xato yuz berdi!</b>\n\n{error}"

    ctx.user_data.clear()
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_keyboard())
    return MAIN_MENU


async def receive_order_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❗ Faqat buyurtma ID raqamini kiriting:")
        return CHECK_ORDER

    order_id = int(text)
    result = check_order_status(order_id)

    if "status" in result:
        status = {
            "Pending":     "⏳ Kutilmoqda",
            "In progress": "🔄 Bajarilmoqda",
            "Completed":   "✅ Bajarildi",
            "Partial":     "⚠️ Qisman bajarildi",
            "Canceled":    "❌ Bekor qilindi",
        }.get(result["status"], result["status"])

        text_out = (
            f"📦 <b>Buyurtma #{order_id} Holati</b>\n\n"
            f"📊 Holat: <b>{status}</b>\n"
            f"⬆️ Start count: {result.get('start_count', '—')}\n"
            f"✅ Qoldi: {result.get('remains', '—')}\n"
            f"🔧 Xizmat: {result.get('service', '—')}"
        )
    else:
        error = result.get("error", "Noma'lum xato")
        text_out = f"❌ Buyurtma topilmadi yoki xato:\n{error}"

    await update.message.reply_text(
        text_out,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_main")]]
        ),
    )
    return MAIN_MENU


async def unknown_admin_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Ruxsat yo'q.")
        return ConversationHandler.END
    await update.message.reply_text("❓ /start dan boshlang.", reply_markup=main_keyboard())
    return MAIN_MENU


# ─── BOTNI ISHGA TUSHIRISH ───────────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(button_handler)],
            SELECT_SERVICE: [CallbackQueryHandler(button_handler)],
            ENTER_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link),
                CallbackQueryHandler(button_handler),
            ],
            ENTER_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity),
                CallbackQueryHandler(button_handler),
            ],
            CONFIRM_ORDER: [CallbackQueryHandler(button_handler)],
            CHECK_ORDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_id),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.ALL, unknown_admin_check),
        ],
    )

    app.add_handler(conv)

    print("🤖 Nakrutka boti ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    # Render bepul tier uchun web server parallel ishga tushiriladi
    threading.Thread(target=run_web_server, daemon=True).start()
    main()
