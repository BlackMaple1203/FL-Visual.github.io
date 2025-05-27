"""
简化的联邦学习系统测试应用
用于验证基本功能
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'

# 配置 Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录访问此页面'
login_manager.login_message_category = 'info'

class User(UserMixin):
    """用户类"""
    def __init__(self, id, username, account_type):
        self.id = id
        self.username = username
        self.account_type = account_type

@login_manager.user_loader
def load_user(user_id):
    """加载用户"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, account_type FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

# 配置
DATABASE = 'federated_learning.db'
UPLOAD_FOLDER = 'uploads'

# 创建必要的文件夹
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            account_type TEXT NOT NULL CHECK (account_type IN ('server', 'client')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """首页"""
    if current_user.is_authenticated:
        if current_user.account_type == 'server':
            return redirect(url_for('server_dashboard'))
        else:
            return redirect(url_for('client_dashboard'))
    return render_template('auth/login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        account_type = request.form.get('account_type', 'client')
        
        # 简化的验证逻辑
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash, account_type FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], user_data[3])
            login_user(user)
            flash(f'欢迎回来，{username}！', 'success')
            
            if user.account_type == 'server':
                return redirect(url_for('server_dashboard'))
            else:
                return redirect(url_for('client_dashboard'))
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        account_type = request.form.get('account_type', 'client')
        
        # 简化的注册逻辑
        password_hash = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password_hash, account_type) VALUES (?, ?, ?)',
                          (username, password_hash, account_type))
            conn.commit()
            conn.close()
            
            flash('注册成功，请登录', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('用户名已存在', 'error')
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    """退出登录"""
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))

@app.route('/server')
@login_required
def server_dashboard():
    """服务端仪表板"""
    if current_user.account_type != 'server':
        flash('权限不足', 'error')
        return redirect(url_for('client_dashboard'))
    return render_template('server/dashboard.html')

@app.route('/client')
@login_required
def client_dashboard():
    """客户端仪表板"""
    return render_template('client/dashboard.html')

@app.route('/api/test')
def api_test():
    """API测试端点"""
    return jsonify({
        'status': 'success',
        'message': 'Flask应用运行正常',
        'templates_available': [
            'auth/login.html',
            'auth/register.html', 
            'server/dashboard.html',
            'client/dashboard.html'
        ]
    })

if __name__ == '__main__':
    init_database()
    print("启动简化版联邦学习系统...")
    print("访问 http://localhost:5000 查看应用")
    print("访问 http://localhost:5000/api/test 测试API")
    app.run(debug=True, port=5000)
