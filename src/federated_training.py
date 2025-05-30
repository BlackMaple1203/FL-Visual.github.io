"""
联邦学习训练系统 - LUNA16肺结节检测
使用FedAvg算法进行分布式训练

主要组件:
1. FederatedServer: 联邦服务器，负责模型聚合
2. FederatedClient: 联邦客户端，负责本地训练
3. FedAvg算法实现
4. 数据分片和分布
"""

import os
import copy
import numpy as np
import pandas as pd
import SimpleITK as sitk
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, Subset
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings
from typing import List, Dict, Tuple
import random
from collections import OrderedDict

# 导入简化的模型和数据集
from train_simple_model import Simple3DUNet, SimpleLUNA16Dataset, DiceLoss

warnings.filterwarnings("ignore")


class FederatedServer:
    """联邦学习服务器"""

    def __init__(self, model_class, model_kwargs, device="cpu"):
        """
        初始化联邦服务器

        Args:
            model_class: 模型类
            model_kwargs: 模型初始化参数
            device: 计算设备
        """
        self.device = device
        self.global_model = model_class(**model_kwargs).to(device)
        self.model_class = model_class
        self.model_kwargs = model_kwargs
        self.round_num = 0

        # 存储训练历史
        self.training_history = {"rounds": [], "avg_loss": [], "client_losses": []}

    def get_global_model_params(self):
        """获取全局模型参数"""
        return copy.deepcopy(self.global_model.state_dict())

    def federated_averaging(
        self, client_params_list: List[Dict], client_weights: List[float]
    ):
        """
        执行FedAvg算法 - 联邦平均

        Args:
            client_params_list: 客户端模型参数列表
            client_weights: 客户端权重（通常基于数据量）
        """
        try:
            # 确保权重归一化
            total_weight = sum(client_weights)
            normalized_weights = [w / total_weight for w in client_weights]

            print(
                f"开始模型聚合 - {len(client_params_list)} 个客户端，权重: {normalized_weights}"
            )

            # 初始化聚合参数
            global_params = OrderedDict()

            # 获取第一个客户端的参数结构
            first_client_params = client_params_list[0]

            # 对每个参数进行加权平均
            for param_name in first_client_params.keys():
                param_tensor = first_client_params[param_name]

                # 检查是否是需要跳过的参数（如BatchNorm的num_batches_tracked）
                if param_name.endswith("num_batches_tracked"):
                    # 对于不需要聚合的参数，直接使用第一个客户端的值
                    global_params[param_name] = param_tensor.clone()
                    continue

                # 确保参数是浮点类型以支持加权平均
                if param_tensor.dtype in [torch.int32, torch.int64, torch.long]:
                    # 对于整型参数，取第一个客户端的值（通常是索引类型参数）
                    global_params[param_name] = param_tensor.clone()
                    continue

                # 对浮点参数进行加权求和
                weighted_sum = torch.zeros_like(param_tensor, dtype=torch.float32)

                for client_params, weight in zip(
                    client_params_list, normalized_weights
                ):
                    client_param = client_params[param_name]
                    if client_param.dtype != torch.float32:
                        client_param = client_param.float()
                    weighted_sum += weight * client_param

                # 恢复原始数据类型
                if param_tensor.dtype != torch.float32:
                    weighted_sum = weighted_sum.to(param_tensor.dtype)

                global_params[param_name] = weighted_sum

            # 更新全局模型
            self.global_model.load_state_dict(global_params)
            self.round_num += 1

            print(f"✅ 全局模型已更新 - 第 {self.round_num} 轮")

        except Exception as e:
            print(f"❌ 模型聚合过程中出现错误: {e}")
            print(f"错误类型: {type(e).__name__}")
            raise e

    def evaluate_global_model(self, test_loader):
        """评估全局模型性能"""
        self.global_model.eval()
        total_loss = 0.0
        num_batches = 0

        criterion = DiceLoss()  # 使用原始训练的DiceLoss

        with torch.no_grad():
            for batch in test_loader:
                if batch["series_uid"][0] == "error":
                    continue

                images = batch["image"].to(self.device)
                labels = batch["label"].to(self.device)

                outputs = self.global_model(images)
                loss = criterion(outputs, labels)

                total_loss += loss.item()
                num_batches += 1

        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        print(f"全局模型验证损失: {avg_loss:.4f}")

        return avg_loss

    def save_global_model(self, save_path="federated_global_model.pth"):
        """保存全局模型"""
        torch.save(
            {
                "model_state_dict": self.global_model.state_dict(),
                "round_num": self.round_num,
                "training_history": self.training_history,
            },
            save_path,
        )
        print(f"全局模型已保存到: {save_path}")


class FederatedClient:
    """联邦学习客户端"""

    def __init__(self, client_id: int, model_class, model_kwargs, device="cpu"):
        """
        初始化联邦客户端

        Args:
            client_id: 客户端ID
            model_class: 模型类
            model_kwargs: 模型初始化参数
            device: 计算设备
        """
        self.client_id = client_id
        self.device = device
        self.model = model_class(**model_kwargs).to(device)
        self.model_class = model_class
        self.model_kwargs = model_kwargs

        # 本地训练参数
        self.learning_rate = 0.001
        self.local_epochs = 3

        # 训练历史
        self.training_history = []

    def load_global_model(self, global_params: Dict):
        """加载全局模型参数"""
        self.model.load_state_dict(global_params)

    def local_train(self, train_loader, epochs=None):
        """
        执行本地训练

        Args:
            train_loader: 训练数据加载器
            epochs: 本地训练轮数

        Returns:
            训练损失列表
        """
        if epochs is None:
            epochs = self.local_epochs

        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        criterion = DiceLoss()  # 使用原始训练的DiceLoss

        epoch_losses = []

        print(f"客户端 {self.client_id} 开始本地训练 ({epochs} 轮)...")

        for epoch in range(epochs):
            total_loss = 0.0
            num_batches = 0

            for batch_idx, batch in enumerate(train_loader):
                try:
                    if batch["series_uid"][0] == "error":
                        continue

                    images = batch["image"].to(self.device)
                    labels = batch["label"].to(self.device)

                    optimizer.zero_grad()
                    outputs = self.model(images)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()

                    total_loss += loss.item()
                    num_batches += 1

                    if batch_idx % 5 == 0:
                        print(
                            f"  客户端 {self.client_id} - Epoch {epoch+1}/{epochs}, "
                            f"Batch {batch_idx+1}, Loss: {loss.item():.4f}"
                        )

                except Exception as e:
                    print(f"  客户端 {self.client_id} 训练出错: {e}")
                    continue

            avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
            epoch_losses.append(avg_loss)
            print(
                f"  客户端 {self.client_id} - Epoch {epoch+1} 平均损失: {avg_loss:.4f}"
            )

        self.training_history.extend(epoch_losses)
        return epoch_losses

    def get_model_params(self):
        """获取本地模型参数"""
        return copy.deepcopy(self.model.state_dict())

    def get_data_size(self, data_loader):
        """获取数据集大小"""
        return len(data_loader.dataset)


class FederatedLearningCoordinator:
    """联邦学习协调器"""

    def __init__(
        self, num_clients=3, model_class=Simple3DUNet, model_kwargs=None, device="cpu"
    ):
        """
        初始化联邦学习协调器

        Args:
            num_clients: 客户端数量
            model_class: 模型类
            model_kwargs: 模型初始化参数
            device: 计算设备
        """
        if model_kwargs is None:
            model_kwargs = {"in_channels": 1, "out_channels": 2}

        self.num_clients = num_clients
        self.device = device

        # 创建服务器
        self.server = FederatedServer(model_class, model_kwargs, device)

        # 创建客户端
        self.clients = [
            FederatedClient(i, model_class, model_kwargs, device)
            for i in range(num_clients)
        ]

        print(f"联邦学习系统初始化完成 - {num_clients} 个客户端")

    def distribute_data(self, dataset, distribution_strategy="iid"):
        """
        分布数据到各个客户端

        Args:
            dataset: 完整数据集
            distribution_strategy: 分布策略 ('iid', 'non_iid')

        Returns:
            客户端数据加载器列表
        """
        total_size = len(dataset)

        if distribution_strategy == "iid":
            # IID分布 - 随机均匀分配
            indices = list(range(total_size))
            random.shuffle(indices)

            client_sizes = [total_size // self.num_clients] * self.num_clients
            # 处理余数
            for i in range(total_size % self.num_clients):
                client_sizes[i] += 1

            client_datasets = []
            start_idx = 0

            for size in client_sizes:
                end_idx = start_idx + size
                client_indices = indices[start_idx:end_idx]
                client_dataset = Subset(dataset, client_indices)
                client_datasets.append(client_dataset)
                start_idx = end_idx

        else:  # non_iid
            # Non-IID分布 - 按subset分配（每个客户端处理不同的subset）
            # 假设数据集已经按subset组织
            client_datasets = []
            subset_per_client = max(1, len(dataset.available_files) // self.num_clients)

            for i in range(self.num_clients):
                start_file = i * subset_per_client
                end_file = min(
                    (i + 1) * subset_per_client, len(dataset.available_files)
                )

                # 创建该客户端的文件列表
                client_files = dataset.available_files[start_file:end_file]

                # 过滤数据
                client_data = []
                for item in dataset.data:
                    if any(file in item["image"] for file in client_files):
                        client_data.append(item)

                # 创建客户端特定的数据集
                client_dataset = SimpleLUNA16Dataset(
                    data_dir=dataset.data_dir,
                    csv_path=dataset.csv_path,
                    patch_size=dataset.patch_size,
                    max_samples=len(client_data),
                )
                client_dataset.data = client_data
                client_datasets.append(client_dataset)

        # 创建数据加载器
        client_loaders = []
        for i, client_dataset in enumerate(client_datasets):
            loader = DataLoader(
                client_dataset, batch_size=1, shuffle=True, num_workers=0
            )
            client_loaders.append(loader)
            print(f"客户端 {i} 数据量: {len(client_dataset)}")

        return client_loaders

    def federated_training(
        self, train_loaders, test_loader=None, global_rounds=5, local_epochs=3
    ):
        """
        执行联邦学习训练

        Args:
            train_loaders: 客户端训练数据加载器列表
            test_loader: 测试数据加载器
            global_rounds: 全局训练轮数
            local_epochs: 本地训练轮数
        """
        print(f"开始联邦学习训练 - {global_rounds} 轮全局训练")

        for round_num in range(global_rounds):
            print(f"\n=== 全局训练轮次 {round_num + 1}/{global_rounds} ===")

            # 1. 分发全局模型到所有客户端
            global_params = self.server.get_global_model_params()
            for client in self.clients:
                client.load_global_model(global_params)

            # 2. 各客户端执行本地训练
            client_params_list = []
            client_weights = []

            for i, (client, train_loader) in enumerate(
                zip(self.clients, train_loaders)
            ):
                if len(train_loader.dataset) == 0:
                    print(f"客户端 {i} 数据为空，跳过训练")
                    continue

                # 本地训练
                client.local_epochs = local_epochs
                epoch_losses = client.local_train(train_loader, local_epochs)

                # 收集模型参数和权重
                client_params = client.get_model_params()
                client_weight = client.get_data_size(train_loader)

                client_params_list.append(client_params)
                client_weights.append(client_weight)

                print(f"客户端 {i} 本地训练完成，数据量: {client_weight}")

            # 3. 服务器执行模型聚合
            if client_params_list:
                try:
                    self.server.federated_averaging(client_params_list, client_weights)

                    # 记录训练历史
                    client_losses = []
                    for client in self.clients:
                        if client.training_history:
                            recent_losses = client.training_history[-local_epochs:]
                            if recent_losses:
                                client_losses.extend(recent_losses)

                    avg_client_loss = np.mean(client_losses) if client_losses else 0.0

                    self.server.training_history["rounds"].append(round_num + 1)
                    self.server.training_history["avg_loss"].append(avg_client_loss)

                    print(f"第 {round_num + 1} 轮平均客户端损失: {avg_client_loss:.4f}")

                    # 4. 评估全局模型（可选，可能跳过以避免错误）
                    if test_loader is not None:
                        try:
                            global_loss = self.server.evaluate_global_model(test_loader)
                            self.server.training_history["avg_loss"][-1] = global_loss
                        except Exception as e:
                            print(f"全局模型评估失败: {e}")
                            # 继续训练，不中断
                except Exception as e:
                    print(f"模型聚合失败: {e}")
                    break

        print("\n联邦学习训练完成！")
        return self.server.training_history

    def save_federated_model(self, save_path="federated_luna16_model.pth"):
        """保存联邦学习模型"""
        self.server.save_global_model(save_path)

    def plot_training_history(self):
        """绘制训练历史"""
        history = self.server.training_history

        if not history["rounds"]:
            print("没有训练历史可绘制")
            return

        plt.figure(figsize=(12, 4))

        # 损失曲线
        plt.subplot(1, 2, 1)
        plt.plot(history["rounds"], history["avg_loss"], "b-o", label="平均损失")
        plt.xlabel("全局训练轮次")
        plt.ylabel("损失")
        plt.title("联邦学习训练损失")
        plt.legend()
        plt.grid(True)

        # 客户端参与情况
        plt.subplot(1, 2, 2)
        client_participation = [len(self.clients)] * len(history["rounds"])
        plt.bar(
            history["rounds"], client_participation, alpha=0.7, label="参与客户端数"
        )
        plt.xlabel("全局训练轮次")
        plt.ylabel("客户端数量")
        plt.title("客户端参与情况")
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        plt.show()


def train_federated_model(num_clients=3, global_rounds=5, local_epochs=3):
    """
    训练联邦学习模型的主函数

    Args:
        num_clients: 客户端数量
        global_rounds: 全局训练轮数
        local_epochs: 本地训练轮数
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")

    # 数据路径
    data_dir = "./LUNA16"
    csv_path = "./LUNA16/CSVFILES/annotations.csv"

    # 创建数据集
    print("创建训练数据集...")
    train_dataset = SimpleLUNA16Dataset(
        data_dir=data_dir,
        csv_path=csv_path,
        patch_size=(64, 64, 64),
        max_samples=15,  # 限制样本数量用于快速测试
    )

    print("创建测试数据集...")
    test_dataset = SimpleLUNA16Dataset(
        data_dir=data_dir, csv_path=csv_path, patch_size=(64, 64, 64), max_samples=5
    )

    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False, num_workers=0)

    # 创建联邦学习协调器
    coordinator = FederatedLearningCoordinator(
        num_clients=num_clients,
        model_class=Simple3DUNet,
        model_kwargs={"in_channels": 1, "out_channels": 2},
        device=device,
    )

    # 分布数据到客户端
    print("分布数据到客户端...")
    client_loaders = coordinator.distribute_data(
        train_dataset, distribution_strategy="iid"
    )

    # 执行联邦学习训练
    training_history = coordinator.federated_training(
        train_loaders=client_loaders,
        test_loader=test_loader,
        global_rounds=global_rounds,
        local_epochs=local_epochs,
    )

    # 保存模型
    coordinator.save_federated_model("best_federated_lung_nodule_model.pth")

    # 绘制训练历史
    coordinator.plot_training_history()

    print(f"\n联邦学习训练完成！")
    print(f"客户端数量: {num_clients}")
    print(f"全局轮数: {global_rounds}")
    print(f"本地轮数: {local_epochs}")

    return coordinator


if __name__ == "__main__":
    # 运行联邦学习训练
    coordinator = train_federated_model(num_clients=3, global_rounds=3, local_epochs=2)
