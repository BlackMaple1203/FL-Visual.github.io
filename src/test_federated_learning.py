#!/usr/bin/env python3
"""
联邦学习快速测试脚本
用于验证联邦学习功能的基本可用性
"""

import sys
import os
import subprocess
import time


def run_command(cmd, description):
    """运行命令并记录结果"""
    print(f"\n{'='*50}")
    print(f"🔄 {description}")
    print(f"命令: {cmd}")
    print(f"{'='*50}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ 成功! 耗时: {elapsed:.1f}秒")
            if result.stdout:
                print("输出:")
                print(result.stdout[-500:])  # 只显示最后500个字符
        else:
            print(f"❌ 失败! 返回码: {result.returncode}")
            if result.stderr:
                print("错误信息:")
                print(result.stderr[-500:])

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"⏰ 超时! (5分钟)")
        return False
    except Exception as e:
        print(f"💥 异常: {e}")
        return False


def check_files():
    """检查必要文件是否存在"""
    print("📁 检查项目文件...")

    required_files = [
        "main.py",
        "federated_training.py",
        "federated_inference.py",
        "train_simple_model.py",
        "LUNA16/CSVFILES/annotations.csv",
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        return False
    else:
        print("✅ 所有必要文件存在")
        return True


def main():
    """主测试流程"""
    print("🚀 联邦学习快速测试开始")
    print(f"当前目录: {os.getcwd()}")

    # 1. 检查文件
    if not check_files():
        print("❌ 文件检查失败，退出测试")
        return False

    # 2. 测试联邦学习训练（最小配置）
    training_success = run_command(
        "python main.py --mode federated_train --num_clients 2 --global_rounds 1 --local_epochs 1",
        "联邦学习训练测试（2客户端，1轮）",
    )

    # 3. 检查模型文件是否生成
    model_file = "best_federated_lung_nodule_model.pth"
    if os.path.exists(model_file):
        file_size = os.path.getsize(model_file) / (1024 * 1024)  # MB
        print(f"✅ 联邦模型文件已生成: {model_file} ({file_size:.1f}MB)")
        model_exists = True
    else:
        print(f"❌ 联邦模型文件未生成: {model_file}")
        model_exists = False

    # 4. 测试联邦推理（如果模型存在）
    if model_exists:
        # 找一个示例图像
        sample_image = None
        for subset in range(10):
            subset_dir = f"LUNA16/subset{subset}"
            if os.path.exists(subset_dir):
                for file in os.listdir(subset_dir):
                    if file.endswith(".mhd"):
                        sample_image = os.path.join(subset_dir, file)
                        break
                if sample_image:
                    break

        if sample_image:
            inference_success = run_command(
                f"timeout 60 python main.py --mode inference --use_federated --image_path '{sample_image}'",
                "联邦推理测试（60秒超时）",
            )
        else:
            print("⚠️  未找到测试图像，跳过推理测试")
            inference_success = True
    else:
        print("⚠️  模型不存在，跳过推理测试")
        inference_success = False

    # 5. 总结
    print(f"\n{'='*60}")
    print("🎯 测试总结")
    print(f"{'='*60}")
    print(f"文件检查: ✅")
    print(f"联邦训练: {'✅' if training_success else '❌'}")
    print(f"模型生成: {'✅' if model_exists else '❌'}")
    print(f"联邦推理: {'✅' if inference_success else '❌'}")

    overall_success = training_success and model_exists

    if overall_success:
        print(f"\n🎉 联邦学习功能测试通过!")
        print(f"可以开始使用联邦学习功能了:")
        print(f"  - 训练: python main.py --mode federated_train")
        print(
            f"  - 推理: python main.py --mode inference --use_federated --image_path <path>"
        )
        print(f"  - 演示: python main.py --mode federated_demo")
    else:
        print(f"\n❌ 测试失败，需要检查和修复问题")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
