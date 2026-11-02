from aiogram.fsm.state import State, StatesGroup

# Kino qo'shish jarayoni uchun holatlar (States)
class AddMovieState(StatesGroup):
    code = State()       # Kino kodi kutilayotgan holat
    video = State()      # Kino videosi kutilayotgan holat
    title = State()      # Kino nomi kutilayotgan holat
