import os
import numpy as np
import pandas as pd
import SimpleITK as sitk
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from monai.networks.nets import UNet
from monai.networks.layers import Norm
from monai.losses import DiceLoss
from monai.transforms import (
    Compose,
    LoadImaged,
    Orientationd,
    Spacingd,
    ScaleIntensityRanged,
    CropForegroundd,
    RandCropByPosNegLabeld,
    ToTensord,
    Activations,
    AsDiscrete,
    AddChanneld,
)

# Try different import names for compatibility
try:
    from monai.transforms import AddChanneld
except ImportError:
    try:
        from monai.transforms import AddChannel as AddChanneld
    except ImportError:
        from monai.transforms.utility.dictionary import AddChanneld
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings("ignore")


class LUNA16Dataset(Dataset):
    def __init__(
        self, data_dir, csv_path, transforms=None, subset_folders=None, max_samples=None
    ):
        """
        LUNA16数据集加载器

        Args:
            data_dir: LUNA16数据目录
            csv_path: annotations.csv文件路径
            transforms: 数据变换
            subset_folders: 使用的子集文件夹列表，如['subset0', 'subset1']
            max_samples: 最大样本数量，用于快速测试
        """
        self.data_dir = data_dir
        self.transforms = transforms

        # 读取标注文件
        self.annotations = pd.read_csv(csv_path)
        print(f"总共有 {len(self.annotations)} 个标注")

        # 获取所有可用的mhd文件
        self.image_files = []

        if subset_folders is None:
            subset_folders = [f"subset{i}" for i in range(10)]

        for subset in subset_folders:
            subset_path = os.path.join(data_dir, subset)
            if os.path.exists(subset_path):
                mhd_files = [f for f in os.listdir(subset_path) if f.endswith(".mhd")]
                for mhd_file in mhd_files:
                    series_uid = mhd_file.replace(".mhd", "")
                    # 检查是否有对应的标注
                    if series_uid in self.annotations["seriesuid"].values:
                        self.image_files.append(
                            {
                                "series_uid": series_uid,
                                "image_path": os.path.join(subset_path, mhd_file),
                                "subset": subset,
                            }
                        )

        print(f"找到 {len(self.image_files)} 个有标注的图像文件")

        # 限制样本数量用于快速测试
        if max_samples and max_samples < len(self.image_files):
            self.image_files = self.image_files[:max_samples]
            print(f"限制到 {max_samples} 个样本用于测试")

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        item = self.image_files[idx]
        series_uid = item["series_uid"]
        image_path = item["image_path"]

        # 加载图像
        image = sitk.ReadImage(image_path)
        image_array = sitk.GetArrayFromImage(image)

        # 获取图像的spacing和origin信息
        spacing = image.GetSpacing()  # (x, y, z)
        origin = image.GetOrigin()  # (x, y, z)

        # 获取该图像的所有标注
        nodule_annotations = self.annotations[
            self.annotations["seriesuid"] == series_uid
        ]

        # 创建标签mask
        label_array = np.zeros_like(image_array, dtype=np.float32)

        for _, annotation in nodule_annotations.iterrows():
            # 世界坐标转换为体素坐标
            world_coord = np.array(
                [annotation["coordX"], annotation["coordY"], annotation["coordZ"]]
            )
            voxel_coord = self.world_to_voxel(world_coord, origin, spacing)

            z, y, x = int(voxel_coord[2]), int(voxel_coord[1]), int(voxel_coord[0])
            diameter_mm = annotation["diameter_mm"]

            # 将直径转换为体素单位
            radius_voxels = [
                int(diameter_mm / (2 * spacing[0])),  # x
                int(diameter_mm / (2 * spacing[1])),  # y
                int(diameter_mm / (2 * spacing[2])),  # z
            ]

            # 在label中标记结节区域
            z_min = max(0, z - radius_voxels[2])
            z_max = min(label_array.shape[0], z + radius_voxels[2] + 1)
            y_min = max(0, y - radius_voxels[1])
            y_max = min(label_array.shape[1], y + radius_voxels[1] + 1)
            x_min = max(0, x - radius_voxels[0])
            x_max = min(label_array.shape[2], x + radius_voxels[0] + 1)

            # 创建球形mask
            for zi in range(z_min, z_max):
                for yi in range(y_min, y_max):
                    for xi in range(x_min, x_max):
                        dist = np.sqrt(
                            ((xi - x) * spacing[0]) ** 2
                            + ((yi - y) * spacing[1]) ** 2
                            + ((zi - z) * spacing[2]) ** 2
                        )
                        if dist <= diameter_mm / 2:
                            label_array[zi, yi, xi] = 1.0

        # 准备数据字典
        data_dict = {
            "image": image_array.astype(np.float32),
            "label": label_array,
            "series_uid": series_uid,
            "spacing": spacing,
            "origin": origin,
        }

        if self.transforms:
            data_dict = self.transforms(data_dict)

        return data_dict

    def world_to_voxel(self, world_coord, origin, spacing):
        """将世界坐标转换为体素坐标"""
        voxel_coord = (np.array(world_coord) - np.array(origin)) / np.array(spacing)
        return voxel_coord


def get_transforms():
    """获取训练和验证的数据变换"""

    train_transforms = Compose(
        [
            AddChanneld(keys=["image", "label"]),
            Orientationd(keys=["image", "label"], axcodes="RAS"),
            Spacingd(
                keys=["image", "label"],
                pixdim=(1.0, 1.0, 1.0),
                mode=("bilinear", "nearest"),
            ),
            ScaleIntensityRanged(
                keys=["image"], a_min=-1000, a_max=400, b_min=0.0, b_max=1.0, clip=True
            ),
            CropForegroundd(keys=["image", "label"], source_key="image"),
            RandCropByPosNegLabeld(
                keys=["image", "label"],
                label_key="label",
                spatial_size=(96, 96, 96),
                pos=1,
                neg=1,
                num_samples=4,
                image_key="image",
                image_threshold=0,
            ),
            ToTensord(keys=["image", "label"]),
        ]
    )

    val_transforms = Compose(
        [
            AddChanneld(keys=["image", "label"]),
            Orientationd(keys=["image", "label"], axcodes="RAS"),
            Spacingd(
                keys=["image", "label"],
                pixdim=(1.0, 1.0, 1.0),
                mode=("bilinear", "nearest"),
            ),
            ScaleIntensityRanged(
                keys=["image"], a_min=-1000, a_max=400, b_min=0.0, b_max=1.0, clip=True
            ),
            CropForegroundd(keys=["image", "label"], source_key="image"),
            ToTensord(keys=["image", "label"]),
        ]
    )

    return train_transforms, val_transforms


def train_model():
    """训练模型"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")

    # 数据路径
    data_dir = "./LUNA16"
    csv_path = "./LUNA16/CSVFILES/annotations.csv"

    # 获取数据变换
    train_transforms, val_transforms = get_transforms()

    # 创建数据集 - 使用部分数据进行快速训练测试
    print("创建训练数据集...")
    train_dataset = LUNA16Dataset(
        data_dir=data_dir,
        csv_path=csv_path,
        transforms=train_transforms,
        subset_folders=["subset0", "subset1"],  # 只使用前两个子集
        max_samples=20,  # 限制样本数量用于快速测试
    )

    print("创建验证数据集...")
    val_dataset = LUNA16Dataset(
        data_dir=data_dir,
        csv_path=csv_path,
        transforms=val_transforms,
        subset_folders=["subset2"],  # 使用subset2作为验证集
        max_samples=5,  # 验证集更少样本
    )

    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset,
        batch_size=1,  # 由于内存限制，使用小batch size
        shuffle=True,
        num_workers=0,  # 在macOS上建议设置为0避免多进程问题
        pin_memory=True if device.type == "cuda" else False,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=0,
        pin_memory=True if device.type == "cuda" else False,
    )

    print(f"训练样本数: {len(train_dataset)}")
    print(f"验证样本数: {len(val_dataset)}")

    # 创建模型
    model = UNet(
        spatial_dims=3,
        in_channels=1,
        out_channels=2,  # 背景 + 结节
        channels=(16, 32, 64, 128, 256),
        strides=(2, 2, 2, 2),
        num_res_units=2,
        norm=Norm.BATCH,
    ).to(device)

    # 损失函数和优化器
    criterion = DiceLoss(to_onehot_y=True, softmax=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    # 训练循环
    num_epochs = 10  # 少量epoch用于快速测试
    best_val_loss = float("inf")

    print("开始训练...")
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0

        print(f"\nEpoch {epoch+1}/{num_epochs}")

        # 训练阶段
        train_pbar = tqdm(train_loader, desc="Training")
        for batch_idx, batch_data in enumerate(train_pbar):
            try:
                images = batch_data["image"].to(device)
                labels = batch_data["label"].to(device)

                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()
                train_pbar.set_postfix({"loss": f"{loss.item():.4f}"})

            except Exception as e:
                print(f"训练批次 {batch_idx} 出错: {e}")
                continue

        avg_train_loss = train_loss / len(train_loader)

        # 验证阶段
        model.eval()
        val_loss = 0

        with torch.no_grad():
            val_pbar = tqdm(val_loader, desc="Validation")
            for batch_idx, batch_data in enumerate(val_pbar):
                try:
                    images = batch_data["image"].to(device)
                    labels = batch_data["label"].to(device)

                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    val_loss += loss.item()
                    val_pbar.set_postfix({"loss": f"{loss.item():.4f}"})

                except Exception as e:
                    print(f"验证批次 {batch_idx} 出错: {e}")
                    continue

        avg_val_loss = (
            val_loss / len(val_loader) if len(val_loader) > 0 else float("inf")
        )

        print(
            f"Epoch {epoch+1}: Train Loss = {avg_train_loss:.4f}, Val Loss = {avg_val_loss:.4f}"
        )

        # 保存最佳模型
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "best_val_loss": best_val_loss,
                },
                "best_lung_nodule_model.pth",
            )
            print(f"保存最佳模型，验证损失: {best_val_loss:.4f}")

    print("训练完成!")
    return model


if __name__ == "__main__":
    model = train_model()
