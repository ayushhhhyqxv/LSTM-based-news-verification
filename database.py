import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('chat_app.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        truth_probability REAL DEFAULT 1.0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ('Admin', 'admin@example.com', generate_password_hash('admin123'))
        )
    except sqlite3.IntegrityError:
        pass
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('chat_app.db')
    conn.row_factory = sqlite3.Row
    return conn