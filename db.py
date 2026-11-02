import sqlite3

class Database:
    def __init__(self, db_file="bot.db"):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        # Foydalanuvchilar jadvali
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY
            )
        """)
        
        # Kinolar jadvali (kino kodi, telegram fayl ID si va nomi)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                file_id TEXT,
                title TEXT
            )
        """)
        self.connection.commit()

    # 1. Botga yangi foydalanuvchi qo'shish
    def add_user(self, user_id):
        self.cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        self.connection.commit()

    # 2. Barcha foydalanuvchilar ro'yxatini olish (reklama tarqatish uchun)
    def get_users(self):
        self.cursor.execute("SELECT user_id FROM users")
        return self.cursor.fetchall()

    # 3. Bazaga yangi kino qo'shish
    def add_movie(self, code, file_id, title):
        self.cursor.execute(
            "INSERT OR REPLACE INTO movies (code, file_id, title) VALUES (?, ?, ?)", 
            (code, file_id, title)
        )
        self.connection.commit()

    # 4. Kino kodi bo'yicha kinoni qidirib topish
    def get_movie(self, code):
        self.cursor.execute("SELECT file_id, title FROM movies WHERE code = ?", (code,))
        return self.cursor.fetchone()

    # Bazani yopish
    def close(self):
        self.connection.close()
      
