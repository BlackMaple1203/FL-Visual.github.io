#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import threading
import time
from contextlib import contextmanager

class DatabaseManager:
    """数据库管理器，提供安全的数据库连接管理"""
    
    def __init__(self, db_path, timeout=30):
        self.db_path = db_path
        self.timeout = timeout
        self._local = threading.local()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            # 设置较长的超时时间和其他安全参数
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False
            )
            # 启用WAL模式以减少锁定问题
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=10000')
            conn.execute('PRAGMA temp_store=memory')
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query, params=None, fetch=False):
        """安全执行查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                result = cursor.fetchall()
                conn.commit()
                return result
            else:
                conn.commit()
                return cursor.lastrowid if cursor.lastrowid else None
    
    def execute_many(self, query, param_list):
        """批量执行查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, param_list)
            conn.commit()
            return cursor.rowcount

# 创建全局数据库管理器实例
db_manager = DatabaseManager('federated_learning.db')

def safe_log_server_event(client_id, event_type, message):
    """安全记录服务端日志"""
    try:
        db_manager.execute_query('''
            INSERT INTO server_logs (client_id, event_type, message)
            VALUES (?, ?, ?)
        ''', (client_id, event_type, message))
    except Exception as e:
        print(f"记录日志时出错: {e}")

def safe_update_client_status(client_id, status=None, has_uploaded_data=None, is_training=None, training_progress=None):
    """安全更新客户端状态"""
    try:
        # 构建动态更新查询
        update_fields = []
        params = []
        
        if status is not None:
            update_fields.append("status = ?")
            params.append(status)
        if has_uploaded_data is not None:
            update_fields.append("has_uploaded_data = ?")
            params.append(has_uploaded_data)
        if is_training is not None:
            update_fields.append("is_training = ?")
            params.append(is_training)
        if training_progress is not None:
            update_fields.append("training_progress = ?")
            params.append(training_progress)
        
        if not update_fields:
            return
        
        # 总是更新last_activity
        update_fields.append("last_activity = CURRENT_TIMESTAMP")
        params.append(client_id)
        
        query = f'''
            UPDATE client_status 
            SET {', '.join(update_fields)}
            WHERE client_id = ?
        '''
        
        db_manager.execute_query(query, params)
        
    except Exception as e:
        print(f"更新客户端状态时出错: {e}")

def safe_get_client_status():
    """安全获取客户端状态"""
    try:
        return db_manager.execute_query('''
            SELECT client_id, status, has_uploaded_data, is_training, 
                   training_progress, last_activity
            FROM client_status
            ORDER BY last_activity DESC
        ''', fetch=True)
    except Exception as e:
        print(f"获取客户端状态时出错: {e}")
        return []

def safe_get_server_logs(limit=50):
    """安全获取服务端日志"""
    try:
        return db_manager.execute_query('''
            SELECT client_id, event_type, message, timestamp
            FROM server_logs
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,), fetch=True)
    except Exception as e:
        print(f"获取服务端日志时出错: {e}")
        return []
