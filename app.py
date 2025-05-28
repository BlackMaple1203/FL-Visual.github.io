"""
联邦学习系统 Flask 后端应用
支持用户注册、登录、文件上传和模型训练
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room, leave_room
from database_manager import DatabaseManager
import sqlite3
import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import nibabel as nib
from datetime import datetime
import uuid
import io
import base64
import string
import random
import re

# 配置
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
DATABASE = 'federated_learning.db'
ALLOWED_EXTENSIONS = {'gz'}  # 支持 .nii.gz 文件

app = Flask(__name__, static_folder='app/static', template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化数据库管理器
db_manager = DatabaseManager(DATABASE)

# 创建必要的文件夹
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Flask-Login 配置
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'

class User(UserMixin):
    """用户模型"""
    def __init__(self, user_id, username, account_type, client_id=None):
        self.id = user_id
        self.username = username
        self.account_type = account_type  # 'server' or 'client'
        self.client_id = client_id

@login_manager.user_loader
def load_user(user_id):
    """加载用户"""
    try:
        user_data = db_manager.execute_query(
            'SELECT * FROM users WHERE id = ?', 
            (user_id,), 
            fetch=True
        )
        
        if user_data:
            user_row = user_data[0]
            return User(user_row[0], user_row[1], user_row[3], user_row[5])  # id, username, account_type, client_id
        return None
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None

def init_database():
    """初始化数据库"""
    try:
        # 创建用户表
        db_manager.execute_query('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                account_type TEXT NOT NULL CHECK (account_type IN ('server', 'client')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                client_id TEXT,
                email TEXT
            )
        ''')
        
        # 创建训练会话表
        db_manager.execute_query('''
            CREATE TABLE IF NOT EXISTS training_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                loss_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 创建预测结果表
        db_manager.execute_query('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                filename TEXT NOT NULL,
                result_image TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
          # 创建客户端状态表
        db_manager.execute_query('''
            CREATE TABLE IF NOT EXISTS client_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                is_online BOOLEAN DEFAULT FALSE,
                status TEXT DEFAULT 'offline',
                has_uploaded_data BOOLEAN DEFAULT FALSE,
                is_training BOOLEAN DEFAULT FALSE,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                training_progress REAL DEFAULT 0.0,
                data_upload_time TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 创建服务器日志表
        db_manager.execute_query('''
            CREATE TABLE IF NOT EXISTS server_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
          # 创建服务器节点表
        db_manager.execute_query('''
            CREATE TABLE IF NOT EXISTS server_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                username TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by_server INTEGER,
                status TEXT DEFAULT 'disconnected',
                has_data BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (added_by_server) REFERENCES users (id)
            )
        ''')
        
        print("数据库初始化完成")
    except Exception as e:
        print(f"数据库初始化错误: {e}")

def allowed_file(filename):
    """检查文件类型"""
    return filename.lower().endswith('.nii.gz')

def generate_client_id():
    """生成唯一的客户端ID"""
    return 'CLIENT_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def safe_log_server_event(client_id, event_type, message):
    """安全地记录服务器事件"""
    try:
        db_manager.execute_query(
            'INSERT INTO server_logs (client_id, event_type, message) VALUES (?, ?, ?)',
            (client_id, event_type, message)
        )
    except Exception as e:
        print(f"记录服务器事件失败: {e}")

def safe_update_client_status(client_id, status=None, is_online=None, has_uploaded_data=None, is_training=None, training_progress=None, data_upload_time=None):
    """安全地更新客户端状态"""
    try:
        updates = []
        params = []
        
        if status is not None:
            updates.append("status = ?")
            params.append(status)
            # 同时更新is_online状态
            updates.append("is_online = ?")
            params.append(status == 'online')
        if is_online is not None:
            updates.append("is_online = ?")
            params.append(is_online)
        if has_uploaded_data is not None:
            updates.append("has_uploaded_data = ?")
            params.append(has_uploaded_data)
        if is_training is not None:
            updates.append("is_training = ?")
            params.append(is_training)
        if training_progress is not None:
            updates.append("training_progress = ?")
            params.append(training_progress)
        if data_upload_time is not None:
            updates.append("data_upload_time = ?")
            params.append(data_upload_time)
            
        if updates:
            updates.append("last_activity = CURRENT_TIMESTAMP")
            updates.append("last_seen = CURRENT_TIMESTAMP")
            params.append(client_id)
            
            query = f"UPDATE client_status SET {', '.join(updates)} WHERE client_id = ?"
            db_manager.execute_query(query, params)
    except Exception as e:
        print(f"更新客户端状态失败: {e}")

def safe_get_client_status(client_id):
    """安全地获取客户端状态"""
    try:
        result = db_manager.execute_query(
            'SELECT is_online, has_uploaded_data, is_training, training_progress, last_seen FROM client_status WHERE client_id = ?',
            (client_id,),
            fetch=True
        )
        return result[0] if result else None
    except Exception as e:
        print(f"获取客户端状态失败: {e}")
        return None

def generate_loss_curve():
    """生成模拟的loss曲线数据"""
    epochs = list(range(1, 21))  # 20个epoch
    # 模拟递减的loss值，加入一些随机波动
    base_loss = 2.5
    losses = []
    for i, epoch in enumerate(epochs):
        loss = base_loss * np.exp(-0.15 * i) + np.random.normal(0, 0.05)
        loss = max(0.1, loss)  # 确保loss不会变成负数
        losses.append(round(loss, 4))
    
    return epochs, losses

def create_loss_plot(epochs, losses):
    """创建loss图表"""
    plt.figure(figsize=(10, 6))
    plt.plot(epochs, losses, 'b-', linewidth=2, marker='o', markersize=4)
    plt.title('Training Loss Curve', fontsize=16, fontweight='bold')
    plt.xlabel('Epoch', fontsize=12)
    plt.ylabel('Loss', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # 保存到内存中
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()
    
    # 转换为base64编码
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    return img_base64

def simulate_training(session_id, filename):
    """模拟训练过程"""
    import time
    import threading
    
    def training_process():
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # 更新状态为训练中
        cursor.execute('UPDATE training_sessions SET status = ? WHERE session_id = ?', 
                      ('training', session_id))
        conn.commit()
        
        # 模拟训练时间
        time.sleep(5)
        
        # 生成loss数据
        epochs, losses = generate_loss_curve()
        loss_data = {
            'epochs': epochs,
            'losses': losses
        }
        
        # 更新训练结果
        cursor.execute('''
            UPDATE training_sessions 
            SET status = ?, loss_data = ?, completed_at = ? 
            WHERE session_id = ?
        ''', ('completed', json.dumps(loss_data), datetime.now(), session_id))
        conn.commit()
        conn.close()
    
    # 在后台线程中运行训练
    thread = threading.Thread(target=training_process)
    thread.daemon = True
    thread.start()

def simulate_prediction(filename):
    """模拟模型预测过程"""
    # 创建一个简单的热力图来模拟病灶检测结果
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # 模拟原始影像
    original_image = np.random.rand(64, 64) * 0.3 + 0.2
    ax1.imshow(original_image, cmap='gray')
    ax1.set_title('Original Image')
    ax1.axis('off')
    
    # 模拟预测结果（热力图）
    prediction_mask = np.zeros((64, 64))
    # 添加一些"病灶"区域
    prediction_mask[20:30, 25:35] = np.random.rand(10, 10) * 0.8 + 0.2
    prediction_mask[40:48, 15:25] = np.random.rand(8, 10) * 0.6 + 0.3
    
    # 叠加显示
    ax2.imshow(original_image, cmap='gray', alpha=0.7)
    ax2.imshow(prediction_mask, cmap='hot', alpha=0.5)
    ax2.set_title('Prediction Result (Red: High Risk)')
    ax2.axis('off')
    
    plt.tight_layout()
    
    # 保存到内存
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()
    
    # 转换为base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # 生成随机置信度
    confidence = round(np.random.uniform(0.75, 0.95), 3)
    
    return img_base64, confidence

# 路由定义
@app.route('/')
def index():
    """首页 - 显示系统主页和角色选择"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """仪表板重定向"""
    if current_user.is_authenticated:
        if current_user.account_type == 'server':
            return redirect(url_for('server_dashboard'))
        else:
            return redirect(url_for('client_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        # 检查是否为AJAX请求
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form['username']
            password = request.form['password']
        
        try:
            user_data = db_manager.execute_query(
                'SELECT * FROM users WHERE username = ?', 
                (username,), 
                fetch=True
            )
            
            if user_data and check_password_hash(user_data[0][2], password):
                user_row = user_data[0]
                user = User(user_row[0], user_row[1], user_row[3], user_row[5])  # id, username, account_type, client_id
                login_user(user)
                
                # 如果是客户端用户，更新客户端状态
                if user.account_type == 'client' and user.client_id:
                    safe_update_client_status(user.client_id, status='online')
                    safe_log_server_event(user.client_id, 'login', f'客户端 {username} 登录')
                
                # 如果是AJAX请求，返回JSON响应
                if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                    if user.account_type == 'server':
                        return jsonify({'success': True, 'redirect': url_for('server_dashboard')})
                    else:
                        return jsonify({'success': True, 'redirect': url_for('client_dashboard')})
                else:
                    if user.account_type == 'server':
                        return redirect(url_for('server_dashboard'))
                    else:
                        return redirect(url_for('client_dashboard'))
            else:
                error_msg = '用户名或密码错误'
                # 如果是AJAX请求，返回JSON错误
                if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 401
                else:
                    flash(error_msg)
        except Exception as e:
            error_msg = f'登录失败: {str(e)}'
            print(f"登录错误: {e}")
            if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 500
            else:
                flash(error_msg)
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'POST':
        # 检查是否为AJAX请求
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            account_type = data.get('account_type')
        else:
            username = request.form['username']
            password = request.form['password']
            account_type = request.form['account_type']
        
        if account_type not in ['server', 'client']:
            error_msg = '无效的账户类型'
            if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            else:
                flash(error_msg)
                return render_template('auth/register.html')
        
        try:
            # 检查用户名是否已存在
            existing_user = db_manager.execute_query(
                'SELECT id FROM users WHERE username = ?', 
                (username,), 
                fetch=True
            )
            
            if existing_user:
                error_msg = '用户名已存在'
                if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                    return jsonify({'success': False, 'message': error_msg}), 400
                else:
                    flash(error_msg)
                    return render_template('auth/register.html')
            
            # 为客户端用户生成客户端ID
            client_id = generate_client_id() if account_type == 'client' else None
            
            # 创建新用户
            password_hash = generate_password_hash(password)
            db_manager.execute_query('''
                INSERT INTO users (username, password_hash, account_type, client_id)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, account_type, client_id))
            
            # 如果是客户端用户，初始化客户端状态
            if account_type == 'client' and client_id:
                # 获取新用户的ID
                user_data = db_manager.execute_query(
                    'SELECT id FROM users WHERE username = ?',
                    (username,),
                    fetch=True
                )
                if user_data:
                    user_id = user_data[0][0]
                    db_manager.execute_query('''
                        INSERT INTO client_status (client_id, user_id, status)
                        VALUES (?, ?, ?)
                    ''', (client_id, user_id, 'offline'))
            
            success_msg = '注册成功，请登录'
            if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                return jsonify({'success': True, 'message': success_msg, 'redirect': url_for('login')})
            else:
                flash(success_msg)
                return redirect(url_for('login'))
        except Exception as e:
            error_msg = f'注册失败: {str(e)}'
            print(f"注册错误: {e}")
            if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 500
            else:
                flash(error_msg)
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    """登出"""
    if current_user.account_type == 'client' and current_user.client_id:
        safe_update_client_status(current_user.client_id, status='offline')
        safe_log_server_event(current_user.client_id, 'logout', f'客户端 {current_user.username} 登出')
    
    logout_user()
    return redirect(url_for('login'))

@app.route('/server')
@login_required
def server_dashboard():
    """服务端仪表板"""
    if current_user.account_type != 'server':
        flash('权限不足')
        return redirect(url_for('index'))
    
    return render_template('server/dashboard.html')

@app.route('/client')
@login_required
def client_dashboard():
    """客户端仪表板"""
    if current_user.account_type != 'client':
        flash('权限不足')
        return redirect(url_for('index'))
    
    return render_template('client/dashboard.html')

@app.route('/upload_training', methods=['POST'])
@login_required
def upload_training():
    """上传训练文件"""
    if current_user.account_type != 'client':
        return jsonify({'error': '权限不足'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 添加时间戳避免文件名冲突
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 创建训练会话
        session_id = str(uuid.uuid4())
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO training_sessions (user_id, session_id, filename, status)
            VALUES (?, ?, ?, ?)
        ''', (current_user.id, session_id, filename, 'pending'))
        conn.commit()
        conn.close()
        
        # 开始模拟训练
        simulate_training(session_id, filename)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': '文件上传成功，训练已开始'
        })
    
    return jsonify({'error': '不支持的文件格式，请上传 .nii.gz 文件'}), 400

@app.route('/training_status/<session_id>')
@login_required
def training_status(session_id):
    """获取训练状态"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT status, loss_data, completed_at 
        FROM training_sessions 
        WHERE session_id = ? AND user_id = ?
    ''', (session_id, current_user.id))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'error': '训练会话不存在'}), 404
    
    status, loss_data, completed_at = result
    
    response = {
        'status': status,
        'completed_at': completed_at
    }
    
    if loss_data:
        response['loss_data'] = json.loads(loss_data)
    
    return jsonify(response)

@app.route('/get_loss_chart/<session_id>')
@login_required
def get_loss_chart(session_id):
    """获取训练loss图表"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT loss_data FROM training_sessions 
        WHERE session_id = ?
    ''', (session_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not result[0]:
        return jsonify({'error': '训练数据不存在'}), 404
    
    loss_data = json.loads(result[0])
    epochs = loss_data['epochs']
    losses = loss_data['losses']
    
    # 生成图表
    chart_base64 = create_loss_plot(epochs, losses)
    
    return jsonify({
        'chart_image': chart_base64,
        'epochs': epochs,
        'losses': losses
    })

@app.route('/all_training_sessions')
@login_required
def all_training_sessions():
    """获取所有训练会话（供server端查看）"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if current_user.account_type == 'server':
        # 服务端可以查看所有训练会话
        cursor.execute('''
            SELECT ts.session_id, ts.filename, ts.status, ts.created_at, 
                   ts.completed_at, u.username, ts.loss_data
            FROM training_sessions ts
            JOIN users u ON ts.user_id = u.id
            ORDER BY ts.created_at DESC
        ''')
    else:
        # 客户端只能查看自己的训练会话
        cursor.execute('''
            SELECT session_id, filename, status, created_at, 
                   completed_at, ? as username, loss_data
            FROM training_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (current_user.username, current_user.id))
    
    sessions = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'session_id': session[0],
        'filename': session[1],
        'status': session[2],
        'created_at': session[3],
        'completed_at': session[4],
        'username': session[5],
        'has_loss_data': bool(session[6])
    } for session in sessions])

@app.route('/upload_prediction', methods=['POST'])
@login_required
def upload_prediction():
    """上传文件进行预测"""
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pred_{timestamp}_{filename}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 模拟预测
        result_image, confidence = simulate_prediction(filename)
        
        # 保存预测结果
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO predictions (user_id, filename, result_image, confidence)
            VALUES (?, ?, ?, ?)
        ''', (current_user.id, filename, result_image, confidence))
        conn.commit()
        prediction_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'prediction_id': prediction_id,
            'result_image': result_image,
            'confidence': confidence,
            'message': '预测完成'
        })
    
    return jsonify({'error': '不支持的文件格式，请上传 .nii.gz 文件'}), 400

@app.route('/client_stats')
@login_required
def client_stats():
    """获取客户端统计信息"""
    if current_user.account_type != 'client':
        return jsonify({'error': '权限不足'}), 403
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 获取训练会话统计
    cursor.execute('''
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
            COUNT(CASE WHEN status = 'running' THEN 1 END) as running_sessions,
            MAX(created_at) as last_training
        FROM training_sessions 
        WHERE user_id = ?
    ''', (current_user.id,))
    
    stats = cursor.fetchone()
    
    # 获取最近的训练会话
    cursor.execute('''
        SELECT session_id, filename, status, created_at
        FROM training_sessions 
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 5
    ''', (current_user.id,))
    
    recent_sessions = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'total_sessions': stats[0] or 0,
        'completed_sessions': stats[1] or 0,
        'running_sessions': stats[2] or 0,
        'last_training': stats[3],
        'recent_sessions': [
            {
                'session_id': session[0],
                'filename': session[1],
                'status': session[2],
                'created_at': session[3]
            }
            for session in recent_sessions
        ]
    })

@app.route('/server_info')
@login_required
def server_info():
    """获取服务器信息"""
    # 模拟服务器信息
    server_info = {
        'server_status': 'online',
        'connected_clients': 3,
        'total_rounds': 10,
        'current_round': 5,
        'model_accuracy': 0.87,
        'last_aggregation': '2024-01-15 14:30:00',
        'server_load': 45.2,
        'memory_usage': 68.5
    }
    
    return jsonify(server_info)

@app.route('/model_performance')
@login_required  
def model_performance():
    """获取模型性能数据"""
    # 模拟性能数据
    rounds = list(range(1, 11))
    accuracy = [0.65, 0.72, 0.76, 0.79, 0.82, 0.84, 0.86, 0.87, 0.88, 0.89]
    loss = [2.1, 1.8, 1.5, 1.3, 1.1, 0.9, 0.8, 0.7, 0.6, 0.55]
    
    return jsonify({
        'rounds': rounds,
        'accuracy': accuracy,
        'loss': loss,
        'clients_participated': [2, 3, 3, 4, 4, 3, 4, 3, 4, 3]
    })

@app.route('/download_model/<session_id>')
@login_required
def download_model(session_id):
    """下载训练好的模型"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT status, filename FROM training_sessions 
        WHERE session_id = ? AND user_id = ?
    ''', (session_id, current_user.id))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'error': '训练会话不存在'}), 404
        
    if result[0] != 'completed':
        return jsonify({'error': '训练尚未完成'}), 400
    
    # 创建一个模拟的模型文件
    model_content = f"# 联邦学习模型 - {session_id}\n# 训练文件: {result[1]}\n# 训练完成时间: {datetime.now()}\n"
      # 创建临时文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(model_content)
        temp_file = f.name
    
    return send_file(temp_file, as_attachment=True, download_name=f'model_{session_id}.txt')

# 新增API路由
@app.route('/api/add_node', methods=['POST'])
@login_required
def add_node():
    """服务端添加节点"""
    if current_user.account_type != 'server':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        client_id = data.get('client_id', '').strip()
        
        if not client_id:
            return jsonify({'success': False, 'message': '请输入客户端ID'}), 400
        
        # 检查客户端ID是否存在
        user_data = db_manager.execute_query(
            'SELECT id, username FROM users WHERE client_id = ? AND account_type = ?',
            (client_id, 'client'),
            fetch=True
        )
        
        if not user_data:
            return jsonify({'success': False, 'message': f'客户端ID {client_id} 不存在'}), 404
        
        # 检查节点是否已经添加
        existing_node = db_manager.execute_query(
            'SELECT id FROM server_nodes WHERE client_id = ?',
            (client_id,),
            fetch=True
        )
        
        if existing_node:
            return jsonify({'success': False, 'message': '该节点已经存在'}), 400
        
        # 添加节点
        db_manager.execute_query('''
            INSERT INTO server_nodes (client_id, added_by_server, status)
            VALUES (?, ?, ?)
        ''', (client_id, current_user.id, 'disconnected'))
        
        # 记录日志
        safe_log_server_event(client_id, 'node_added', f'服务器添加了节点 {client_id}')
        
        return jsonify({
            'success': True, 
            'message': f'成功添加节点 {client_id}',
            'client_id': client_id,
            'username': user_data[0][1]
        })
        
    except Exception as e:
        print(f"添加节点错误: {e}")
        return jsonify({'success': False, 'message': f'添加节点失败: {str(e)}'}), 500

@app.route('/api/start_training', methods=['POST'])
@login_required
def start_training():
    """服务端开始训练"""
    if current_user.account_type != 'server':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        # 检查是否有已上传数据的节点
        nodes_with_data = db_manager.execute_query('''
            SELECT sn.client_id, cs.has_uploaded_data, u.username
            FROM server_nodes sn
            JOIN client_status cs ON sn.client_id = cs.client_id
            JOIN users u ON cs.user_id = u.id
            WHERE cs.has_uploaded_data = TRUE
        ''', fetch=True)
        
        if not nodes_with_data:
            return jsonify({'success': False, 'message': '没有节点上传数据，无法开始训练'}), 400
        
        # 更新所有有数据的节点为训练状态
        training_id = str(uuid.uuid4())
        for node in nodes_with_data:
            client_id = node[0]
            safe_update_client_status(client_id, is_training=True, training_progress=0.0)
            safe_log_server_event(client_id, 'training_start', f'开始训练，训练ID: {training_id}')
        
        return jsonify({
            'success': True,
            'message': f'训练已开始，共 {len(nodes_with_data)} 个节点参与',
            'training_id': training_id,
            'participating_nodes': len(nodes_with_data)
        })
        
    except Exception as e:
        print(f"开始训练错误: {e}")
        return jsonify({'success': False, 'message': f'开始训练失败: {str(e)}'}), 500

@app.route('/api/client_status')
@login_required
def get_client_status():
    """获取客户端状态"""
    try:
        if current_user.account_type == 'server':
            # 服务器端获取所有节点状态
            nodes = db_manager.execute_query('''
                SELECT sn.client_id, u.username, cs.status, cs.has_uploaded_data, 
                       cs.is_training, cs.training_progress, cs.last_activity
                FROM server_nodes sn
                JOIN users u ON sn.client_id = u.client_id
                LEFT JOIN client_status cs ON sn.client_id = cs.client_id
                ORDER BY sn.created_at DESC
            ''', fetch=True)
            
            return jsonify({
                'success': True,
                'nodes': [{
                    'client_id': node[0],
                    'username': node[1],
                    'status': node[2] or 'offline',
                    'has_uploaded_data': bool(node[3]),
                    'is_training': bool(node[4]),
                    'training_progress': node[5] or 0.0,
                    'last_activity': node[6]
                } for node in nodes]
            })
        else:
            # 客户端获取自己的状态
            if current_user.client_id:
                status = safe_get_client_status(current_user.client_id)
                return jsonify({
                    'success': True,
                    'status': status[0] if status else 'offline',
                    'has_uploaded_data': bool(status[1]) if status else False,
                    'is_training': bool(status[2]) if status else False,
                    'training_progress': status[3] if status else 0.0
                })
            else:
                return jsonify({'success': False, 'message': '客户端ID未分配'}), 400
                
    except Exception as e:
        print(f"获取客户端状态错误: {e}")
        return jsonify({'success': False, 'message': f'获取状态失败: {str(e)}'}), 500

@app.route('/api/training_status')
@login_required
def get_training_status():
    """获取训练状态（服务器端）"""
    if current_user.account_type != 'server':
        return jsonify({'status': 'unauthorized', 'message': '权限不足'}), 403
    
    try:
        # 检查是否有正在训练的节点
        training_nodes = db_manager.execute_query('''
            SELECT COUNT(*) FROM client_status WHERE is_training = TRUE
        ''', fetch=True)
        
        training_count = training_nodes[0][0] if training_nodes else 0
        
        # 获取最近的训练会话
        recent_sessions = db_manager.execute_query('''
            SELECT status, COUNT(*) as count
            FROM training_sessions
            WHERE created_at > datetime('now', '-1 day')
            GROUP BY status
        ''', fetch=True)
        
        status_summary = {row[0]: row[1] for row in recent_sessions} if recent_sessions else {}
        
        if training_count > 0:
            status = 'training'
        elif status_summary.get('completed', 0) > 0:
            status = 'completed'
        else:
            status = 'idle'
        
        return jsonify({
            'status': status,
            'training_nodes': training_count,
            'recent_sessions': status_summary,
            'message': f'当前有 {training_count} 个节点正在训练'
        })
        
    except Exception as e:
        print(f"获取训练状态错误: {e}")
        return jsonify({'status': 'error', 'message': f'获取训练状态失败: {str(e)}'}), 500

@app.route('/api/server_logs')
@login_required
def get_server_logs():
    """获取服务器日志"""
    if current_user.account_type != 'server':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        logs = db_manager.execute_query('''
            SELECT client_id, event_type, message, timestamp
            FROM server_logs
            ORDER BY timestamp DESC
            LIMIT 100
        ''', fetch=True)
        
        return jsonify({
            'success': True,
            'logs': [{
                'client_id': log[0],
                'event_type': log[1],
                'message': log[2],
                'timestamp': log[3]
            } for log in logs]
        })
        
    except Exception as e:
        print(f"获取服务器日志错误: {e}")
        return jsonify({'success': False, 'message': f'获取日志失败: {str(e)}'}), 500

@app.route('/api/upload_data', methods=['POST'])
@login_required
def upload_data():
    """客户端上传数据"""
    if current_user.account_type != 'client':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    if not current_user.client_id:
        return jsonify({'success': False, 'message': '客户端ID未分配'}), 400
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{current_user.client_id}_{timestamp}_{filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
              # 更新客户端状态
            safe_update_client_status(current_user.client_id, has_uploaded_data=True)
            safe_log_server_event(current_user.client_id, 'data_upload', f'客户端上传了文件: {file.filename}')
            return jsonify({
                'success': True,
                'message': '文件上传成功',
                'filename': filename
            })
        else:
            return jsonify({'success': False, 'message': '不支持的文件格式，请上传 .nii.gz 文件'}), 400
            
    except Exception as e:
        print(f"上传数据错误: {e}")
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500

@app.route('/api/server_nodes', methods=['GET'])
@login_required
def api_get_server_nodes():
    """获取服务器节点列表"""
    if current_user.account_type != 'server':
        return jsonify([]), 403
    
    try:
        nodes = db_manager.execute_query('''
            SELECT sn.client_id, u.username 
            FROM server_nodes sn
            JOIN users u ON sn.client_id = u.client_id
            ORDER BY sn.created_at
        ''', fetch=True)
        
        return jsonify([{'client_id': node[0], 'username': node[1]} for node in nodes])
    except Exception as e:
        print(f"获取节点列表错误: {e}")
        return jsonify([])

# SocketIO事件处理
@socketio.on('register_client')
def handle_register_client(data):
    """处理客户端注册"""
    try:
        client_type = data.get('type')
        client_name = data.get('name')
        
        if client_type == 'client' and current_user.is_authenticated and current_user.client_id:
            # 检查客户端是否在服务器节点中
            node_exists = db_manager.execute_query(
                'SELECT id FROM server_nodes WHERE client_id = ?',
                (current_user.client_id,),
                fetch=True
            )
            
            if node_exists:
                safe_update_client_status(current_user.client_id, status='online')
                emit('registration_confirmed', {
                    'status': 'success',
                    'client_id': current_user.client_id,
                    'message': '客户端注册成功'
                })
                safe_log_server_event(current_user.client_id, 'connect', f'客户端 {client_name} 连接到服务器')
            else:
                emit('registration_failed', {
                    'status': 'error',
                    'message': '客户端未被服务器添加为节点'
                })
        elif client_type == 'server':
            emit('registration_confirmed', {
                'status': 'success',
                'message': '服务器注册成功'
            })
            
    except Exception as e:
        print(f"客户端注册错误: {e}")
        emit('registration_failed', {'status': 'error', 'message': '注册失败'})

@socketio.on('update_parameters')
def handle_update_parameters(data):
    """处理参数更新"""
    try:
        if current_user.is_authenticated and current_user.client_id:
            client_id = data.get('client_id')
            data_count = data.get('data_count', 0)
            
            if client_id == current_user.client_id:
                safe_log_server_event(client_id, 'parameter_update', f'客户端更新参数，数据量: {data_count}')
                
                # 模拟参数更新进度
                import time
                import threading
                
                def update_progress():
                    for i in range(0, 101, 20):
                        safe_update_client_status(client_id, training_progress=i/100)
                        time.sleep(1)
                    
                    safe_log_server_event(client_id, 'parameter_complete', '参数更新完成')
                
                thread = threading.Thread(target=update_progress)
                thread.daemon = True
                thread.start()
                
    except Exception as e:
        print(f"参数更新错误: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    try:
        if current_user.is_authenticated and current_user.client_id:
            safe_update_client_status(current_user.client_id, status='offline')
            safe_log_server_event(current_user.client_id, 'disconnect', f'客户端 {current_user.username} 断开连接')
    except Exception as e:
        print(f"断开连接错误: {e}")

if __name__ == '__main__':
    init_database()
    socketio.run(app, debug=True, port=5000)
