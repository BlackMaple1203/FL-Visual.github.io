#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""测试客户端ID显示问题"""

import sqlite3
from database_manager import DatabaseManager

def test_user_loading():
    """测试用户加载和客户端ID"""
    db_manager = DatabaseManager('federated_learning.db')
    
    # 查询所有客户端用户
    try:
        users = db_manager.execute_query(
            'SELECT id, username, account_type, client_id FROM users WHERE account_type = ?',
            ('client',),
            fetch=True
        )
        
        print("客户端用户信息:")
        for user in users:
            print(f"  ID: {user[0]}, 用户名: {user[1]}, 类型: {user[2]}, 客户端ID: {user[3]}")
            
            # 模拟用户加载过程
            user_data = db_manager.execute_query(
                'SELECT * FROM users WHERE id = ?',
                (user[0],),
                fetch=True
            )
            
            if user_data:
                user_row = user_data[0]
                print(f"    完整数据: {user_row}")
                print(f"    索引5 (client_id): {user_row[5] if len(user_row) > 5 else 'None'}")
        
    except Exception as e:
        print(f"查询错误: {e}")

if __name__ == "__main__":
    test_user_loading()
