from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from flask_login import login_required, current_user
from app import require_paid
from app.TradeTracker import TradeAnalyzer
import os

try:
    # pandas removed for deployment
    # numpy removed for deployment
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not available")

# numpy removed for deployment
from datetime import datetime
import calendar as cal
from werkzeug.utils import secure_filename
from PIL import Image
import hashlib

bp = Blueprint("main", __name__)

# 獲取專案根目錄
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 圖片上傳配置
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(filepath, max_size=(800, 800), quality=85):
    try:
        img = Image.open(filepath)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(filepath, 'JPEG', quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"Image compression error: {e}")
        return False

def get_analyzer():
    data_dir = os.path.join(PROJECT_ROOT, f'user_data/{current_user.id}')
    os.makedirs(data_dir, exist_ok=True)
    return TradeAnalyzer(data_dir=data_dir)

# ==================== 計算函數 ====================


def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """計算夏普比率（簡化版）"""
    if len(returns) < 2:
        return 0
    filtered = [r for r in returns if r != 0]
    if len(filtered) < 2:
        return 0
    mean_return = sum(filtered) / len(filtered)
    # 計算標準差
    variance = sum((r - mean_return) ** 2 for r in filtered) / len(filtered)
    std_return = variance ** 0.5
    if std_return == 0:
        return 0
    sharpe = (mean_return - risk_free_rate/252) / std_return * (252 ** 0.5)
    return round(sharpe, 2)

def calculate_max_drawdown(returns):
    if len(returns) < 2:
        return 0
    cumulative = 0
    peak = 0
    max_dd = 0
    for r in returns:
        cumulative += r
        if cumulative > peak:
            peak = cumulative
        if peak > 0:
            dd = (peak - cumulative) / peak
            if dd > max_dd:
                max_dd = dd
    return round(max_dd * 100, 2)

def calculate_profit_factor(returns):
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0
    return round(gross_profit / gross_loss, 2)

# ==================== 路由 ====================

@bp.route("/")
@login_required
@require_paid
def index():
    analyzer = get_analyzer()
    stats = {}
    performance_data = {"labels": [], "values": []}
    
    if session.get("current_account"):
        account_id = session["current_account"]
        if account_id in analyzer.accounts:
            account = analyzer.accounts[account_id]
            account_stats = analyzer.get_account_stats(account_id)
            stats = {
                "account_name": account.name,
                "balance": account.current_balance,
                "total_pnl": account_stats["total_pnl"],
                "total_trades": account_stats["total_trades"],
                "win_rate": account_stats["win_rate"]
            }
            
            account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
            if os.path.exists(account_file):
                try:
                    df = pd.read_csv(account_file)
                    if len(df) > 0:
                        df = df.sort_values('date')
                        cumulative = 0
                        for _, row in df.iterrows():
                            cumulative += float(row['net_pnl'])
                            performance_data["values"].append(cumulative)
                            date = row['date'][:10] if isinstance(row['date'], str) else str(row['date'])[:10]
                            performance_data["labels"].append(date)
                except Exception as e:
                    print(f"Error loading equity curve: {e}")
    
    return render_template("dashboard.html", stats=stats, performance_data=performance_data)

@bp.route("/accounts")
@login_required
@require_paid
def accounts():
    analyzer = get_analyzer()
    accounts_list = []
    for acc_id, acc in analyzer.accounts.items():
        stats = analyzer.get_account_stats(acc_id)
        accounts_list.append({
            "id": acc_id,
            "name": acc.name,
            "balance": acc.current_balance,
            "currency": acc.currency,
            "total_trades": stats["total_trades"],
            "total_pnl": stats["total_pnl"]
        })
    return render_template("accounts.html", accounts=accounts_list)

@bp.route("/create_account", methods=["POST"])
@login_required
def create_account():
    name = request.form["name"]
    initial_balance = float(request.form.get("initial_balance", 0))
    currency = request.form.get("currency", current_user.default_currency)
    notes = request.form.get("notes", "")
    analyzer = get_analyzer()
    analyzer.create_account(name, initial_balance, currency, notes)
    return redirect(url_for("main.accounts"))

@bp.route("/switch_account", methods=["POST"])
@login_required
def switch_account():
    account_id = request.form["account_id"]
    session["current_account"] = account_id
    return redirect(url_for("main.index"))


@bp.route("/add_trade", methods=["GET", "POST"])
@login_required
def add_trade():
    if request.method == "POST":
        pnl = float(request.form["pnl"])
        symbol = request.form.get("symbol", "")
        direction = request.form.get("direction", "")
        fees = float(request.form.get("fees", 0))
        notes = request.form.get("notes", "")
        tags = request.form.get("tags", "")
        emotion = request.form.get("emotion", "")
        emotion_notes = request.form.get("emotion_notes", "")
        
        screenshot_path = None
        if 'screenshot' in request.files:
            file = request.files['screenshot']
            if file and file.filename and allowed_file(file.filename):
                user_upload_dir = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", "screenshots")
                os.makedirs(user_upload_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = secure_filename(file.filename)
                filename = f"{timestamp}_{hashlib.md5(safe_filename.encode()).hexdigest()[:8]}.jpg"
                filepath = os.path.join(user_upload_dir, filename)
                file.save(filepath)
                compress_image(filepath)
                screenshot_path = filename
        
        analyzer = get_analyzer()
        account_id = session.get("current_account")
        
        if account_id:
            if screenshot_path:
                if notes:
                    notes = notes + " - 📸 Screenshot: " + screenshot_path
                else:
                    notes = "📸 Screenshot: " + screenshot_path
            analyzer.add_trade(pnl, symbol, direction, fees, notes, account_id, tags, emotion, emotion_notes)
            flash('Trade added successfully!', 'success')
            return redirect(url_for("main.index"))
    
    return render_template("add_trade.html")

@bp.route("/view_trades")
@login_required
@require_paid
def view_trades():
    analyzer = get_analyzer()
    trades = []
    account_id = session.get("current_account")
    
    if account_id:
        account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
        if os.path.exists(account_file):
            df = pd.read_csv(account_file)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)
            trades = df.head(50).to_dict('records')
            for trade in trades:
                if isinstance(trade['date'], pd.Timestamp):
                    trade['date'] = trade['date'].strftime('%Y-%m-%d %H:%M')
                trade['pnl'] = float(trade['pnl'])
                trade['fees'] = float(trade['fees'])
                trade['net_pnl'] = float(trade['net_pnl'])
    
    return render_template("trades.html", trades=trades)

@bp.route("/calendar")
@login_required
@require_paid
def calendar():
    now = datetime.now()
    return render_template("calendar.html", year=now.year, month=now.month)

@bp.route("/api/calendar-data/<int:year>/<int:month>")
@login_required
def calendar_data(year, month):
    try:
        analyzer = get_analyzer()
        account_id = session.get("current_account")
        if not account_id:
            return jsonify({"error": "No account selected"}), 400
        
        account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
        _, days_in_month = cal.monthrange(year, month)
        daily_data = {day: {"pnl": 0, "trades": [], "count": 0} for day in range(1, days_in_month + 1)}
        
        if os.path.exists(account_file):
            df = pd.read_csv(account_file)
            df['date'] = pd.to_datetime(df['date'])
            mask = (df['date'].dt.year == year) & (df['date'].dt.month == month)
            month_trades = df[mask]
            
            for _, trade in month_trades.iterrows():
                day = trade['date'].day
                daily_data[day]["pnl"] += trade['net_pnl']
                daily_data[day]["trades"].append({
                    "id": int(trade['id']),
                    "symbol": str(trade['symbol']),
                    "direction": str(trade['direction']),
                    "pnl": float(trade['pnl']),
                    "fees": float(trade['fees']),
                    "net_pnl": float(trade['net_pnl']),
                    "notes": str(trade['notes']),
                    "time": trade['date'].strftime('%H:%M')
                })
                daily_data[day]["count"] += 1
        
        result = []
        for day in range(1, days_in_month + 1):
            result.append({
                "day": day,
                "pnl": daily_data[day]["pnl"],
                "count": daily_data[day]["count"],
                "trades": daily_data[day]["trades"]
            })
        
        return jsonify({
            "year": year,
            "month": month,
            "month_name": cal.month_name[month],
            "days": result
        })
    except Exception as e:
        print(f"Calendar data error: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/api/advanced-metrics")
@login_required
@require_paid
def advanced_metrics():
    try:
        analyzer = get_analyzer()
        account_id = session.get("current_account")
        
        if not account_id:
            return jsonify({"sharpe_ratio": 0, "max_drawdown": 0, "profit_factor": 0})
        
        account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
        returns = []
        if os.path.exists(account_file):
            df = pd.read_csv(account_file)
            returns = df['net_pnl'].tolist()
            returns = [float(r) for r in returns]
        
        sharpe = calculate_sharpe_ratio(returns)
        max_dd = calculate_max_drawdown(returns)
        pf = calculate_profit_factor(returns)
        
        return jsonify({
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "profit_factor": pf
        })
    except Exception as e:
        print(f"Advanced metrics error: {e}")
        return jsonify({"sharpe_ratio": 0, "max_drawdown": 0, "profit_factor": 0})

@bp.route("/delete_trade/<int:trade_id>", methods=["POST"])
@login_required
def delete_trade(trade_id):
    try:
        analyzer = get_analyzer()
        account_id = session.get("current_account")
        if not account_id:
            flash('No account selected', 'danger')
            return redirect(url_for('main.view_trades'))
        
        account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
        if os.path.exists(account_file):
            df = pd.read_csv(account_file)
            if trade_id not in df['id'].values:
                flash('Trade not found', 'danger')
                return redirect(url_for('main.view_trades'))
            trade_to_delete = df[df['id'] == trade_id].iloc[0]
            pnl_impact = trade_to_delete['net_pnl']
            df = df[df['id'] != trade_id]
            df['id'] = range(1, len(df) + 1)
            df.to_csv(account_file, index=False)
            analyzer.accounts[account_id].current_balance -= pnl_impact
            analyzer.save_accounts()
            flash(f'Trade #{trade_id} deleted successfully', 'success')
        else:
            flash('No trades found', 'danger')
    except Exception as e:
        flash(f'Error deleting trade: {str(e)}', 'danger')
    return redirect(url_for('main.view_trades'))

@bp.route("/delete_account/<account_id>", methods=["POST"])
@login_required
def delete_account(account_id):
    try:
        analyzer = get_analyzer()
        if account_id not in analyzer.accounts:
            flash('Account not found', 'danger')
            return redirect(url_for('main.accounts'))
        account_name = analyzer.accounts[account_id].name
        confirm = request.form.get('confirm') == 'YES'
        if not confirm:
            flash('Please type YES to confirm deletion', 'warning')
            return redirect(url_for('main.accounts'))
        is_current = (session.get('current_account') == account_id)
        account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
        if os.path.exists(account_file):
            os.remove(account_file)
        del analyzer.accounts[account_id]
        analyzer.save_accounts()
        if is_current:
            session.pop('current_account', None)
            if analyzer.accounts:
                first_account = list(analyzer.accounts.keys())[0]
                session['current_account'] = first_account
                flash(f'Account {account_name} deleted. Switched to {analyzer.accounts[first_account].name}', 'info')
            else:
                flash(f'Account {account_name} deleted. No accounts left.', 'warning')
        else:
            flash(f'Account {account_name} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting account: {str(e)}', 'danger')
    return redirect(url_for('main.accounts'))

@bp.route("/delete_all_trades", methods=["POST"])
@login_required
def delete_all_trades():
    try:
        analyzer = get_analyzer()
        account_id = session.get("current_account")
        if not account_id:
            flash('No account selected', 'danger')
            return redirect(url_for('main.view_trades'))
        confirm = request.form.get('confirm') == 'YES'
        if not confirm:
            flash('Please type YES to confirm deletion', 'warning')
            return redirect(url_for('main.view_trades'))
        account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
        if os.path.exists(account_file):
            empty_df = pd.DataFrame(columns=['id', 'date', 'symbol', 'direction', 'pnl', 'fees', 'net_pnl', 'notes', 'tags'])
            empty_df.to_csv(account_file, index=False)
            analyzer.accounts[account_id].current_balance = analyzer.accounts[account_id].initial_balance
            analyzer.save_accounts()
            flash('All trades deleted. Balance reset.', 'success')
        else:
            flash('No trades found', 'info')
    except Exception as e:
        flash(f'Error deleting trades: {str(e)}', 'danger')
    return redirect(url_for('main.view_trades'))

@bp.route("/screenshots/<path:filename>")
@login_required
def serve_screenshot(filename):
    user_upload_dir = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", "screenshots")
    file_path = os.path.join(user_upload_dir, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path, mimetype='image/jpeg')


@bp.route("/strategy-analysis")
@login_required
@require_paid
def strategy_analysis():
    analyzer = get_analyzer()
    account_id = session.get("current_account")
    
    if not account_id:
        flash('Please select an account first', 'warning')
        return redirect(url_for('main.accounts'))
    
    account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
    
    strategies = {}
    if os.path.exists(account_file):
        df = pd.read_csv(account_file)
        
        for _, row in df.iterrows():
            tags = row.get('tags', '')
            if pd.notna(tags) and tags:
                for tag in str(tags).replace(',', ' ').split():
                    tag = tag.strip()
                    if tag:
                        if tag not in strategies:
                            strategies[tag] = {
                                'trades': [],
                                'total_pnl': 0,
                                'count': 0,
                                'winning': 0
                            }
                        net_pnl = float(row['net_pnl'])
                        strategies[tag]['trades'].append(net_pnl)
                        strategies[tag]['total_pnl'] += net_pnl
                        strategies[tag]['count'] += 1
                        if net_pnl > 0:
                            strategies[tag]['winning'] += 1
    
    for tag, data in strategies.items():
        returns = data['trades']
        data['win_rate'] = round(data['winning'] / data['count'] * 100, 1) if data['count'] > 0 else 0
        data['sharpe'] = calculate_sharpe_ratio(returns)
        data['avg_pnl'] = round(data['total_pnl'] / data['count'], 2) if data['count'] > 0 else 0
        data['max_drawdown'] = calculate_max_drawdown(returns)
        pf = calculate_profit_factor(returns)
        # 將 inf 轉為 999999 以便在模板中處理
        data['profit_factor'] = 999999 if pf == float('inf') else pf
    
    return render_template("strategy_analysis.html", strategies=strategies)

@bp.route("/emotion-analysis")
@login_required
@require_paid
def emotion_analysis():
    """情緒分析頁面"""
    analyzer = get_analyzer()
    account_id = session.get("current_account")
    
    if not account_id:
        flash('Please select an account first', 'warning')
        return redirect(url_for('main.accounts'))
    
    account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
    
    # 情緒統計
    emotions = {}
    emotion_pnl = {}
    
    if os.path.exists(account_file):
        df = pd.read_csv(account_file)
        
        for _, row in df.iterrows():
            emotion = row.get('emotion', '')
            if pd.notna(emotion) and emotion:
                net_pnl = float(row['net_pnl'])
                
                if emotion not in emotions:
                    emotions[emotion] = {
                        'count': 0,
                        'total_pnl': 0,
                        'winning': 0,
                        'trades': []
                    }
                
                emotions[emotion]['count'] += 1
                emotions[emotion]['total_pnl'] += net_pnl
                emotions[emotion]['trades'].append(net_pnl)
                if net_pnl > 0:
                    emotions[emotion]['winning'] += 1
    
    # 計算每個情緒的指標
    emotion_stats = {}
    for emotion, data in emotions.items():
        returns = data['trades']
        emotion_stats[emotion] = {
            'count': data['count'],
            'total_pnl': data['total_pnl'],
            'win_rate': round(data['winning'] / data['count'] * 100, 1) if data['count'] > 0 else 0,
            'avg_pnl': round(data['total_pnl'] / data['count'], 2) if data['count'] > 0 else 0,
            'sharpe': calculate_sharpe_ratio(returns),
            'max_drawdown': calculate_max_drawdown(returns)
        }
    
    # 情緒映射顯示名稱
    emotion_names = {
        'calm': '😌 Calm',
        'confident': '😎 Confident',
        'excited': '🤩 Excited',
        'anxious': '😰 Anxious',
        'fearful': '😨 Fearful',
        'greedy': '🤑 Greedy',
        'impatient': '⏰ Impatient',
        'hesitant': '🤔 Hesitant',
        'frustrated': '😤 Frustrated',
        'regretful': '😞 Regretful'
    }
    
    return render_template("emotion_analysis.html", emotion_stats=emotion_stats, emotion_names=emotion_names)

import stripe

from flask import current_app

@bp.route("/pricing")
def pricing():
    """定價頁面"""
    return render_template("pricing.html")

@bp.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    """創建 Stripe 結帳會話"""
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'TradeTracker Pro',
                        'description': 'Unlimited access to all trading journal features',
                    },
                    'unit_amount': 299,
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('main.payment_success', _external=True),
            cancel_url=url_for('main.pricing', _external=True),
            client_reference_id=str(current_user.id),
            customer_email=current_user.email,
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('main.pricing'))

@bp.route("/subscription-success")
@login_required
def subscription_success():
    """訂閱成功回調"""
    session_id = request.args.get('session_id')
    if session_id:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            subscription = stripe.Subscription.retrieve(checkout_session.subscription)
            
            current_user.is_paid = True
            current_user.subscription_id = subscription.id
            current_user.subscription_status = subscription.status
            
            
            flash('Subscription successful! You now have full access.', 'success')
        except Exception as e:
            flash(f'Error verifying subscription: {str(e)}', 'danger')
    else:
        flash('Subscription successful!', 'success')
    
    return redirect(url_for('main.index'))


def require_paid(f):
    """裝飾器：強制要求付費，否則跳轉到定價頁面"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('auth.login'))
        
        # 管理員可以免費訪問所有頁面
        if current_user.username == 'admin':
            return f(*args, **kwargs)
        
        if not current_user.is_paid:
            flash('This feature requires a Pro subscription. Please upgrade to continue.', 'warning')
            return redirect(url_for('main.pricing'))
        
        return f(*args, **kwargs)
    return decorated_function

@bp.route("/api/equity-curve")
@login_required
def equity_curve():
    """API 返回資金曲線數據"""
    try:
        analyzer = get_analyzer()
        account_id = session.get("current_account")
        
        if not account_id:
            return jsonify({"labels": [], "values": []})
        
        account_file = os.path.join(PROJECT_ROOT, f"user_data/{current_user.id}", f"{account_id}_trades.csv")
        
        labels = []
        values = []
        if os.path.exists(account_file):
            df = pd.read_csv(account_file)
            if len(df) > 0:
                df = df.sort_values('date')
                cumulative = 0
                for _, row in df.iterrows():
                    cumulative += float(row['net_pnl'])
                    values.append(cumulative)
                    # 格式化日期顯示
                    date = row['date'][:10] if isinstance(row['date'], str) else str(row['date'])[:10]
                    labels.append(date)
        
        return jsonify({
            "labels": labels,
            "values": values
        })
        
    except Exception as e:
        print(f"Equity curve error: {e}")
        return jsonify({"labels": [], "values": []})

    
    print(f"Subscription success callback received. Session ID: {session_id}")
    
    if not session_id:
        flash('Payment successful!', 'success')
        return redirect(url_for('main.index'))
    
    try:
        # 獲取 Stripe 會話信息
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        print(f"Checkout session retrieved: {checkout_session.id}")
        
        # 更新用戶為付費
        current_user.is_paid = True
        
        # 獲取訂閱信息
        if checkout_session.subscription:
            subscription = stripe.Subscription.retrieve(checkout_session.subscription)
            from datetime import datetime
            current_user.subscription_id = subscription.id
            current_user.subscription_status = subscription.status
            current_user.subscription_end = datetime.fromtimestamp(subscription.current_period_end)
            print(f"Subscription: {subscription.id}, Status: {subscription.status}")
        
        # 保存用戶
        db.session.commit()
        print(f"✅ User {current_user.username} upgraded to Pro!")
        
        flash('Payment successful! You now have Pro access.', 'success')
        
    except Exception as e:
        print(f"Subscription error: {e}")
        flash(f'Error processing subscription: {str(e)}', 'danger')
    
    return redirect(url_for('main.index'))

import stripe
from flask import request, abort
import json

@bp.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    """Stripe Webhook - 處理支付事件"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    # 你的 webhook secret（在 Stripe Dashboard 獲取）
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        # Invalid payload
        abort(400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        abort(400)
    
    # 處理事件
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # 獲取用戶 ID
        user_id = session.get('client_reference_id')
        if user_id:
            from app.models import User, db
            user = User.get(int(user_id))
            if user:
                user.is_paid = True
                user.subscription_id = session.get('subscription')
                user.subscription_status = 'active'
                if session.get('subscription'):
                    subscription = stripe.Subscription.retrieve(session['subscription'])
                    from datetime import datetime
                    user.subscription_end = datetime.fromtimestamp(subscription.current_period_end)
                user.save()
                print(f"✅ Webhook: User {user.username} upgraded to Pro!")
    
    return jsonify({"status": "success"}), 200

@bp.route("/payment-success")
@login_required
def payment_success():
    """支付成功頁面 - 直接升級用戶"""
    current_user.is_paid = True
    db.session.commit()
    flash('Payment successful! You now have Pro access.', 'success')
    return redirect(url_for('main.index'))
