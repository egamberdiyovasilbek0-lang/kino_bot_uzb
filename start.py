from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from db import Database

# Router yaratamiz
router = Router()
db = Database()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    
    # Foydalanuvchini bazaga qo'shish
    db.add_user(user_id)
    
    # Foydalanuvchiga xabar yuborish
    await message.answer(
        f"Assalomu alaykum, {full_name}!\n\n"
        f"🎬 Kino botimizga xush kelibsiz. Botdan foydalanish uchun kino kodini yuboring (masalan: `1`, `10` va hokazo)."
    )
  
