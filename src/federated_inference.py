"""
联邦学习推理模块
支持使用联邦训练的模型进行肺结节检测
"""

import os
import numpy as np
import torch
import SimpleITK as sitk
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy.ndimage import label, generate_binary_structure
import warnings

from train_simple_model import Simple3DUNet

warnings.filterwarnings("ignore")


class FederatedLungNodulePredictor:
    """联邦学习肺结节预测器"""

    def __init__(self, model_path, device=None):
        """
        初始化联邦学习预测器

        Args:
            model_path: 联邦训练模型路径
            device: 计算设备
        """
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model = self.load_federated_model(model_path)

    def load_federated_model(self, model_path):
        """加载联邦训练的模型"""
        model = Simple3DUNet(in_channels=1, out_channels=2).to(self.device)

        if os.path.exists(model_path):
            print(f"加载联邦学习模型: {model_path}")
            checkpoint = torch.load(model_path, map_location=self.device)

            # 检查是否是联邦学习保存的格式
            if "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"])
                round_num = checkpoint.get("round_num", "Unknown")
                print(f"模型来自联邦学习第 {round_num} 轮")
            else:
                # 兼容普通模型格式
                model.load_state_dict(checkpoint)
                print("加载普通格式模型")
        else:
            print(f"警告: 模型文件不存在 {model_path}，使用随机初始化的模型")

        model.eval()
        return model

    def normalize_image(self, image):
        """图像标准化"""
        image = np.clip(image, -1000, 400)
        image = (image + 1000) / 1400.0  # 归一化到0-1
        return image.astype(np.float32)

    def predict(self, image_path, patch_size=(64, 64, 64), confidence_threshold=0.3):
        """
        对单个CT图像进行预测

        Args:
            image_path: 图像路径
            patch_size: 预测块大小
            confidence_threshold: 置信度阈值

        Returns:
            tuple: (nodules, probability_map, original_image, spacing, origin)
        """
        # 加载图像
        image = sitk.ReadImage(image_path)
        image_array = sitk.GetArrayFromImage(image)
        spacing = image.GetSpacing()
        origin = image.GetOrigin()

        print(f"图像形状: {image_array.shape}")
        print(f"图像间距: {spacing}")

        # 标准化图像
        normalized_image = self.normalize_image(image_array)

        # 预测
        probability_map = self.sliding_window_prediction(normalized_image, patch_size)

        # 检测结节
        nodules = self.detect_nodules(
            probability_map, spacing, origin, threshold=confidence_threshold
        )

        return nodules, probability_map, image_array, spacing, origin

    def sliding_window_prediction(self, image, patch_size=(64, 64, 64), stride=None):
        """
        滑动窗口预测

        Args:
            image: 输入图像
            patch_size: 窗口大小
            stride: 滑动步长

        Returns:
            概率图
        """
        if stride is None:
            stride = [s // 2 for s in patch_size]  # 默认50%重叠

        original_shape = image.shape
        probability_map = np.zeros(original_shape, dtype=np.float32)
        count_map = np.zeros(original_shape, dtype=np.float32)

        # 计算需要的patch数量
        patch_positions = []
        for z in range(0, original_shape[0], stride[0]):
            for y in range(0, original_shape[1], stride[1]):
                for x in range(0, original_shape[2], stride[2]):
                    # 确保patch不超出边界
                    z_end = min(z + patch_size[0], original_shape[0])
                    y_end = min(y + patch_size[1], original_shape[1])
                    x_end = min(x + patch_size[2], original_shape[2])

                    z_start = max(0, z_end - patch_size[0])
                    y_start = max(0, y_end - patch_size[1])
                    x_start = max(0, x_end - patch_size[2])

                    patch_positions.append(
                        (z_start, y_start, x_start, z_end, y_end, x_end)
                    )

        print(f"总共需要预测 {len(patch_positions)} 个patch")

        # 批量预测
        for i, (z1, y1, x1, z2, y2, x2) in enumerate(patch_positions):
            # 提取patch
            patch = image[z1:z2, y1:y2, x1:x2]

            # 如果patch大小不足，进行padding
            if patch.shape != patch_size:
                padded_patch = np.zeros(patch_size, dtype=np.float32)
                padded_patch[: patch.shape[0], : patch.shape[1], : patch.shape[2]] = (
                    patch
                )
                patch = padded_patch

            # 转换为tensor并预测
            input_tensor = (
                torch.from_numpy(patch).unsqueeze(0).unsqueeze(0).to(self.device)
            )

            with torch.no_grad():
                output = self.model(input_tensor)
                prob = torch.sigmoid(output[0, 1]).cpu().numpy()  # 取结节通道的概率

            # 将结果添加到概率图
            actual_patch_shape = (z2 - z1, y2 - y1, x2 - x1)
            prob_resized = prob[
                : actual_patch_shape[0],
                : actual_patch_shape[1],
                : actual_patch_shape[2],
            ]

            probability_map[z1:z2, y1:y2, x1:x2] += prob_resized
            count_map[z1:z2, y1:y2, x1:x2] += 1

            if (i + 1) % max(1, len(patch_positions) // 10) == 0:
                print(f"完成预测: {i + 1}/{len(patch_positions)}")

        # 平均化重叠区域
        probability_map = np.divide(
            probability_map,
            count_map,
            out=np.zeros_like(probability_map),
            where=count_map != 0,
        )

        return probability_map

    def detect_nodules(
        self, probability_map, spacing, origin, threshold=0.3, min_size=8
    ):
        """
        从概率图中检测结节

        Args:
            probability_map: 概率图
            spacing: 图像间距
            origin: 图像原点
            threshold: 概率阈值
            min_size: 最小连通域大小

        Returns:
            结节列表: [(x, y, z, confidence), ...]
        """
        # 二值化
        binary_map = (probability_map > threshold).astype(np.uint8)

        # 连通域分析
        structure = generate_binary_structure(3, 3)  # 3D连通性
        labeled_map, num_features = label(binary_map, structure=structure)

        nodules = []

        for i in range(1, num_features + 1):
            # 获取连通域
            component_mask = labeled_map == i
            component_size = np.sum(component_mask)

            # 过滤太小的连通域
            if component_size < min_size:
                continue

            # 计算质心
            coords = np.where(component_mask)
            centroid_z = np.mean(coords[0])
            centroid_y = np.mean(coords[1])
            centroid_x = np.mean(coords[2])

            # 计算该区域的平均置信度
            confidence = np.mean(probability_map[component_mask])

            # 转换为世界坐标
            world_x = centroid_x * spacing[0] + origin[0]
            world_y = centroid_y * spacing[1] + origin[1]
            world_z = centroid_z * spacing[2] + origin[2]

            nodules.append((world_x, world_y, world_z, confidence))

        # 按置信度排序
        nodules.sort(key=lambda x: x[3], reverse=True)

        return nodules


def predict_with_federated_model(
    image_path, model_path="best_federated_lung_nodule_model.pth"
):
    """
    使用联邦学习模型进行预测的便捷函数

    Args:
        image_path: CT图像路径
        model_path: 联邦学习模型路径

    Returns:
        预测结果
    """
    predictor = FederatedLungNodulePredictor(model_path)
    nodules, prob_map, image, spacing, origin = predictor.predict(image_path)

    print(f"检测到 {len(nodules)} 个结节候选:")
    for i, (x, y, z, conf) in enumerate(nodules):
        print(f"  结节 {i+1}: 世界坐标=({x:.1f}, {y:.1f}, {z:.1f}), 置信度={conf:.3f}")

    return nodules, prob_map, image, spacing, origin


def visualize_federated_results(image_array, probability_map, nodules, max_slices=3):
    """
    可视化联邦学习预测结果

    Args:
        image_array: 原始CT图像
        probability_map: 概率图
        nodules: 检测到的结节列表
        max_slices: 最大显示切片数
    """
    if len(nodules) == 0:
        print("未检测到结节，显示概率最高的切片")
        slice_max_probs = [
            np.max(probability_map[i]) for i in range(probability_map.shape[0])
        ]
        top_slices = np.argsort(slice_max_probs)[-max_slices:][::-1]
    else:
        # 转换结节位置为体素坐标并找到对应切片
        nodule_slices = []
        for x, y, z, conf in nodules[:max_slices]:
            # 这里简化处理，实际应该进行坐标转换
            slice_idx = int(len(image_array) / 2)  # 使用中间切片作为示例
            nodule_slices.append(slice_idx)
        top_slices = nodule_slices

    fig, axes = plt.subplots(2, len(top_slices), figsize=(4 * len(top_slices), 8))
    if len(top_slices) == 1:
        axes = axes.reshape(2, 1)

    for i, slice_idx in enumerate(top_slices):
        # 显示原始图像
        axes[0, i].imshow(image_array[slice_idx], cmap="gray")
        axes[0, i].set_title(f"原始图像 - 切片 {slice_idx}")
        axes[0, i].axis("off")

        # 显示概率图叠加
        axes[1, i].imshow(image_array[slice_idx], cmap="gray", alpha=0.7)
        prob_overlay = axes[1, i].imshow(
            probability_map[slice_idx], cmap="jet", alpha=0.6, vmin=0, vmax=1
        )
        axes[1, i].set_title(f"概率图 - 切片 {slice_idx}")
        axes[1, i].axis("off")

    plt.colorbar(prob_overlay, ax=axes[1, :], shrink=0.6, label="结节概率")
    plt.suptitle("联邦学习模型预测结果", fontsize=16)
    plt.tight_layout()
    plt.show()


def demo_federated_prediction():
    """联邦学习预测演示"""
    # 查找样本文件
    data_dir = "./LUNA16"

    for subset in ["subset0", "subset1", "subset2"]:
        subset_path = os.path.join(data_dir, subset)
        if os.path.exists(subset_path):
            mhd_files = [f for f in os.listdir(subset_path) if f.endswith(".mhd")]
            if mhd_files:
                sample_file = os.path.join(subset_path, mhd_files[0])
                print(f"使用样本文件: {sample_file}")

                # 使用联邦学习模型预测
                nodules, prob_map, image, spacing, origin = (
                    predict_with_federated_model(sample_file)
                )

                # 可视化结果
                visualize_federated_results(image, prob_map, nodules)
                return sample_file

    print("未找到可用的样本数据")
    return None


if __name__ == "__main__":
    demo_federated_prediction()
