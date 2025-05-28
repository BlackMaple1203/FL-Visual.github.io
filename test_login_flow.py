#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""测试客户端登录和ID显示"""

import requests
import time

def test_client_login():
    """测试客户端登录流程"""
    base_url = "http://127.0.0.1:5000"
    
    # 创建会话
    session = requests.Session()
    
    # 1. 访问登录页面，获取CSRF token
    print("1. 访问登录页面...")
    login_page = session.get(f"{base_url}/login/client")
    print(f"登录页面状态: {login_page.status_code}")
    
    # 2. 提交登录表单
    print("2. 提交登录表单...")
    login_data = {
        'username': 'user1',
        'password': 'password123',
        'account_type': 'client'
    }
    
    login_response = session.post(f"{base_url}/login/client", data=login_data)
    print(f"登录响应状态: {login_response.status_code}")
    print(f"响应URL: {login_response.url}")
      # 3. 访问客户端仪表板
    print("3. 访问客户端仪表板...")
    dashboard_response = session.get(f"{base_url}/client")
    print(f"仪表板状态: {dashboard_response.status_code}")
      # 4. 检查响应内容中的客户端ID
    if dashboard_response.status_code == 200:
        content = dashboard_response.text
        print(f"页面长度: {len(content)} 字符")
        
        if 'CLIENT_VJ3VDJR7' in content:
            print("✓ 客户端ID正确显示在页面中")
        elif '未分配' in content:
            print("✗ 客户端ID显示为'未分配'")
            # 查找具体位置
            pos = content.find('未分配')
            if pos != -1:
                print(f"'未分配'出现在位置: {pos}")
                print(f"周围文本: {content[max(0, pos-50):pos+50]}")
        else:
            print("? 无法确定客户端ID状态")
        
        # 查找客户端ID相关的HTML片段
        import re
        id_pattern = r'<span[^>]*id="client-id"[^>]*>([^<]+)</span>'
        match = re.search(id_pattern, content)
        if match:
            print(f"客户端ID元素内容: '{match.group(1).strip()}'")
        else:
            print("未找到client-id元素")
            
        # 查找client-id-value class
        value_pattern = r'<span[^>]*class="[^"]*client-id-value[^"]*"[^>]*>([^<]+)</span>'
        value_match = re.search(value_pattern, content)
        if value_match:
            print(f"client-id-value内容: '{value_match.group(1).strip()}'")
        
        # 检查是否有登录重定向信息
        if '登录' in content or 'login' in content.lower():
            print("页面包含登录相关内容，可能未正确登录")
        
        # 查找current_user相关内容
        if 'current_user' in content:
            print("页面包含current_user引用")
    
    return session

if __name__ == "__main__":
    test_client_login()
