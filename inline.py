from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. Majburiy obuna uchun kanalga o'tish tugmasi
def check_sub_keyboard(channel_username: str):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{channel_username}")
            ],
            [
                InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")
            ]
        ]
    )
    return keyboard

# 2. Admin uchun asosiy menyu tugmalari
def admin_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="add_movie"),
                InlineKeyboardButton(text="🗑 Kino o'chirish", callback_data="delete_movie")
            ],
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="stats"),
                InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="send_ads")
            ]
        ]
    )
    return keyboard
  
