#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import random
import string

def generate_client_id():
    """生成客户端ID，格式：CLIENT_XXXXXXXX"""
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"CLIENT_{random_part}"

def migrate_users_table():
    """迁移users表，添加缺失的列"""
    try:
        conn = sqlite3.connect('federated_learning.db')
        cursor = conn.cursor()
        
        print("开始迁移users表...")
        
        # 检查是否已存在client_id列
        cursor.execute("PRAGMA table_info(users);")
        columns = [col[1] for col in cursor.fetchall()]
          # 添加client_id列（如果不存在）
        if 'client_id' not in columns:
            print("添加client_id列...")
            cursor.execute("ALTER TABLE users ADD COLUMN client_id TEXT;")
            
            # 为现有用户生成唯一的client_id
            cursor.execute("SELECT id, username FROM users WHERE client_id IS NULL;")
            users_without_client_id = cursor.fetchall()
            
            for user_id, username in users_without_client_id:
                while True:
                    client_id = generate_client_id()
                    # 检查client_id是否已存在
                    cursor.execute("SELECT id FROM users WHERE client_id = ?;", (client_id,))
                    if not cursor.fetchone():
                        break
                
                cursor.execute("UPDATE users SET client_id = ? WHERE id = ?;", (client_id, user_id))
                print(f"为用户 '{username}' 分配客户端ID: {client_id}")
            
            # 添加UNIQUE约束（在填充数据后）
            print("为client_id添加唯一约束...")
            cursor.execute("CREATE UNIQUE INDEX idx_users_client_id ON users(client_id);")
        else:
            print("client_id列已存在")
        
        # 添加email列（如果不存在）
        if 'email' not in columns:
            print("添加email列...")
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT;")
        else:
            print("email列已存在")
        
        conn.commit()
        print("users表迁移完成！")
        
        # 显示更新后的表结构
        cursor.execute("PRAGMA table_info(users);")
        columns = cursor.fetchall()
        print("\n更新后的users表结构:")
        for col in columns:
            print(f"  {col}")
        
        # 显示所有用户及其client_id
        cursor.execute("SELECT id, username, client_id, account_type FROM users;")
        users = cursor.fetchall()
        print(f"\n现有用户:")
        for user in users:
            print(f"  ID: {user[0]}, 用户名: {user[1]}, 客户端ID: {user[2]}, 账户类型: {user[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"迁移过程中出错: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    migrate_users_table()
