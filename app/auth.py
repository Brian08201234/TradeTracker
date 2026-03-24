from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, db
from app.TradeTracker import TradeAnalyzer
import os

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            user_data_dir = f'user_data/{user.id}'
            os.makedirs(user_data_dir, exist_ok=True)
            
            analyzer = TradeAnalyzer(data_dir=user_data_dir)
            
            if not analyzer.accounts:
                analyzer.create_account(f"{user.username}'s Account", 0, user.default_currency)
            
            if analyzer.accounts:
                session['current_account'] = list(analyzer.accounts.keys())[0]
            
            flash(f'Welcome back, {username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            user_data_dir = f'user_data/{user.id}'
            os.makedirs(user_data_dir, exist_ok=True)
            
            flash('Registration successful! Please upgrade to Pro to start trading.', 'info')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
    
    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    email = request.form.get('email')
    default_currency = request.form.get('default_currency', 'USD')
    
    if email and email != current_user.email:
        if User.query.filter_by(email=email).first():
            flash('Email already in use', 'danger')
            return redirect(url_for('auth.profile'))
        current_user.email = email
    
    current_user.default_currency = default_currency
    db.session.commit()
    
    flash('Profile updated successfully', 'success')
    return redirect(url_for('auth.profile'))

@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'danger')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('auth.profile'))
    
    if len(new_password) < 6:
        flash('Password must be at least 6 characters', 'danger')
        return redirect(url_for('auth.profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Password changed successfully', 'success')
    return redirect(url_for('auth.profile'))

@bp.route('/change-username', methods=['POST'])
@login_required
def change_username():
    """修改用戶名"""
    new_username = request.form.get('new_username')
    
    if not new_username:
        flash('Username cannot be empty', 'danger')
        return redirect(url_for('auth.profile'))
    
    existing_user = User.find_by_username(new_username)
    if existing_user and existing_user.id != current_user.id:
        flash('Username already taken', 'danger')
        return redirect(url_for('auth.profile'))
    
    current_user.username = new_username
    db.session.commit()
    
    flash('Username updated successfully!', 'success')
    return redirect(url_for('auth.profile'))
