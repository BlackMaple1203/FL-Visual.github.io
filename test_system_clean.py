#!/usr/bin/env python3
"""
联邦学习系统功能测试脚本 - 清洁版
测试所有主要功能包括：登录、注册、节点管理、数据上传、训练等
"""
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:5000"

class SystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.server_session = requests.Session()  # 专门用于服务器端测试
        self.test_results = []
        # 使用时间戳确保用户名唯一
        timestamp = str(int(time.time()))
        self.client_username = f"test_client_{timestamp}"
        self.server_username = f"test_server_{timestamp}"
        
    def log_test(self, test_name, success, message=""):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
    
    def test_registration(self):
        """测试用户注册功能"""
        print("\n=== 测试用户注册功能 ===")
        
        # 测试客户端注册
        client_data = {
            "username": self.client_username,
            "password": "test123456",
            "confirmPassword": "test123456",
            "account_type": "client"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/register", 
                                       json=client_data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("客户端注册", True, f"用户 {self.client_username} 注册成功")
                else:
                    self.log_test("客户端注册", False, result.get('message', '注册失败'))
            else:
                self.log_test("客户端注册", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("客户端注册", False, str(e))
        
        # 测试服务器注册
        server_data = {
            "username": self.server_username,
            "password": "server123456",
            "confirmPassword": "server123456", 
            "account_type": "server"
        }
        
        try:
            response = self.server_session.post(f"{BASE_URL}/register", 
                                               json=server_data,
                                               headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("服务器注册", True, f"用户 {self.server_username} 注册成功")
                else:
                    self.log_test("服务器注册", False, result.get('message', '注册失败'))
            else:
                self.log_test("服务器注册", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("服务器注册", False, str(e))
    
    def test_login(self):
        """测试用户登录功能"""
        print("\n=== 测试用户登录功能 ===")
        
        # 测试客户端登录
        client_login_data = {
            "username": self.client_username,
            "password": "test123456"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/login", 
                                       json=client_login_data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("客户端登录", True, f"用户 {self.client_username} 登录成功")
                else:
                    self.log_test("客户端登录", False, result.get('message', '登录失败'))
            else:
                self.log_test("客户端登录", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("客户端登录", False, str(e))
        
        # 测试服务器登录
        server_login_data = {
            "username": self.server_username,
            "password": "server123456"
        }
        
        try:
            response = self.server_session.post(f"{BASE_URL}/login", 
                                               json=server_login_data,
                                               headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("服务器登录", True, f"用户 {self.server_username} 登录成功")
                else:
                    self.log_test("服务器登录", False, result.get('message', '登录失败'))
            else:
                self.log_test("服务器登录", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("服务器登录", False, str(e))
    
    def test_dashboard_access(self):
        """测试控制台访问"""
        print("\n=== 测试控制台访问 ===")
        
        # 测试客户端控制台
        try:
            response = self.session.get(f"{BASE_URL}/client")
            
            if response.status_code == 200:
                if "client-id" in response.text and "未分配" not in response.text:
                    self.log_test("客户端控制台访问", True, "控制台正常显示，包含客户端ID")
                elif "未分配" in response.text:
                    self.log_test("客户端控制台访问", False, "客户端ID显示为'未分配'")
                else:
                    self.log_test("客户端控制台访问", True, "控制台可访问但需要验证客户端ID")
            else:
                self.log_test("客户端控制台访问", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("客户端控制台访问", False, str(e))
        
        # 测试服务器控制台
        try:
            response = self.server_session.get(f"{BASE_URL}/server")
            
            if response.status_code == 200:
                if "server-controls" in response.text or "客户端节点" in response.text:
                    self.log_test("服务器控制台访问", True, "服务器控制台可正常访问")
                else:
                    self.log_test("服务器控制台访问", True, "服务器控制台可访问但需要验证内容")
            else:
                self.log_test("服务器控制台访问", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("服务器控制台访问", False, str(e))
    
    def test_api_endpoints(self):
        """测试API端点"""
        print("\n=== 测试API端点 ===")
        
        # 测试客户端状态API（使用客户端会话）
        try:
            response = self.session.get(f"{BASE_URL}/api/client_status")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("客户端状态API", True, "API返回正确格式的响应")
                else:
                    self.log_test("客户端状态API", False, "API响应格式不正确")
            else:
                self.log_test("客户端状态API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("客户端状态API", False, str(e))
        
        # 测试服务器端的客户端状态API（使用服务器会话）
        try:
            response = self.server_session.get(f"{BASE_URL}/api/client_status")
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'nodes' in data:
                    self.log_test("服务器端客户端状态API", True, f"返回 {len(data['nodes'])} 个客户端状态")
                else:
                    self.log_test("服务器端客户端状态API", False, "API响应格式不正确")
            else:
                self.log_test("服务器端客户端状态API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("服务器端客户端状态API", False, str(e))
        
        # 测试训练状态API（使用服务器会话）
        try:
            response = self.server_session.get(f"{BASE_URL}/api/training_status")
            if response.status_code == 200:
                data = response.json()
                if 'status' in data:
                    self.log_test("训练状态API", True, f"训练状态: {data['status']}")
                else:
                    self.log_test("训练状态API", False, "API响应格式不正确")
            else:
                self.log_test("训练状态API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("训练状态API", False, str(e))
      def test_data_upload(self):
        """测试数据上传功能"""
        print("\n=== 测试数据上传功能 ===")
        
        # 创建一个模拟的.nii.gz文件
        test_data = b"模拟的医疗影像数据内容，用于验证上传功能"
        
        try:
            files = {
                'file': ('test_brain_scan.nii.gz', test_data, 'application/gzip')
            }
            
            response = self.session.post(f"{BASE_URL}/api/upload_data", files=files)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("数据上传", True, result.get('message', '上传成功'))
                else:
                    self.log_test("数据上传", False, result.get('message', '上传失败'))
            else:
                self.log_test("数据上传", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("数据上传", False, str(e))
    
    def test_error_handling(self):
        """测试错误处理"""
        print("\n=== 测试错误处理 ===")
        
        # 测试无效登录
        try:
            invalid_login = {
                "username": "invalid_user", 
                "password": "wrong_password"
            }
            
            response = self.session.post(f"{BASE_URL}/login", 
                                       json=invalid_login,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                if not result.get('success'):
                    self.log_test("错误处理-无效登录", True, "正确返回登录失败")
                else:
                    self.log_test("错误处理-无效登录", False, "应该返回登录失败但却成功了")
            else:
                self.log_test("错误处理-无效登录", True, f"正确返回HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("错误处理-无效登录", False, str(e))
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*50)
        print("测试结果摘要")
        print("="*50)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print("\n" + "="*50)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始联邦学习系统功能测试...")
        print(f"测试目标: {BASE_URL}")
        
        # 按顺序运行测试
        self.test_registration()
        self.test_login()
        self.test_dashboard_access()
        self.test_api_endpoints()
        self.test_data_upload()
        self.test_error_handling()
        
        # 打印摘要
        self.print_summary()

if __name__ == "__main__":
    # 检查服务器是否运行
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✅ 服务器连接成功 (HTTP {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务器 {BASE_URL}")
        print(f"错误: {e}")
        print("请确保Flask服务器正在运行")
        sys.exit(1)
    
    # 运行测试
    tester = SystemTester()
    tester.run_all_tests()
