import os
import sys
import sqlite3
import datetime
import time
import logging
import re
import threading

# SSL sertifikat
os.environ['REQUESTS_CA_BUNDLE'] = '/etc/ssl/certs/ca-certificates.crt'
os.environ['SSL_CERT_FILE'] = '/etc/ssl/certs/ca-certificates.crt'

try:
    os.symlink('/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt')
except Exception:
    pass

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ╔══════════════════════════════════════════╗
# ║          ⚙️ SOZLAMALAR                  ║
# ╚══════════════════════════════════════════╝
BOT_TOKEN = "8720789945:AAHyWvjwzhRhaCntP_4RQ8M1IUUOrrjHjM0"
ADMIN_ID  = 8595373987
DB_PATH   = "kino_bot.db"

import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    CallbackQuery, Message
)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", num_threads=6)
telebot.apihelper.SESSION_TIME_OUT = 60

# Webhookni tozalash
try:
    bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook o'chirildi")
except Exception as e:
    logger.warning(f"Webhook o'chirishda xato: {e}")


# ╔══════════════════════════════════════════╗
# ║          🗄️ DATABASE                   ║
# ╚══════════════════════════════════════════╝
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        first_name TEXT DEFAULT '',
        joined_at TEXT DEFAULT '',
        is_banned INTEGER DEFAULT 0,
        is_vip INTEGER DEFAULT 0,
        vip_until TEXT DEFAULT '',
        searches INTEGER DEFAULT 0,
        balance INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS movies (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        added_at TEXT DEFAULT '',
        views INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS movie_parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_code TEXT NOT NULL,
        part_num INTEGER NOT NULL,
        file_id TEXT NOT NULL,
        file_type TEXT DEFAULT 'video',
        caption TEXT DEFAULT '',
        FOREIGN KEY (movie_code) REFERENCES movies(code)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS channels (
        channel_id TEXT PRIMARY KEY,
        channel_name TEXT DEFAULT '',
        channel_link TEXT DEFAULT '',
        added_at TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_number TEXT NOT NULL,
        bank_name TEXT DEFAULT '',
        owner_name TEXT DEFAULT '',
        added_at TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS vip_prices (
        months INTEGER PRIMARY KEY,
        price INTEGER NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        months INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        screenshot_file_id TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT '',
        reviewed_at TEXT DEFAULT ''
    )""")

    default_prices = [(1, 10000), (2, 18000), (3, 25000), (6, 45000), (12, 80000)]
    for m, p in default_prices:
        c.execute("INSERT OR IGNORE INTO vip_prices (months, price) VALUES (?,?)", (m, p))

    conn.commit()
    conn.close()
    logger.info("Database yaratildi/tekshirildi")


def ensure_user(user_id, username='', first_name=''):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            "INSERT INTO users (user_id,username,first_name,joined_at) VALUES (?,?,?,?)",
            (user_id, username, first_name, now)
        )
        conn.commit()
    conn.close()


def is_vip(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_vip, vip_until FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row['is_vip']:
        if row['vip_until']:
            try:
                until = datetime.datetime.strptime(row['vip_until'], '%Y-%m-%d %H:%M:%S')
                if until > datetime.datetime.now():
                    return True
                else:
                    set_vip(user_id, False)
            except Exception:
                pass
    return False


def set_vip(user_id, active, months=0):
    conn = get_db()
    c = conn.cursor()
    if active and months > 0:
        until = datetime.datetime.now() + datetime.timedelta(days=30 * months)
        c.execute(
            "UPDATE users SET is_vip=1, vip_until=? WHERE user_id=?",
            (until.strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
    elif active:
        c.execute("UPDATE users SET is_vip=1 WHERE user_id=?", (user_id,))
    else:
        c.execute("UPDATE users SET is_vip=0, vip_until='' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def is_banned(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row and row['is_banned']


def set_ban(user_id, banned=True):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if banned else 0, user_id))
    conn.commit()
    conn.close()


def check_subscription(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT channel_id, channel_name, channel_link FROM channels")
    channels = c.fetchall()
    conn.close()

    not_subscribed = []
    for ch in channels:
        try:
            member = bot.get_chat_member(ch['channel_id'], user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(dict(ch))
        except Exception as e:
            logger.warning(f"Kanal tekshirishda xato {ch['channel_id']}: {e}")
            not_subscribed.append(dict(ch))

    return len(not_subscribed) == 0, not_subscribed


def format_number(n):
    s = str(n)
    groups = []
    while s:
        groups.insert(0, s[-3:])
        s = s[:-3]
    return ' '.join(groups)


# ╔══════════════════════════════════════════╗
# ║          🎹 KLAVIATURALAR             ║
# ╚════════════════════════════════════════╝
def main_menu_kb(is_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🎬 Kino qidirish"))
    kb.add(KeyboardButton("👤 Profil"), KeyboardButton("💎 VIP sotib olish"))
    kb.add(KeyboardButton("📋 VIP narxlar"))
    if is_admin:
        kb.add(KeyboardButton("🔑 Admin Panel"))
    return kb


def admin_menu_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📊 Statistika"),
        KeyboardButton("📢 Kanal boshqarish"),
        KeyboardButton("🎬 Kino boshqarish"),
        KeyboardButton("💳 Karta boshqarish"),
        KeyboardButton("💵 VIP narx"),
        KeyboardButton("📨 Xabar yuborish"),
        KeyboardButton("👤 Foydalanuvchi boshqarish"),
        KeyboardButton("💰 To'lovlar"),
        KeyboardButton("🔙 Orqaga")
    )
    return kb


def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Bekor qilish"))
    return kb


def subscription_kb(not_subscribed):
    kb = InlineKeyboardMarkup()
    for ch in not_subscribed:
        kb.add(InlineKeyboardButton(f"📢 {ch['channel_name']}", url=ch['channel_link']))
    kb.add(InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub"))
    return kb


def vip_buy_kb():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT months, price FROM vip_prices ORDER BY months")
    prices = c.fetchall()
    conn.close()

    kb = InlineKeyboardMarkup()
    for p in prices:
        price_str = format_number(p['price'])
        kb.add(InlineKeyboardButton(
            f"{p['months']} oy — {price_str} so'm",
            callback_data=f"buyvip_{p['months']}"
        ))
    return kb


def movie_parts_kb(movie_code, parts, user_vip=False):
    kb = InlineKeyboardMarkup()
    for p in parts:
        kb.add(InlineKeyboardButton(
            f"🎞 Qism {p['part_num']}",
            callback_data=f"part_{movie_code}_{p['part_num']}"
        ))
    if user_vip and len(parts) > 1:
        kb.add(InlineKeyboardButton(
            "⬇️️ Barchasini yuklab olish",
            callback_data=f"download_all_{movie_code}"
        ))
    return kb


# ╔══════════════════════════════════════════╗
# ║          🔑 ADMIN STATE                ║
# ╚══════════════════════════════════════════╝
admin_state = {}


def set_admin_state(user_id, action, data=None):
    if data is not None:
        admin_state[user_id] = {'action': action, **data}
    else:
        admin_state[user_id] = {'action': action}


def get_admin_state(user_id):
    return admin_state.get(user_id)


def clear_admin_state(user_id):
    admin_state.pop(user_id, None)


def is_admin(user_id):
    return user_id == ADMIN_ID


# ╔══════════════════════════════════════════╗
# ║          👤 FOYDALANUVCHI HANDLERLARI   ║
# ╚══════════════════════════════════════════╝

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ''
    first_name = message.from_user.first_name or ''
    ensure_user(user_id, username, first_name)
    clear_admin_state(user_id)

    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Siz botdan chiqarilgansiz.")
        return

    is_adm = is_admin(user_id)

    if not is_vip(user_id):
        ok, not_sub = check_subscription(user_id)
        if not ok:
            bot.send_message(
                user_id,
                "🔒 <b>Majburiy obuna!</b>\n\n"
                "Kino tomosha qilish uchun quyidagi kanallarga obuna bo'ling:\n"
                "Obuna bo'lganingizdan keyin \"✅ Obuna bo'ldim\" tugmasini bosing.",
                reply_markup=subscription_kb(not_sub)
            )
            return

    text = (
        f"👋 Assalomu alaykum, <b>{first_name}</b>!\n\n"
        "🎬 Men yordamchingiz — kino bot!\n"
        "Quyidagi menyudan tanlang yoki kino kodini yuboring:\n\n"
        "💎 <b>VIP</b> foydalanuvchilar uchun:\n"
        "  ⚡️ Obunasiz kirish\n"
        "  ⚡️ Barcha qismlar birga yuklash"
    )
    bot.send_message(user_id, text, reply_markup=main_menu_kb(is_adm))


@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    ok, not_sub = check_subscription(user_id)
    if ok:
        is_adm = is_admin(user_id)
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
        bot.send_message(
            user_id,
            "🎉 Obuna tasdiqlandi! Endi kinolardan foydalanishingiz mumkin.",
            reply_markup=main_menu_kb(is_adm)
        )
    else:
        bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)


@bot.message_handler(func=lambda m: m.text == "🎬 Kino qidirish")
def btn_search(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, "🚫 Siz botdan chiqarilgansiz.")
        return

    if not is_vip(user_id):
        ok, _ = check_subscription(user_id)
        if not ok:
            bot.send_message(user_id, "❌ Avval kanallarga obuna bo'ling!")
            return

    bot.send_message(user_id, "🎬 Kino kodini kiriting:\nMasalan: <b>101</b>", reply_markup=cancel_kb())
    set_admin_state(user_id, "waiting_search_code")


@bot.message_handler(func=lambda m: m.text == "📋 VIP narxlar")
def btn_vip_prices(message):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT months, price FROM vip_prices ORDER BY months")
    prices = c.fetchall()
    conn.close()

    text = "📋 <b>VIP Tariflar Narxlari:</b>\n\n"
    for p in prices:
        text += f"🔹 <b>{p['months']} oy</b> — {format_number(p['price'])} so'm\n"
    text += "\nSotib olish uchun 💎 VIP sotib olish tugmasini bosing."
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "👤 Profil")
def btn_profile(message):
    user_id = message.from_user.id
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    if not user:
        bot.send_message(user_id, "❌ Foydalanuvchi topilmadi. /start ni bosing.")
        return

    vip_status = "💎 VIP" if is_vip(user_id) else "🆓 Oddiy"
    vip_until = user['vip_until'] if user['vip_until'] else "—"

    text = (
        f"👤 <b>Profil</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📛 Ism: {user['first_name']}\n"
        f"🔹 Username: @{user['username'] or 'yo\'q'}\n"
        f"📅 Qo'shilgan: {user['joined_at']}\n"
        f"🎬 Qidirishlar: {user['searches']}\n"
        f"💼 Holat: {vip_status}\n"
        f"📆 VIP muddati: {vip_until}\n"
    )
    bot.send_message(user_id, text)


@bot.message_handler(func=lambda m: m.text == "💎 VIP sotib olish")
def btn_vip_buy(message):
    text = (
        "💎 <b>VIP olish</b>\n\n"
        "VIP sotib olish uchun:\n"
        "1️⃣ Quyidagi tariflardan birini tanlang\n"
        "2️⃣ Ko'rsatilgan kartaga to'lov qiling\n"
        "3️⃣ To'lov chek rasmini yuboring\n"
        "4️⃣ Admin tasdiqlashini kuting ✅"
    )
    bot.send_message(message.chat.id, text, reply_markup=vip_buy_kb())


@bot.callback_query_handler(func=lambda call: call.data.startswith("buyvip_"))
def callback_vip_select(call):
    user_id = call.from_user.id
    months = int(call.data.split("_")[1])

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT price FROM vip_prices WHERE months=?", (months,))
    price_row = c.fetchone()
    c.execute("SELECT * FROM cards")
    cards = c.fetchall()
    conn.close()

    if not price_row:
        bot.answer_callback_query(call.id, "❌ Narx topilmadi!", show_alert=True)
        return

    price = price_row['price']
    cards_text = ""
    if cards:
        for i, card in enumerate(cards, 1):
            cards_text += f"\n💳 <b>Karta {i}:</b>\n"
            cards_text += f"  Raqam: <code>{card['card_number']}</code>\n"
            cards_text += f"  Bank: {card['bank_name']}\n"
            cards_text += f"  Egasi: {card['owner_name']}\n"
    else:
        cards_text = "\n⚠️ Hali to'lov kartalari qo'shilmagan.\n"

    price_str = format_number(price)
    text = (
        f"💎 <b>VIP {months} oylik tarif</b>\n"
        f"💰 Narxi: <b>{price_str} so'm</b>\n"
        f"{cards_text}\n"
        f"📌 To'lovni amalga oshirgach, to'lov cheki (skrinshot) rasmini ushbu botga yuboring!"
    )
    set_admin_state(user_id, "waiting_payment_screenshot", {"months": months, "amount": price})
    bot.send_message(user_id, text, reply_markup=cancel_kb())


@bot.callback_query_handler(func=lambda call: call.data.startswith("part_"))
def callback_download_part(call):
    user_id = call.from_user.id
    parts = call.data.split("_")
    code = parts[1]
    part = int(parts[2])

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM movie_parts WHERE movie_code=? AND part_num=?", (code, part))
    part_row = c.fetchone()
    conn.close()

    if not part_row:
        bot.answer_callback_query(call.id, "❌ Qism topilmadi!", show_alert=True)
        return

    user_vip = is_vip(user_id)
    caption = f"🎬 {code} — Qism {part}" + ("\n⚡️ VIP" if user_vip else "")

    try:
        if part_row['file_type'] == 'video':
            bot.send_video(user_id, part_row['file_id'], caption=caption, supports_streaming=True)
        else:
            bot.send_document(user_id, part_row['file_id'], caption=caption)
        bot.answer_callback_query(call.id, f"✅ Qism {part} yuborildi!")
    except Exception as e:
        logger.error(f"Fayl yuborishda xato: {e}")
        bot.answer_callback_query(call.id, "❌ Fayl yuborishda xatolik!", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("download_all_"))
def callback_download_all(call):
    user_id = call.from_user.id
    code = call.data.replace("download_all_", "")

    if not is_vip(user_id):
        bot.answer_callback_query(call.id, "❌ Bu funksiya faqat VIP uchun!", show_alert=True)
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM movie_parts WHERE movie_code=? ORDER BY part_num", (code,))
    parts = c.fetchall()
    conn.close()

    bot.answer_callback_query(call.id, f"⬇️ {len(parts)} ta qism yuborilmoqda...")

    for p in parts:
        try:
            caption = f"🎬 {code} — Qism {p['part_num']}\n⚡️ VIP"
            if p['file_type'] == 'video':
                bot.send_video(user_id, p['file_id'], caption=caption, supports_streaming=True)
            else:
                bot.send_document(user_id, p['file_id'], caption=caption)
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Xato: {e}")


# ╔══════════════════════════════════════════╗
# ║          🔑 ADMIN PANEL HANDLERLARI    ║
# ╚══════════════════════════════════════════╝

@bot.message_handler(func=lambda m: m.text == "🔑 Admin Panel" and is_admin(m.from_user.id))
def btn_admin_panel(message):
    clear_admin_state(message.from_user.id)
    bot.send_message(message.chat.id, "🔑 <b>Admin Panel</b>ga xush kelibsiz!", reply_markup=admin_menu_kb())


@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and is_admin(m.from_user.id))
def admin_stats(message):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_vip=1")
    vip_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM movies")
    total_movies = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")
    pending_payments = c.fetchone()[0]
    conn.close()

    text = (
        "📊 <b>Bot Statistikasi:</b>\n\n"
        f"👥 Barcha foydalanuvchilar: <b>{total_users}</b>\n"
        f"💎 VIP foydalanuvchilar: <b>{vip_users}</b>\n"
        f"🎬 Jami kinolar: <b>{total_movies}</b>\n"
        f"⏳ Kutilayotgan to'lovlar: <b>{pending_payments}</b>"
    )
    bot.send_message(message.chat.id, text)


# 🎬 Kino Boshqarish
@bot.message_handler(func=lambda m: m.text == "🎬 Kino boshqarish" and is_admin(m.from_user.id))
def admin_movies(message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("➕ Kino qo'shish"), KeyboardButton("🗑 Kino o'chirish"))
    kb.add(KeyboardButton("🔙 Orqaga"))
    bot.send_message(message.chat.id, "🎬 Kino boshqarish bo'limi:", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "➕ Kino qo'shish" and is_admin(m.from_user.id))
def admin_add_movie_start(message):
    set_admin_state(message.from_user.id, "add_movie_code")
    bot.send_message(message.chat.id, "Kino kodini kiriting (masalan: 101):", reply_markup=cancel_kb())


@bot.message_handler(func=lambda m: m.text == "📢 Kanal boshqarish" and is_admin(m.from_user.id))
def admin_channels(message):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM channels")
    channels = c.fetchall()
    conn.close()

    text = "📢 <b>Ulangan kanallar:</b>\n\n"
    if channels:
        for ch in channels:
            text += f"🔹 {ch['channel_name']} ({ch['channel_id']})\n"
    else:
        text += "Hali kanal qo'shilmagan.\n"

    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("➕ Kanal qo'shish"), KeyboardButton("🗑 Kanal o'chirish"))
    kb.add(KeyboardButton("🔙 Orqaga"))
    bot.send_message(message.chat.id, text, reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "🔙 Orqaga")
def btn_back(message):
    user_id = message.from_user.id
    clear_admin_state(user_id)
    is_adm = is_admin(user_id)
    bot.send_message(user_id, "Bosh menyuga qaytdingiz.", reply_markup=main_menu_kb(is_adm))


@bot.message_handler(func=lambda m: m.text == "❌ Bekor qilish")
def btn_cancel(message):
    user_id = message.from_user.id
    clear_admin_state(user_id)
    is_adm = is_admin(user_id)
    bot.send_message(user_id, "Amal bekor qilindi.", reply_markup=main_menu_kb(is_adm))


@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    user_id = message.from_user.id
    state = get_admin_state(user_id)
    
    if state:
        action = state.get('action')
        
        if action == "waiting_search_code":
            code = message.text.strip()
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM movies WHERE code=?", (code,))
            movie = c.fetchone()
            c.execute("SELECT * FROM movie_parts WHERE movie_code=? ORDER BY part_num", (code,))
            parts = c.fetchall()
            conn.close()
            
            if movie and parts:
                user_vip = is_vip(user_id)
                text = f"🎬 <b>{movie['name']}</b>\n\n{movie['description']}"
                bot.send_message(user_id, text, reply_markup=movie_parts_kb(code, parts, user_vip))
                clear_admin_state(user_id)
            else:
                bot.send_message(user_id, "❌ Kino topilmadi!", reply_markup=cancel_kb())
        
        elif action == "waiting_payment_screenshot":
            if message.content_type == 'photo':
                months = state.get('months')
                amount = state.get('amount')
                file_id = message.photo[-1].file_id
                
                conn = get_db()
                c = conn.cursor()
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                c.execute(
                    "INSERT INTO payments (user_id, months, amount, screenshot_file_id, created_at) VALUES (?,?,?,?,?)",
                    (user_id, months, amount, file_id, now)
                )
                conn.commit()
                conn.close()
                
                bot.send_message(user_id, "✅ To'lov cheki qabul qilindi! Admin tekshirib tasdiqlashini kuting.")
                bot.send_message(ADMIN_ID, f"🔔 Yangi to'lov:\nFoydalanuvchi: {user_id}\nSummasi: {amount} so'm\n{months} oy")
                clear_admin_state(user_id)
            else:
                bot.send_message(user_id, "❌ Rasmni yuboring!", reply_markup=cancel_kb())
        
        elif action == "add_movie_code":
            code = message.text.strip()
            set_admin_state(user_id, "add_movie_name", {"code": code})
            bot.send_message(user_id, "Kino nomini kiriting:", reply_markup=cancel_kb())
        
        elif action == "add_movie_name":
            name = message.text.strip()
            code = state.get('code')
            set_admin_state(user_id, "add_movie_desc", {"code": code, "name": name})
            bot.send_message(user_id, "Kino tavsifini kiriting:", reply_markup=cancel_kb())
        
        elif action == "add_movie_desc":
            desc = message.text.strip()
            code = state.get('code')
            name = state.get('name')
            
            conn = get_db()
            c = conn.cursor()
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            try:
                c.execute(
                    "INSERT INTO movies (code, name, description, added_at) VALUES (?,?,?,?)",
                    (code, name, desc, now)
                )
                conn.commit()
                bot.send_message(user_id, f"✅ Kino '{name}' qo'shildi!")
            except sqlite3.IntegrityError:
                bot.send_message(user_id, "❌ Bu kod allaqachon mavjud!")
            finally:
                conn.close()
                clear_admin_state(user_id)
    
    else:
        bot.send_message(user_id, "❓ Buyruqni tushunmadim. Menyudan tanlang yoki /start bosing.")


# Bot ishga tushirish
if __name__ == "__main__":
    init_db()
    logger.info("🤖 Bot ishga tushdi!")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")
    except Exception as e:
        logger.error(f"Xato: {e}")
