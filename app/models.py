from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(120), nullable=False)
    account_type = db.Column(db.String(20), nullable=False, default='client')
    client_id = db.Column(db.String(20), unique=True, nullable=True)  # 客户端ID，格式：CLIENT_XXXXXXXX
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    training_sessions = db.relationship('TrainingSession', backref='user', lazy=True)
    predictions = db.relationship('Prediction', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class TrainingSession(db.Model):
    """训练会话模型"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, training, completed, failed
    filename = db.Column(db.String(200), nullable=True)
    loss_data = db.Column(db.Text, nullable=True)  # JSON格式的loss数据
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<TrainingSession {self.session_id}>'

class Prediction(db.Model):
    """预测结果模型"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    result_image = db.Column(db.Text, nullable=True)  # base64编码的图片
    confidence = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Prediction {self.filename}>'

class ModelMetrics(db.Model):
    """模型性能指标"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('training_session.id'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Float)
    loss = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    training_session = db.relationship('TrainingSession', backref='metrics', lazy=True)
    
    def __repr__(self):
        return f'<ModelMetrics Round {self.round_number}>'

class ClientNode(db.Model):
    """客户端节点模型"""
    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='offline')  # offline, online, training
    data_count = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # 关系
    user = db.relationship('User', backref='nodes', lazy=True)
    
    def __repr__(self):
        return f'<ClientNode {self.node_id}>'