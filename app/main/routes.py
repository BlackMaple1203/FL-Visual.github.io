from flask import render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import main
import os
import json

@main.route('/')
@main.route('/index')
def index():
    """主页 - 提供角色选择"""
    return render_template('index.html')

@main.route('/server')
@main.route('/server/dashboard')
@login_required
def server_dashboard():
    """服务端控制台 - 联邦学习可视化界面"""
    if current_user.account_type != 'server':
        flash('您没有权限访问服务端控制台', 'warning')
        return redirect(url_for('main.index'))
    return render_template('server/dashboard.html')

@main.route('/client')
@main.route('/client/dashboard')
@login_required
def client_dashboard():
    """客户端控制台"""
    if current_user.account_type != 'client':
        flash('您没有权限访问客户端控制台', 'warning')
        return redirect(url_for('main.index'))
    return render_template('client/dashboard.html')

# API路由用于联邦学习过程
@main.route('/api/training/start', methods=['POST'])
@login_required
def start_training():
    """启动联邦学习训练"""
    data = request.get_json()
    rounds = data.get('rounds', 3)
    client_count = data.get('client_count', 0)
    
    # 这里添加启动训练的逻辑
    return jsonify({
        'status': 'success',
        'message': f'训练已启动，共{rounds}轮',
        'rounds': rounds,
        'client_count': client_count
    })

@main.route('/api/training/stop', methods=['POST'])
@login_required
def stop_training():
    """停止联邦学习训练"""
    # 这里添加停止训练的逻辑
    return jsonify({
        'status': 'success',
        'message': '训练已停止'
    })

@main.route('/api/nodes', methods=['GET'])
@login_required
def get_nodes():
    """获取连接的节点信息"""
    # 模拟节点数据，实际项目中应该从数据库获取
    nodes = [
        {'id': 1, 'name': '节点1', 'status': '在线', 'data_count': 150},
        {'id': 2, 'name': '节点2', 'status': '在线', 'data_count': 200},
    ]
    return jsonify(nodes)