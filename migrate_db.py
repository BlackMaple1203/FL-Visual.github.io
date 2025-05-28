#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加 client_id 列并为现有用户分配ID
"""

import sqlite3
import random
import string
from datetime import datetime

def generate_client_id():
    """生成客户端ID格式：CLIENT_XXXXXXXX"""
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"CLIENT_{random_part}"

def migrate_database():
    """执行数据库迁移"""
    db_path = 'federated_learning.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查是否已存在 client_id 列
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'client_id' not in columns:
            print("添加 client_id 列到 user 表...")
            cursor.execute("ALTER TABLE user ADD COLUMN client_id VARCHAR(20)")
            
            # 为现有用户分配唯一的客户端ID
            cursor.execute("SELECT id, username FROM user WHERE client_id IS NULL")
            users = cursor.fetchall()
            
            used_ids = set()
            for user_id, username in users:
                # 生成唯一的客户端ID
                while True:
                    client_id = generate_client_id()
                    if client_id not in used_ids:
                        used_ids.add(client_id)
                        break
                
                cursor.execute("UPDATE user SET client_id = ? WHERE id = ?", (client_id, user_id))
                print(f"为用户 {username} 分配客户端ID: {client_id}")
            
            # 为 client_id 列添加唯一约束
            print("创建 client_id 唯一索引...")
            cursor.execute("CREATE UNIQUE INDEX idx_user_client_id ON user(client_id)")
            
            conn.commit()
            print("数据库迁移完成！")
        else:
            print("client_id 列已存在，检查现有用户是否需要分配ID...")
            
            # 检查是否有用户没有 client_id
            cursor.execute("SELECT id, username FROM user WHERE client_id IS NULL OR client_id = ''")
            users_without_id = cursor.fetchall()
            
            if users_without_id:
                # 获取现有的客户端ID以避免冲突
                cursor.execute("SELECT client_id FROM user WHERE client_id IS NOT NULL AND client_id != ''")
                used_ids = set(row[0] for row in cursor.fetchall())
                
                for user_id, username in users_without_id:
                    # 生成唯一的客户端ID
                    while True:
                        client_id = generate_client_id()
                        if client_id not in used_ids:
                            used_ids.add(client_id)
                            break
                    
                    cursor.execute("UPDATE user SET client_id = ? WHERE id = ?", (client_id, user_id))
                    print(f"为用户 {username} 分配客户端ID: {client_id}")
                
                conn.commit()
                print(f"为 {len(users_without_id)} 个用户分配了客户端ID")
            else:
                print("所有用户都已有客户端ID")
        
        # 验证迁移结果
        cursor.execute("SELECT username, client_id FROM user")
        users = cursor.fetchall()
        print("\n当前用户列表:")
        for username, client_id in users:
            print(f"用户: {username}, 客户端ID: {client_id}")
        
    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"迁移过程中发生错误: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("开始数据库迁移...")
    migrate_database()
    print("迁移完成！")
