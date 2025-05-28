#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_login_and_client_id():
    """测试登录功能和客户端ID显示"""
    base_url = "http://127.0.0.1:5000"
    
    # 创建会话
    session = requests.Session()
    
    try:
        # 先访问登录页面获取CSRF token等
        login_page = session.get(f"{base_url}/login?session_type=client")
        print(f"登录页面访问状态: {login_page.status_code}")
        
        # 登录请求
        login_data = {
            'username': 'user1',
            'password': 'password123'  # 假设密码是这个，可能需要调整
        }
        
        login_response = session.post(f"{base_url}/login?session_type=client", data=login_data)
        print(f"登录响应状态: {login_response.status_code}")
        
        # 如果登录成功，访问客户端仪表板
        if login_response.status_code == 200 or login_response.status_code == 302:
            dashboard_response = session.get(f"{base_url}/client/dashboard")
            print(f"仪表板访问状态: {dashboard_response.status_code}")
            
            # 检查响应内容中是否包含客户端ID
            if 'CLIENT_VJ3VDJR7' in dashboard_response.text:
                print("✅ 客户端ID显示正常: CLIENT_VJ3VDJR7")
            elif '未分配' in dashboard_response.text:
                print("❌ 客户端ID显示为'未分配'")
            else:
                print("⚠️ 客户端ID状态未知")
                
        else:
            print("❌ 登录失败")
            print(f"响应内容: {login_response.text[:500]}")
            
    except Exception as e:
        print(f"测试过程中出错: {e}")

if __name__ == "__main__":
    test_login_and_client_id()
