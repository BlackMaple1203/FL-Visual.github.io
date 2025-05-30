#!/usr/bin/env python3
"""
LUNA16肺结节检测项目主运行脚本

该脚本提供了完整的训练和推理流程：
1. 训练MONAI UNet模型检测肺结节
2. 使用训练好的模型进行推理
3. 可视化检测结果

使用方法:
    python main.py --mode train                    # 训练模型
    python main.py --mode inference --image_path path/to/image.mhd  # 推理单个图像
    python main.py --mode demo                     # 运行演示
"""

import argparse
import os
import sys


def train_model():
    """训练模型"""
    print("开始训练肺结节检测模型...")
    try:
        from train_simple_model import train_simple_model

        model = train_simple_model()
        print("训练完成！模型已保存为 'best_lung_nodule_model.pth'")
        return True
    except Exception as e:
        print(f"训练过程中出现错误: {e}")
        return False


def train_federated_model(num_clients=3, global_rounds=3, local_epochs=2):
    """训练联邦学习模型"""
    print(f"开始联邦学习训练 - {num_clients}个客户端, {global_rounds}轮全局训练...")
    try:
        from federated_training import train_federated_model

        coordinator = train_federated_model(
            num_clients=num_clients,
            global_rounds=global_rounds,
            local_epochs=local_epochs,
        )
        print("联邦学习训练完成！模型已保存为 'best_federated_lung_nodule_model.pth'")
        return True
    except Exception as e:
        print(f"联邦学习训练过程中出现错误: {e}")
        return False


def run_inference(image_path, use_federated=False):
    """运行推理"""
    if not os.path.exists(image_path):
        print(f"错误: 图像文件不存在 {image_path}")
        return False

    print(f"正在对图像进行推理: {image_path}")
    try:
        if use_federated:
            from federated_inference import (
                predict_with_federated_model,
                visualize_federated_results,
            )

            nodules, prob_map, image, spacing, origin = predict_with_federated_model(
                image_path
            )
            visualize_federated_results(image, prob_map, nodules)
        else:
            from show_nodules import show_predicted_nodules

            show_predicted_nodules(image_path, confidence_threshold=0.3)
        return True
    except Exception as e:
        print(f"推理过程中出现错误: {e}")
        return False


def run_demo(use_federated=False):
    """运行演示"""
    if use_federated:
        print("运行联邦学习演示模式...")
        try:
            from federated_inference import demo_federated_prediction

            demo_federated_prediction()
            return True
        except Exception as e:
            print(f"联邦学习演示过程中出现错误: {e}")
            return False
    else:
        print("运行演示模式...")
        try:
            from show_nodules import demo_with_sample_data

            demo_with_sample_data()
            return True
        except Exception as e:
            print(f"演示过程中出现错误: {e}")
            return False


def check_dependencies():
    """检查依赖"""
    required_packages = [
        "torch",
        "monai",
        "numpy",
        "matplotlib",
        "pandas",
        "SimpleITK",
        "scipy",
        "tqdm",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("缺少以下依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装:")
        print("pip install -r requirements.txt")
        return False

    return True


def check_data():
    """检查数据"""
    data_dir = "./LUNA16"
    csv_path = "./LUNA16/CSVFILES/annotations.csv"

    if not os.path.exists(data_dir):
        print(f"错误: 数据目录不存在 {data_dir}")
        print("请确保LUNA16数据集已正确放置在当前目录下")
        return False

    if not os.path.exists(csv_path):
        print(f"错误: 标注文件不存在 {csv_path}")
        return False

    # 检查至少有一个subset目录
    subset_found = False
    for i in range(10):
        subset_path = os.path.join(data_dir, f"subset{i}")
        if os.path.exists(subset_path):
            subset_found = True
            break

    if not subset_found:
        print("错误: 未找到任何subset目录")
        return False

    print("数据检查通过")
    return True


def main():
    parser = argparse.ArgumentParser(description="LUNA16肺结节检测项目")
    parser.add_argument(
        "--mode",
        choices=["train", "inference", "demo", "federated_train", "federated_demo"],
        required=True,
        help="运行模式: train(训练), inference(推理), demo(演示), federated_train(联邦学习训练), federated_demo(联邦学习演示)",
    )
    parser.add_argument("--image_path", type=str, help="用于推理的图像路径(.mhd文件)")
    parser.add_argument(
        "--model_path",
        type=str,
        default="best_lung_nodule_model.pth",
        help="模型文件路径",
    )
    parser.add_argument(
        "--confidence_threshold", type=float, default=0.3, help="结节检测的置信度阈值"
    )

    # 联邦学习参数
    parser.add_argument("--num_clients", type=int, default=3, help="联邦学习客户端数量")
    parser.add_argument(
        "--global_rounds", type=int, default=3, help="联邦学习全局训练轮数"
    )
    parser.add_argument(
        "--local_epochs", type=int, default=2, help="联邦学习本地训练轮数"
    )
    parser.add_argument(
        "--use_federated", action="store_true", help="使用联邦学习模型进行推理"
    )

    args = parser.parse_args()

    print("LUNA16肺结节检测项目")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        return

    # 检查数据（演示模式和推理模式需要）
    if args.mode in ["demo", "inference", "train", "federated_train", "federated_demo"]:
        if not check_data():
            return

    # 根据模式执行相应操作
    if args.mode == "train":
        success = train_model()
        if success:
            print("\n✅ 训练完成！可以使用以下命令进行推理:")
            print("python main.py --mode demo")

    elif args.mode == "federated_train":
        success = train_federated_model(
            num_clients=args.num_clients,
            global_rounds=args.global_rounds,
            local_epochs=args.local_epochs,
        )
        if success:
            print("\n✅ 联邦学习训练完成！可以使用以下命令进行演示:")
            print("python main.py --mode federated_demo")

    elif args.mode == "inference":
        if not args.image_path:
            print("错误: 推理模式需要指定 --image_path 参数")
            return

        model_path = args.model_path
        if args.use_federated:
            model_path = "best_federated_lung_nodule_model.pth"

        if not os.path.exists(model_path):
            print(f"警告: 模型文件不存在 {model_path}")
            print("将使用随机初始化的模型进行演示")

        success = run_inference(args.image_path, args.use_federated)
        if success:
            print("✅ 推理完成！")

    elif args.mode == "demo":
        model_path = args.model_path
        if args.use_federated:
            model_path = "best_federated_lung_nodule_model.pth"

        if not os.path.exists(model_path):
            print(f"警告: 模型文件不存在 {model_path}")
            print("将使用随机初始化的模型进行演示")

        success = run_demo(args.use_federated)
        if success:
            print("✅ 演示完成！")

    elif args.mode == "federated_demo":
        model_path = "best_federated_lung_nodule_model.pth"
        if not os.path.exists(model_path):
            print(f"警告: 联邦学习模型文件不存在 {model_path}")
            print("将使用随机初始化的模型进行演示")

        success = run_demo(use_federated=True)
        if success:
            print("✅ 联邦学习演示完成！")


if __name__ == "__main__":
    main()
