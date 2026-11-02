import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8638320387:AAEdOIUR9SSBoVhWUsrFMlmKmVPX6xeWWS4"
ADMIN_ID = 8595373987

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

def db_connect():
    conn = sqlite3.connect("movie_bot.db")
    return conn, conn.cursor()

def setup_db():
    conn, cursor = db_connect()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, full_name TEXT, vip_expires TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, title TEXT, part TEXT, file_id TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

setup_db()

def get_setting(key):
    conn, cursor = db_connect()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def set_setting(key, value):
    conn, cursor = db_connect()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def is_vip(user_id):
    if user_id == ADMIN_ID:
        return True
    conn, cursor = db_connect()
    cursor.execute("SELECT vip_expires FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    if res and res[0]:
        expire_date = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S")
        if expire_date > datetime.now():
            return True
    return False

async def check_subscription(user_id):
    if is_vip(user_id):
        return True
    channel = get_setting("required_channel")
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass
    return False

def main_menu(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔍 Kino qidirish (Kod orqali)"))
    kb.add(KeyboardButton("💎 VIP Sotib olish"), KeyboardButton("👤 Kabinet"))
    if user_id == ADMIN_ID:
        kb.add(KeyboardButton("👑 Admin Panel"))
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Kino qo'shish"), KeyboardButton("🗑 Kinoni o'chirish"))
    kb.add(KeyboardButton("📢 Majburiy obuna sozlash"), KeyboardButton("💳 Karta raqam qo'shish"))
    kb.add(KeyboardButton("📊 Statistika"), KeyboardButton("🔙 Asosiy menyu"))
    return kb

class MovieState(StatesGroup):
    code = State()
    title = State()
    part = State()
    file_id = State()

class AdminState(StatesGroup):
    channel = State()
    card = State()
    del_code = State()

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    conn, cursor = db_connect()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?, ?)", 
                   (user_id, message.from_user.full_name))
    conn.commit()
    conn.close()

    if not await check_subscription(user_id):
        channel = get_setting("required_channel")
        kb = InlineKeyboardMarkup(row_width=1)
        if channel:
            kb.add(InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=f"https://t.me/{channel.replace('@', '')}"))
        kb.add(InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub"))
        await message.answer("⚠️ Botdan to'liq foydalanish uchun quyidagi homiy kanalimizga obuna bo'ling va tugmani bosing:", reply_markup=kb)
        return

    await message.answer("Assalomu alaykum! Kino kodini yuboring yoki quyidagi tugmalardan foydalaning:", reply_markup=main_menu(user_id))

@dp.callback_query_handler(text="check_sub")
async def callback_check_sub(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await call.message.answer("Rahmat! Obuna tasdiqlandi. Marhamat, kino kodini yuboring:", reply_markup=main_menu(call.from_user.id))
    else:
        await call.answer("Siz hali kanalga a'zo bo'lmadingiz yoki obuna topilmadi!", show_alert=True)

@dp.message_handler(text="🔙 Asosiy menyu")
async def back_to_main(message: types.Message):
    await message.answer("Asosiy menyu:", reply_markup=main_menu(message.from_user.id))

@dp.message_handler(text="👤 Kabinet")
async def profile(message: types.Message):
    user_id = message.from_user.id
    conn, cursor = db_connect()
    cursor.execute("SELECT vip_expires FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    
    vip_status = "❌ Yo'q"
    if is_vip(user_id):
        if user_id == ADMIN_ID:
            vip_status = "👑 Admin (Cheksiz VIP)"
        else:
            vip_status = f"✅ Faol ({res[0]})"

    text = f"👤 Foydalanuvchi: {message.from_user.full_name}\n🆔 ID: {user_id}\n💎 VIP Status: {vip_status}"
    await message.answer(text)

@dp.message_handler(text="💎 VIP Sotib olish")
async def buy_vip(message: types.Message):
    card = get_setting("card_number") or "Admin tomonidan karta kiritilmagan."
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("1 oylik - 10,000 so'm", callback_data="vip_1"),
        InlineKeyboardButton("2 oylik - 18,000 so'm", callback_data="vip_2"),
        InlineKeyboardButton("3 oylik - 25,000 so'm", callback_data="vip_3"),
        InlineKeyboardButton("6 oylik - 45,000 so'm", callback_data="vip_6"),
        InlineKeyboardButton("12 oylik - 80,000 so'm", callback_data="vip_12"),
    )
    text = f"💎 **VIP Obuna Afzalliklari:**\n- Majburiy obunadan to'liq ozod bo'lasiz!\n- Kinolar 2x tezlikda yuklanadi va cheklovlar yo'q.\n\n💳 **To'lov uchun karta:**\n`{card}`\n\nPulni o'tkazgach, chekni va o'zingizning ID raqamingizni adminga yuboring:"
    await message.answer(text, reply_markup=kb)

@dp.callback_query_handler(text_startswith="vip_")
async def process_vip_buy(call: types.CallbackQuery):
    months = int(call.data.split("_")[1])
    await call.message.answer(f"Siz {months} oylik VIP tarifini tanladingiz. Iltimos to'lov chekini va ID raqamingizni @{ADMIN_ID} ga yuboring.")

@dp.message_handler(text="🔍 Kino qidirish (Kod orqali)")
async def search_movie_prompt(message: types.Message):
    await message.answer("Marhamat, kino kodini yuboring (Masalan: `101`):")

@dp.message_handler(lambda message: message.text.isdigit() or len(message.text.split()) == 1)
async def get_movie_by_code(message: types.Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        channel = get_setting("required_channel")
        kb = InlineKeyboardMarkup(row_width=1)
        if channel:
            kb.add(InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=f"https://t.me/{channel.replace('@', '')}"))
        kb.add(InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub"))
        await message.answer("⚠️ Botdan foydalanish uchun avval kanalga obuna bo'ling!", reply_markup=kb)
        return

    code = message.text.strip()
    conn, cursor = db_connect()
    cursor.execute("SELECT title, part, file_id FROM movies WHERE code = ?", (code,))
    movies = cursor.fetchall()
    conn.close()

    if not movies:
        await message.answer("❌ Bunday kodli kino topilmadi.")
        return

    title = movies[0][0]
    if len(movies) == 1:
        await message.answer_video(
            movies[0][2], 
            caption=f"🎬 {title}\n🤖 Bot: @{message.bot.username}", 
            protect_content=True
        )
    else:
        kb = InlineKeyboardMarkup(row_width=3)
        for m in movies:
            part_name = m[1]
            kb.insert(InlineKeyboardButton(f"{part_name}-qism", callback_data=f"movie_{code}_{part_name}"))
        await message.answer(f"🎬 <b>{title}</b>\n\nQismni tanlang:", reply_markup=kb)

@dp.callback_query_handler(text_startswith="movie_")
async def send_movie_part(call: types.CallbackQuery):
    _, code, part = call.data.split("_")
    conn, cursor = db_connect()
    cursor.execute("SELECT title, file_id FROM movies WHERE code = ? AND part = ?", (code, part))
    movie = cursor.fetchone()
    conn.close()

    if movie:
        await call.message.answer_video(
            movie[1], 
            caption=f"🎬 {movie[0]} ({part}-qism)", 
            protect_content=True
        )
    else:
        await call.answer("Kino qismi topilmadi!", show_alert=True)

@dp.message_handler(text="👑 Admin Panel")
async def admin_panel_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Xush kelibsiz, Admin!", reply_markup=admin_menu())

@dp.message_handler(text="📢 Majburiy obuna sozlash")
async def set_channel_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await AdminState.channel.set()
    await message.answer("Kanal usernameni yuboring (Masalan: `@kino_kanal`):", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=AdminState.channel)
async def set_channel_save(message: types.Message, state: FSMContext):
    set_setting("required_channel", message.text.strip())
    await state.finish()
    await message.answer("✅ Majburiy obuna kanali saqlandi!", reply_markup=admin_menu())

@dp.message_handler(text="💳 Karta raqam qo'shish")
async def set_card_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await AdminState.card.set()
    await message.answer("Plastik karta raqami va egasining F.I.Sh ni kiriting:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=AdminState.card)
async def set_card_save(message: types.Message, state: FSMContext):
    set_setting("card_number", message.text.strip())
    await state.finish()
    await message.answer("✅ Karta muvaffaqiyatli saqlandi!", reply_markup=admin_menu())

@dp.message_handler(text="📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn, cursor = db_connect()
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT code) FROM movies")
    movies_count = cursor.fetchone()[0]
    conn.close()
    await message.answer(f"📊 **Bot statistikasi:**\n\n👤 Foydalanuvchilar: {users_count} ta\n🎬 Kinolar soni: {movies_count} ta")

@dp.message_handler(text="➕ Kino qo'shish")
async def add_movie_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await MovieState.code.set()
    await message.answer("Kino uchun maxsus kod kiriting (masalan: 101):", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=MovieState.code)
async def process_code(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await MovieState.next()
    await message.answer("Kino nomini kiriting:")

@dp.message_handler(state=MovieState.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await MovieState.next()
    await message.answer("Kino qismini kiriting (Masalan: 1 yoki 1-qism):")

@dp.message_handler(state=MovieState.part)
async def process_part(message: types.Message, state: FSMContext):
    await state.update_data(part=message.text.strip())
    await MovieState.next()
    await message.answer("Kino videosini (faylini) yuboring:")

@dp.message_handler(content_types=['video', 'document'], state=MovieState.file_id)
async def process_file(message: types.Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    data = await state.get_data()
    
    conn, cursor = db_connect()
    cursor.execute("INSERT INTO movies (code, title, part, file_id) VALUES (?, ?, ?, ?)",
                   (data['code'], data['title'], data['part'], file_id))
    conn.commit()
    conn.close()

    await state.finish()
    await message.answer(f"✅ Kino muvaffaqiyatli qo'shildi!\nKod: {data['code']}", reply_markup=admin_menu())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
      
