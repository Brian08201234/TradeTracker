from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager, current_user
import os
import stripe
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

login_manager = LoginManager()

STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
stripe.api_key = STRIPE_SECRET_KEY

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
    app.config['DATA_DIR'] = 'user_data'
    app.config['STRIPE_PUBLISHABLE_KEY'] = STRIPE_PUBLISHABLE_KEY
    app.config['STRIPE_SECRET_KEY'] = STRIPE_SECRET_KEY
    
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please login to access this page'
    
    from app import routes, auth
    app.register_blueprint(routes.bp)
    app.register_blueprint(auth.bp)
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.get(int(user_id))

def require_paid(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        if current_user.username == 'admin':
            return f(*args, **kwargs)
        
        if not current_user.is_paid:
            flash('This feature requires a Pro subscription. Please upgrade to continue.', 'warning')
            return redirect(url_for('main.pricing'))
        
        return f(*args, **kwargs)
    return decorated_function
