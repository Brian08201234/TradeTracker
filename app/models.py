import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_paid = db.Column(db.Boolean, default=False)
    subscription_id = db.Column(db.String(100))
    subscription_status = db.Column(db.String(20), default='inactive')
    subscription_end = db.Column(db.DateTime)
    default_currency = db.Column(db.String(3), default='USD')
    timezone = db.Column(db.String(50), default='UTC')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return str(self.id)
    
    def has_access(self):
        return self.is_paid
    
    def display_id(self):
        import hashlib
        hash_val = hashlib.md5(str(self.id).encode()).hexdigest()
        num = int(hash_val[:8], 16) % 100000000
        return f"{num:08d}"
    
    def __repr__(self):
        return f'<User {self.username}>'
