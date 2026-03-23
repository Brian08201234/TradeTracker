import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'users.db')

def get_db():
    """獲取資料庫連接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化資料庫"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_paid INTEGER DEFAULT 0,
            subscription_id TEXT,
            subscription_status TEXT DEFAULT 'inactive',
            subscription_end TIMESTAMP,
            default_currency TEXT DEFAULT 'USD',
            timezone TEXT DEFAULT 'UTC'
        )
    ''')
    
    conn.commit()
    conn.close()

class User:
    """用戶模型"""
    
    def __init__(self, id=None, username=None, email=None, password_hash=None, 
                 created_at=None, is_paid=0, subscription_id=None, 
                 subscription_status='inactive', subscription_end=None,
                 default_currency='USD', timezone='UTC'):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.is_paid = is_paid
        self.subscription_id = subscription_id
        self.subscription_status = subscription_status
        self.subscription_end = subscription_end
        self.default_currency = default_currency
        self.timezone = timezone
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def display_id(self):
        """返回隨機的8位數顯示ID"""
        import hashlib
        hash_val = hashlib.md5(str(self.id).encode()).hexdigest()
        num = int(hash_val[:8], 16) % 100000000
        return f"{num:08d}"
    
    @staticmethod
    def get(user_id):
        """根據 ID 獲取用戶"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            row_dict = dict(row)
            if row_dict.get('created_at') and isinstance(row_dict['created_at'], str):
                try:
                    row_dict['created_at'] = datetime.strptime(row_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            return User(**row_dict)
        return None
    
    @staticmethod
    def find_by_username(username):
        """根據用戶名查找"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return User(**dict(row))
        return None
    
    @staticmethod
    def find_by_email(email):
        """根據郵箱查找"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return User(**dict(row))
        return None
    
    @staticmethod
    def create(username, email, password):
        """創建新用戶"""
        conn = get_db()
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return User.get(user_id)
    
    def save(self):
        """保存用戶"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET username = ?, email = ?, is_paid = ?, subscription_id = ?, 
                subscription_status = ?, subscription_end = ?,
                default_currency = ?, timezone = ?
            WHERE id = ?
        """, (self.username, self.email, self.is_paid, self.subscription_id, 
              self.subscription_status, self.subscription_end,
              self.default_currency, self.timezone, self.id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def query_all():
        """獲取所有用戶"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [User(**dict(row)) for row in rows]

# 初始化資料庫
init_db()
