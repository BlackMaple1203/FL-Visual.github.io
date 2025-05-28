#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import db_manager
from werkzeug.security import generate_password_hash
import uuid

def create_test_user():
    """创建测试用户"""
    try:
        username = "testclient"
        password = "test123"
        account_type = "client"
        
        # 生成客户端ID
        client_id = f"CLIENT_{uuid.uuid4().hex[:8].upper()}"
        
        # 检查用户是否已存在
        existing_user = db_manager.execute_query(
            'SELECT id FROM users WHERE username = ?', 
            (username,), 
            fetch=True
        )
        
        if existing_user:
            print(f"用户 {username} 已存在")
            return
        
        # 创建新用户
        password_hash = generate_password_hash(password)
        
        user_id = db_manager.execute_query('''
            INSERT INTO users (username, password_hash, account_type, client_id)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, account_type, client_id))
        
        # 初始化客户端状态
        db_manager.execute_query('''
            INSERT INTO client_status (client_id, user_id, status)
            VALUES (?, ?, 'offline')
        ''', (client_id, user_id))
        
        print(f"✅ 测试用户创建成功:")
        print(f"   用户名: {username}")
        print(f"   密码: {password}")
        print(f"   客户端ID: {client_id}")
        
        return username, password, client_id
        
    except Exception as e:
        print(f"创建测试用户时出错: {e}")
        return None

if __name__ == "__main__":
    create_test_user()
