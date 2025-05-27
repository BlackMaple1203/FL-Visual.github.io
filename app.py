"""
联邦学习系统 Flask 后端应用
支持用户注册、登录、文件上传和模型训练
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
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

# 配置
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
DATABASE = 'federated_learning.db'
ALLOWED_EXTENSIONS = {'gz'}  # 支持 .nii.gz 文件

app = Flask(__name__, static_folder='app/static', template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

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
    def __init__(self, user_id, username, account_type):
        self.id = user_id
        self.username = username
        self.account_type = account_type  # 'server' or 'client'

@login_manager.user_loader
def load_user(user_id):
    """加载用户"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[3])
    return None

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
    
    # 创建训练会话表
    cursor.execute('''
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
    cursor.execute('''
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
    
    conn.commit()
    conn.close()

def allowed_file(filename):
    """检查文件类型"""
    return filename.lower().endswith('.nii.gz')

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
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            user = User(user_data[0], user_data[1], user_data[3])
            login_user(user)
            
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
            # 如果是AJAX请求，返回JSON错误
            if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
            else:
                flash('用户名或密码错误')
    
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
            if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                return jsonify({'success': False, 'message': '无效的账户类型'}), 400
            else:
                flash('无效的账户类型')
                return render_template('auth/register.html')
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # 检查用户名是否已存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            if request.headers.get('Content-Type') == 'application/json' or request.is_json:
                return jsonify({'success': False, 'message': '用户名已存在'}), 400
            else:
                flash('用户名已存在')
                return render_template('auth/register.html')
        
        # 创建新用户
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, password_hash, account_type)
            VALUES (?, ?, ?)
        ''', (username, password_hash, account_type))
        
        conn.commit()
        conn.close()
        
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            return jsonify({'success': True, 'message': '注册成功，请登录', 'redirect': url_for('login')})
        else:
            flash('注册成功，请登录')
            return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    """登出"""
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

if __name__ == '__main__':
    init_database()
    app.run(debug=True, port=5000)
