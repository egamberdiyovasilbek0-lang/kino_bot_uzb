from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import AddMovieState
from db import Database

router = Router()
db = Database()

# 1. "Kino qo'shish" tugmasi bosilganda
router.callback_query(F.data == "add_movie")
async def start_add_movie(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🎬 Yangi kino kodini kiriting (masalan: 101):")
    await state.set_state(AddMovieState.code)
    await callback.answer()

# 2. Kino kodini qabul qilib, videoni so'rash
async def process_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("🎥 Endi kino videosini (yoki faylini) yuboring:")
    await state.set_state(AddMovieState.video)

# 3. Videoni qabul qilib, nomini so'rash
async def process_video(message: Message, state: FSMContext):
    if not message.video:
        await message.answer("❌ Iltimos, faqat video fayl yuboring!")
        return
    
    file_id = message.video.file_id
    await state.update_data(file_id=file_id)
    await message.answer("✍️ Endi kino nomini kiriting:")
    await state.set_state(AddMovieState.title)

# 4. Kino nomini olib, bazaga saqlash
async def process_title(message: Message, state: FSMContext):
    title = message.text
    data = await state.get_data()
    
    code = data.get("code")
    file_id = data.get("file_id")
    
    # Bazaga qo'shamiz
    db.add_movie(code, file_id, title)
    
    await message.answer(f"✅ Kino muvaffaqiyatli qo'shildi!\n\nKodi: {code}\nNomi: {title}")
    await state.clear()
  
