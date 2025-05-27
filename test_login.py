#!/usr/bin/env python3
"""
快速测试脚本：自动登录并访问服务器仪表板
"""

import requests
import webbrowser

# 应用基础URL
BASE_URL = "http://127.0.0.1:5000"

def test_login_and_dashboard():
    """测试登录并访问服务器仪表板"""
    session = requests.Session()
    
    # 首先获取登录页面以获取任何CSRF tokens
    login_page = session.get(f"{BASE_URL}/login")
    print(f"登录页面状态码: {login_page.status_code}")
    
    # 尝试登录
    login_data = {
        'username': 'admin',
        'password': 'admin123',  # 假设密码
        'account_type': 'server'
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"登录请求状态码: {response.status_code}")
    
    if response.status_code in [200, 302]:
        # 尝试访问服务器仪表板
        dashboard_response = session.get(f"{BASE_URL}/server/dashboard")
        print(f"仪表板访问状态码: {dashboard_response.status_code}")
        
        if dashboard_response.status_code == 200:
            print("✅ 成功访问服务器仪表板!")
            print("在浏览器中打开仪表板...")
            webbrowser.open(f"{BASE_URL}/server/dashboard")
        else:
            print("❌ 无法访问仪表板")
            print("尝试直接在浏览器中访问...")
            webbrowser.open(f"{BASE_URL}/login")
    else:
        print("❌ 登录失败")
        print("在浏览器中打开登录页面...")
        webbrowser.open(f"{BASE_URL}/login")

if __name__ == "__main__":
    test_login_and_dashboard()
