#!/usr/bin/env python3
"""
测试联邦学习训练日志系统的脚本
"""

import requests
import json
import time


def test_training_logs():
    """测试训练和日志功能"""
    base_url = "http://127.0.0.1:5000"

    # 1. 首先登录为服务器用户
    login_data = {"username": "server", "password": "1"}

    session = requests.Session()

    print("🔐 正在登录服务器...")
    login_response = session.post(f"{base_url}/", data=login_data)

    if login_response.status_code == 200:
        print("✅ 服务器登录成功")
    else:
        print("❌ 服务器登录失败")
        return

    # 2. 获取初始状态
    print("\n📊 获取初始服务器状态...")
    status_response = session.get(f"{base_url}/api/server/status")
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"初始训练状态: {status_data['training_status']['is_training']}")
        print(f"客户端数量: {status_data['client_count']}")
        print(f"服务器日志数量: {len(status_data['server_logs'])}")
        print(f"训练日志数量: {len(status_data['training_logs'])}")

    # 3. 启动训练
    print("\n🚀 启动联邦学习训练...")
    training_config = {"global_rounds": 2, "local_epochs": 1}  # 使用较少轮数以快速测试

    start_response = session.post(
        f"{base_url}/server/start_training", json=training_config
    )

    if start_response.status_code == 200:
        print("✅ 训练启动成功")
        result = start_response.json()
        print(f"响应: {result['message']}")
    else:
        print("❌ 训练启动失败")
        print(f"错误: {start_response.text}")
        return

    # 4. 监控训练进度和日志
    print("\n📈 监控训练进度和日志...")
    max_attempts = 30  # 最多等待30次（约5分钟）
    attempt = 0

    while attempt < max_attempts:
        time.sleep(10)  # 每10秒检查一次
        attempt += 1

        status_response = session.get(f"{base_url}/api/server/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            training_status = status_data["training_status"]

            print(f"\n--- 第{attempt}次检查 ---")
            print(
                f"训练状态: {'进行中' if training_status['is_training'] else '已完成'}"
            )
            print(
                f"当前轮次: {training_status['current_round']}/{training_status['total_rounds']}"
            )
            print(f"进度: {training_status['progress']}%")

            # 显示最新的训练日志
            training_logs = status_data["training_logs"]
            if training_logs:
                print("📝 最新训练日志:")
                for log in training_logs[-3:]:  # 显示最后3条日志
                    print(f"  {log}")

            # 显示最新的服务器日志
            server_logs = status_data["server_logs"]
            if server_logs:
                print("🖥️ 最新服务器日志:")
                for log in server_logs[-2:]:  # 显示最后2条日志
                    print(f"  {log}")

            # 如果训练完成，退出循环
            if not training_status["is_training"]:
                print("\n🎉 训练完成！")
                break
        else:
            print(f"❌ 获取状态失败: {status_response.status_code}")

    if attempt >= max_attempts:
        print("\n⏰ 等待超时，训练可能仍在进行中")

    # 5. 获取最终日志统计
    print("\n📊 最终日志统计:")
    final_status = session.get(f"{base_url}/api/server/status")
    if final_status.status_code == 200:
        final_data = final_status.json()
        print(f"总服务器日志: {len(final_data['server_logs'])}")
        print(f"总训练日志: {len(final_data['training_logs'])}")

        print("\n🔍 所有训练日志:")
        for i, log in enumerate(final_data["training_logs"], 1):
            print(f"  {i}. {log}")


if __name__ == "__main__":
    print("🧪 开始测试联邦学习日志系统...")
    test_training_logs()
    print("\n✅ 测试完成！")
