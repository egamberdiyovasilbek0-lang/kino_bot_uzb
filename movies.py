from aiogram import Router, F
from aiogram.types import Message
from db import Database

# Router va bazani ulaymiz
router = Router()
db = Database()

@router.message(F.text)
async def send_movie(message: Message):
    code = message.text.strip()
    
    # Bazadan kino kodi bo'yicha ma'lumotni qidiramiz
    movie = db.get_movie(code)
    
    if movie:
        file_id, title = movie
        # Agar kino topilsa, videoni yuboramiz
        await message.answer_video(
            video=file_id,
            caption=f"🎬 Nomi: {title}\n\nKino kodi: {code}"
        )
    else:
        # Agar bunday kodli kino bazada bo'lmasa
        await message.answer("❌ Kechirasiz, bu kod bo'yicha hech qanday kino topilmadi. Iltimos, boshqa kod kiriting.")
      
