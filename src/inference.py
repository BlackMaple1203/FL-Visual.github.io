import os
import numpy as np
import pandas as pd
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from monai.networks.nets import UNet
from monai.networks.layers import Norm
from monai.transforms import (
    Compose,
    AddChanneld,
    Orientationd,
    Spacingd,
    ScaleIntensityRanged,
    CropForegroundd,
    ToTensord,
)
from monai.inferers import sliding_window_inference
import matplotlib.pyplot as plt
from scipy import ndimage
import warnings

warnings.filterwarnings("ignore")


class LungNodulePredictor:
    def __init__(self, model_path, device=None):
        """
        肺结节预测器

        Args:
            model_path: 训练好的模型路径
            device: 计算设备
        """
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model = self.load_model(model_path)
        self.transforms = self.get_inference_transforms()

    def load_model(self, model_path):
        """加载训练好的模型"""
        model = UNet(
            spatial_dims=3,
            in_channels=1,
            out_channels=2,  # 背景 + 结节
            channels=(16, 32, 64, 128, 256),
            strides=(2, 2, 2, 2),
            num_res_units=2,
            norm=Norm.BATCH,
        ).to(self.device)

        if os.path.exists(model_path):
            checkpoint = torch.load(model_path, map_location=self.device)
            model.load_state_dict(checkpoint["model_state_dict"])
            print(f"成功加载模型: {model_path}")
        else:
            print(f"警告: 模型文件不存在 {model_path}，使用随机初始化的模型")

        model.eval()
        return model

    def get_inference_transforms(self):
        """获取推理时的数据变换"""
        return Compose(
            [
                AddChanneld(keys=["image"]),
                Orientationd(keys=["image"], axcodes="RAS"),
                Spacingd(keys=["image"], pixdim=(1.0, 1.0, 1.0), mode="bilinear"),
                ScaleIntensityRanged(
                    keys=["image"],
                    a_min=-1000,
                    a_max=400,
                    b_min=0.0,
                    b_max=1.0,
                    clip=True,
                ),
                CropForegroundd(keys=["image"], source_key="image"),
                ToTensord(keys=["image"]),
            ]
        )

    def predict(self, image_path):
        """
        对单个CT图像进行预测

        Args:
            image_path: CT图像文件路径(.mhd文件)

        Returns:
            nodules: 检测到的结节坐标列表 [(x, y, z, confidence), ...]
            prediction: 预测的概率图
            original_image: 原始图像
            spacing: 图像间距
            origin: 图像原点
        """
        # 加载图像
        image = sitk.ReadImage(image_path)
        image_array = sitk.GetArrayFromImage(image)
        spacing = image.GetSpacing()
        origin = image.GetOrigin()

        # 准备输入数据
        data_dict = {"image": image_array.astype(np.float32)}

        # 应用变换
        data_dict = self.transforms(data_dict)

        # 移动到设备
        input_tensor = data_dict["image"].unsqueeze(0).to(self.device)

        # 进行推理
        with torch.no_grad():
            # 使用滑动窗口推理处理大图像
            prediction = sliding_window_inference(
                inputs=input_tensor,
                roi_size=(96, 96, 96),
                sw_batch_size=1,
                predictor=self.model,
                overlap=0.5,
            )

            # 获取结节的概率
            prediction = F.softmax(prediction, dim=1)
            nodule_prob = prediction[0, 1].cpu().numpy()  # 取结节类别的概率

        # 检测结节
        nodules = self.detect_nodules(nodule_prob, spacing, origin, threshold=0.5)

        return nodules, nodule_prob, image_array, spacing, origin

    def detect_nodules(self, probability_map, spacing, origin, threshold=0.5):
        """
        从概率图中检测结节

        Args:
            probability_map: 结节概率图
            spacing: 图像间距
            origin: 图像原点
            threshold: 概率阈值

        Returns:
            nodules: 检测到的结节列表 [(x, y, z, confidence), ...]
        """
        # 二值化
        binary_mask = probability_map > threshold

        # 连通分量分析
        labeled_mask, num_features = ndimage.label(binary_mask)

        nodules = []
        for i in range(1, num_features + 1):
            # 获取连通分量
            component = labeled_mask == i

            # 计算连通分量的大小（过滤太小的区域）
            component_size = np.sum(component)
            if component_size < 10:  # 最小体素数阈值
                continue

            # 计算质心
            center_of_mass = ndimage.center_of_mass(component)
            z, y, x = center_of_mass

            # 转换为世界坐标
            world_x = x * spacing[0] + origin[0]
            world_y = y * spacing[1] + origin[1]
            world_z = z * spacing[2] + origin[2]

            # 计算该区域的平均置信度
            confidence = np.mean(probability_map[component])

            nodules.append((world_x, world_y, world_z, confidence))

        # 按置信度排序
        nodules.sort(key=lambda x: x[3], reverse=True)

        return nodules


def predict_and_visualize(image_path, model_path="best_lung_nodule_model.pth"):
    """
    预测并可视化结果

    Args:
        image_path: CT图像路径
        model_path: 模型路径
    """
    # 创建预测器
    predictor = LungNodulePredictor(model_path)

    # 进行预测
    print(f"正在预测: {image_path}")
    nodules, probability_map, original_image, spacing, origin = predictor.predict(
        image_path
    )

    print(f"检测到 {len(nodules)} 个可能的结节:")
    for i, (x, y, z, conf) in enumerate(nodules):
        print(f"  结节 {i+1}: 位置=({x:.1f}, {y:.1f}, {z:.1f}), 置信度={conf:.3f}")

    # 可视化结果
    visualize_results(original_image, probability_map, nodules, spacing, origin)

    return nodules


def visualize_results(
    original_image, probability_map, nodules, spacing, origin, max_slices=5
):
    """
    可视化预测结果

    Args:
        original_image: 原始图像 (Z, Y, X)
        probability_map: 概率图 (Z, Y, X)
        nodules: 检测到的结节列表
        spacing: 图像间距
        origin: 图像原点
        max_slices: 最大显示切片数
    """
    # 转换结节的世界坐标为体素坐标
    nodule_voxels = []
    for x, y, z, conf in nodules:
        voxel_x = int((x - origin[0]) / spacing[0])
        voxel_y = int((y - origin[1]) / spacing[1])
        voxel_z = int((z - origin[2]) / spacing[2])
        nodule_voxels.append((voxel_x, voxel_y, voxel_z, conf))

    # 找到包含结节的切片
    nodule_slices = []
    for _, _, z, _ in nodule_voxels:
        if 0 <= z < original_image.shape[0]:
            nodule_slices.append(z)

    # 如果没有检测到结节，显示中间几个切片
    if not nodule_slices:
        mid_slice = original_image.shape[0] // 2
        nodule_slices = list(
            range(max(0, mid_slice - 2), min(original_image.shape[0], mid_slice + 3))
        )

    # 限制显示的切片数量
    nodule_slices = sorted(set(nodule_slices))[:max_slices]

    fig, axes = plt.subplots(2, len(nodule_slices), figsize=(4 * len(nodule_slices), 8))
    if len(nodule_slices) == 1:
        axes = axes.reshape(2, 1)

    for i, slice_idx in enumerate(nodule_slices):
        # 显示原始图像
        axes[0, i].imshow(original_image[slice_idx], cmap="gray")
        axes[0, i].set_title(f"Original Slice {slice_idx}")
        axes[0, i].axis("off")

        # 在原始图像上标记结节
        for voxel_x, voxel_y, voxel_z, conf in nodule_voxels:
            if voxel_z == slice_idx:
                # 画一个圆圈标记结节
                circle = plt.Circle(
                    (voxel_x, voxel_y), 10, color="red", fill=False, linewidth=2
                )
                axes[0, i].add_patch(circle)
                axes[0, i].text(
                    voxel_x + 15, voxel_y, f"{conf:.2f}", color="red", fontsize=10
                )

        # 显示概率图
        axes[1, i].imshow(original_image[slice_idx], cmap="gray", alpha=0.7)
        probability_overlay = axes[1, i].imshow(
            probability_map[slice_idx], cmap="jet", alpha=0.5, vmin=0, vmax=1
        )
        axes[1, i].set_title(f"Probability Map Slice {slice_idx}")
        axes[1, i].axis("off")

    # 添加颜色条
    plt.colorbar(
        probability_overlay, ax=axes[1, :], shrink=0.6, label="Nodule Probability"
    )

    plt.tight_layout()
    plt.show()


def test_prediction():
    """测试预测功能"""
    # 查找第一个可用的mhd文件进行测试
    data_dir = "./LUNA16"

    # 寻找测试文件
    test_file = None
    for subset in ["subset0", "subset1", "subset2"]:
        subset_path = os.path.join(data_dir, subset)
        if os.path.exists(subset_path):
            mhd_files = [f for f in os.listdir(subset_path) if f.endswith(".mhd")]
            if mhd_files:
                test_file = os.path.join(subset_path, mhd_files[0])
                break

    if test_file:
        print(f"使用测试文件: {test_file}")
        nodules = predict_and_visualize(test_file)
        return nodules
    else:
        print("未找到测试文件")
        return []


if __name__ == "__main__":
    test_prediction()
