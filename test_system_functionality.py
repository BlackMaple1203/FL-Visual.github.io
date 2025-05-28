#!/usr/bin/env python3
"""
联邦学习系统功能测试脚本
测试所有主要功能包括：登录、注册、节点管理、数据上传、训练等
"""
import requests
import json
import time
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import os

BASE_URL = "http://127.0.0.1:5000"

class SystemTester:    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        # 使用时间戳确保用户名唯一
        import time
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
        
        # 使用时间戳确保用户名唯一
        import time
        timestamp = str(int(time.time()))
        
        # 测试客户端注册
        client_data = {
            "username": f"test_client_{timestamp}",
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
                    self.log_test("客户端注册", True, f"客户端ID: {result.get('client_id', 'N/A')}")
                else:
                    self.log_test("客户端注册", False, result.get('message', '未知错误'))
            else:
                self.log_test("客户端注册", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("客户端注册", False, str(e))
          # 测试服务器端注册
        server_data = {
            "username": f"test_server_{timestamp}",
            "password": "test123456", 
            "confirmPassword": "test123456",
            "account_type": "server"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/register",
                                       json=server_data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("服务器端注册", True)
                else:
                    self.log_test("服务器端注册", False, result.get('message', '未知错误'))
            else:
                self.log_test("服务器端注册", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("服务器端注册", False, str(e))
    
    def test_login(self):
        """测试登录功能"""
        print("\n=== 测试登录功能 ===")
        
        # 测试客户端登录
        client_login = {
            "username": "test_client_001",
            "password": "test123456"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/login",
                                       json=client_login,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("客户端登录", True, "登录成功，获得会话")
                    self.client_session = self.session
                else:
                    self.log_test("客户端登录", False, result.get('message', '未知错误'))
            else:
                self.log_test("客户端登录", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("客户端登录", False, str(e))
      def test_client_dashboard_access(self):
        """测试客户端控制台访问"""
        print("\n=== 测试控制台访问 ===")
        
        try:
            response = self.session.get(f"{BASE_URL}/client")
            
            if response.status_code == 200:
                # 检查是否包含客户端ID显示
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
    
    def test_api_endpoints(self):
        """测试API端点"""
        print("\n=== 测试API端点 ===")
          # 测试客户端状态API
        try:
            response = self.session.get(f"{BASE_URL}/api/client_status")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # 客户端调用时返回状态信息，服务器调用时返回节点列表
                    if 'nodes' in data:
                        self.log_test("客户端状态API", True, f"返回 {len(data['nodes'])} 个客户端状态")
                    else:
                        self.log_test("客户端状态API", True, "返回客户端状态信息")
                else:
                    self.log_test("客户端状态API", False, data.get('message', '未知错误'))
            else:
                self.log_test("客户端状态API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("客户端状态API", False, str(e))
            self.log_test("客户端状态API", False, str(e))
        
        # 测试服务器节点API
        try:
            response = self.session.get(f"{BASE_URL}/api/server_nodes")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("服务器节点API", True, f"返回 {len(data)} 个节点")
                else:
                    self.log_test("服务器节点API", False, "返回数据格式错误")
            else:
                self.log_test("服务器节点API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("服务器节点API", False, str(e))
            
        # 测试服务器日志API
        try:
            response = self.session.get(f"{BASE_URL}/api/server_logs")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("服务器日志API", True, f"返回 {len(data)} 条日志")
                else:
                    self.log_test("服务器日志API", False, "返回数据格式错误")
            else:
                self.log_test("服务器日志API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("服务器日志API", False, str(e))
    
    def test_error_handling(self):
        """测试错误处理"""
        print("\n=== 测试错误处理 ===")
        
        # 测试重复用户名注册
        duplicate_user = {
            "username": "test_client_001",  # 已存在用户名
            "password": "test123456",
            "confirmPassword": "test123456",
            "account_type": "client"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/register",
                                       json=duplicate_user,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 400:
                result = response.json()
                if not result.get('success') and '已存在' in result.get('message', ''):
                    self.log_test("重复用户名错误处理", True, "正确拒绝重复用户名")
                else:
                    self.log_test("重复用户名错误处理", False, "错误消息不正确")
            else:
                self.log_test("重复用户名错误处理", False, f"应返回400但返回{response.status_code}")
                
        except Exception as e:
            self.log_test("重复用户名错误处理", False, str(e))
        
        # 测试错误登录
        wrong_login = {
            "username": "nonexistent_user",
            "password": "wrongpassword"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/login",
                                       json=wrong_login,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 401:
                result = response.json()
                if not result.get('success'):
                    self.log_test("错误登录处理", True, "正确拒绝错误凭据")
                else:
                    self.log_test("错误登录处理", False, "未正确处理错误登录")
            else:
                self.log_test("错误登录处理", False, f"应返回401但返回{response.status_code}")
                
        except Exception as e:
            self.log_test("错误登录处理", False, str(e))
    
    def test_data_upload_simulation(self):
        """测试数据上传模拟"""
        print("\n=== 测试数据上传功能 ===")
        
        # 创建测试文件
        test_file_content = b"Mock NII.GZ file content for testing"
        test_filename = "test_brain_scan.nii.gz"
        
        try:
            files = {'file': (test_filename, test_file_content, 'application/gzip')}
            response = self.session.post(f"{BASE_URL}/api/upload_data", files=files)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("数据上传", True, f"文件上传成功: {result.get('filename')}")
                else:
                    self.log_test("数据上传", False, result.get('message', '未知错误'))
            else:
                self.log_test("数据上传", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("数据上传", False, str(e))
    
    def test_server_dashboard_features(self):
        """测试服务器控制台功能"""
        print("\n=== 测试服务器控制台功能 ===")
        
        # 新建会话测试服务器端
        server_session = requests.Session()
        
        # 登录服务器端
        server_login = {
            "username": "test_server_001",
            "password": "test123456"
        }
        
        try:
            response = server_session.post(f"{BASE_URL}/login",
                                         json=server_login,
                                         headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.log_test("服务器端登录", True, "服务器端登录成功")
                      # 测试服务器控制台访问
                    dashboard_response = server_session.get(f"{BASE_URL}/server")
                    if dashboard_response.status_code == 200:
                        self.log_test("服务器控制台访问", True, "服务器控制台可正常访问")
                    else:
                        self.log_test("服务器控制台访问", False, f"HTTP {dashboard_response.status_code}")
                        
                else:
                    self.log_test("服务器端登录", False, result.get('message', '未知错误'))
            else:
                self.log_test("服务器端登录", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("服务器端登录", False, str(e))
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始系统功能测试...")
        print("=" * 50)
        
        start_time = time.time()
        
        # 运行各项测试
        self.test_registration()
        self.test_login()
        self.test_client_dashboard_access()
        self.test_api_endpoints()
        self.test_error_handling()
        self.test_data_upload_simulation()
        self.test_server_dashboard_features()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 统计测试结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 50)
        print("📊 测试结果汇总")
        print("=" * 50)
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        print(f"测试用时: {duration:.2f}秒")
        
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        return passed_tests == total_tests

def main():
    """主函数"""
    print("联邦学习系统功能测试")
    print("=" * 50)
    
    # 检查服务器是否运行
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code != 200:
            print("❌ 服务器未运行或无法访问")
            print("请确保在运行测试前启动应用: python app.py")
            return False
    except requests.exceptions.RequestException:
        print("❌ 无法连接到服务器")
        print("请确保在运行测试前启动应用: python app.py")
        return False
    
    print("✅ 服务器连接正常")
    
    # 运行测试
    tester = SystemTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 所有测试通过！系统功能正常。")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查相关功能。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
