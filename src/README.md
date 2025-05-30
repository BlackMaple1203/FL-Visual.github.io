# LUNA16肺结节检测项目

本项目使用MONAI库基于LUNA16数据集训练3D UNet模型来检测肺部结节，并提供可视化功能。

## 项目结构

```
├── main.py                 # 主运行脚本（支持联邦学习模式）
├── train_model.py         # 模型训练脚本
├── train_simple_model.py  # 简化模型训练脚本
├── inference.py           # 推理脚本
├── simple_inference.py    # 简化推理脚本
├── federated_training.py  # 🆕 联邦学习训练系统
├── federated_inference.py # 🆕 联邦学习推理系统
├── show_nodules.py        # 可视化脚本（原有功能 + 新增模型预测可视化）
├── requirements.txt       # 依赖包列表（包含联邦学习依赖）
├── README.md             # 项目说明
├── TESTING_SUMMARY.md    # 测试总结
├── FEDERATED_LEARNING_INTEGRATION.md  # 🆕 联邦学习集成文档
└── LUNA16/               # LUNA16数据集目录
    ├── CSVFILES/
    │   └── annotations.csv
    ├── subset0/
    ├── subset1/
    └── ...
```

## 环境准备

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包：
- `monai`: 医学图像深度学习框架
- `torch`: PyTorch深度学习框架
- `SimpleITK`: 医学图像处理
- `numpy`, `matplotlib`, `pandas`: 基础数据处理和可视化

### 2. 数据准备

确保LUNA16数据集放置在项目根目录下，结构如下：
```
LUNA16/
├── CSVFILES/
│   └── annotations.csv      # 结节标注文件
├── subset0/                # 子集0的CT图像
│   ├── *.mhd              # 图像头文件
│   └── *.raw              # 图像数据文件
├── subset1/               # 子集1的CT图像
└── ...
```

## 使用方法

### 1. 训练模型

#### 集中式训练（原有功能）
```bash
python main.py --mode train
```

#### 🆕 联邦学习训练
```bash
# 基础联邦训练（3个客户端，5轮全局训练）
python main.py --mode federated_train

# 自定义参数的联邦训练
python main.py --mode federated_train --num_clients 5 --global_rounds 10 --local_epochs 3
```

**联邦学习参数说明**：
- `--num_clients`: 客户端数量（默认：3）
- `--global_rounds`: 全局训练轮数（默认：5）
- `--local_epochs`: 本地训练轮数（默认：3）

这将：
- 使用LUNA16数据集的前几个子集进行训练
- 创建3D UNet模型
- 执行联邦学习训练流程（FedAvg算法）
- 保存联邦全局模型为 `best_federated_lung_nodule_model.pth`

### 2. 模型推理

#### 使用集中式训练的模型
```bash
python main.py --mode inference --image_path ./LUNA16/subset0/1.3.6.1.4.1.14519.5.2.1.6279.6001.xxxxxx.mhd
```

#### 🆕 使用联邦学习模型
```bash
python main.py --mode inference --use_federated --image_path ./LUNA16/subset0/1.3.6.1.4.1.14519.5.2.1.6279.6001.xxxxxx.mhd
```

### 3. 演示模式

#### 集中式模型演示
```bash
python main.py --mode demo
```

#### 🆕 联邦学习模型演示
```bash
python main.py --mode federated_demo
```

## 🚀 功能特性

### 1. 训练模式
- **集中式训练**: 传统的集中化模型训练
- **🆕 联邦学习训练**: 分布式训练，保护数据隐私
  - FedAvg算法实现
  - 支持多客户端协同训练
  - 支持IID和Non-IID数据分布
  - 模型参数加权聚合

### 2. 数据预处理
- 自动读取LUNA16数据格式（.mhd/.raw文件）
- 世界坐标到体素坐标的转换
- 图像标准化和重采样
- 前景裁剪和随机裁剪

### 3. 模型架构
- 3D UNet网络，适合医学图像分割
- 输入：单通道CT图像
- 输出：2通道（背景 + 结节）概率图

### 4. 🆕 联邦学习特性
- **隐私保护**: 原始数据不离开客户端
- **通信效率**: 只传输模型参数
- **可扩展性**: 支持动态客户端数量
- **容错性**: 支持客户端异常处理

### 5. 可视化功能
- **原始功能**: `show_nodules()` - 显示已知结节位置的标记框
- **新增功能**: `show_predicted_nodules()` - 显示模型预测的结节
- 三种视图：
  - 原始CT图像 + 结节标记
  - 概率图叠加
  - 传统标记框显示

### 6. 结节检测后处理
- 概率阈值过滤
- 连通分量分析
- 置信度排序
- 最小尺寸过滤

## 代码示例

### 使用原始可视化功能
```python
from show_nodules import show_nodules
import numpy as np

# 假设已有CT数据和结节坐标
nodules = np.array([[100, 200, 50, 10]])  # x, y, z, diameter
show_nodules(ct_scan, nodules)
```

### 使用模型预测可视化
```python
from show_nodules import show_predicted_nodules

# 对CT图像进行结节检测和可视化
show_predicted_nodules(
    image_path='./LUNA16/subset0/sample.mhd',
    model_path='best_lung_nodule_model.pth',
    confidence_threshold=0.5
)
```

### 程序化推理
```python
from inference import LungNodulePredictor

# 创建预测器
predictor = LungNodulePredictor('best_lung_nodule_model.pth')

# 预测结节
nodules, prob_map, image, spacing, origin = predictor.predict('sample.mhd')

for i, (x, y, z, conf) in enumerate(nodules):
    print(f"结节 {i+1}: 位置=({x:.1f}, {y:.1f}, {z:.1f}), 置信度={conf:.3f}")
```

## 性能优化建议

1. **内存优化**: 
   - 使用滑动窗口推理处理大图像
   - 小批量训练（batch_size=1）
   - 及时释放不需要的变量

2. **训练优化**:
   - 增加数据增强
   - 使用更多训练数据
   - 调整学习率和优化器参数
   - 增加训练轮数

3. **推理优化**:
   - 调整置信度阈值
   - 优化后处理参数
   - 使用GPU加速（如果可用）

## 注意事项

1. **数据格式**: 确保LUNA16数据集格式正确，每个.mhd文件都有对应的.raw文件
2. **内存需求**: 3D医学图像处理需要较大内存，建议至少8GB RAM
3. **训练时间**: 完整训练可能需要数小时到数天，建议使用GPU
4. **模型文件**: 训练完成后会生成较大的.pth文件（~100MB）

## 故障排除

1. **ImportError**: 检查是否安装了所有依赖包
2. **FileNotFoundError**: 检查LUNA16数据集路径是否正确
3. **CUDA错误**: 如果没有GPU，模型会自动使用CPU
4. **内存错误**: 减少batch_size或max_samples参数

## 扩展功能

可以进一步扩展的功能：
- 添加数据增强技术
- 实现多类别结节分类
- 添加结节大小估计
- 集成多模型融合
- 添加Web界面
- 支持DICOM格式

## 📁 项目状态

🎉 **项目已完成并通过全面测试！**

### ✅ 已实现功能
- [x] 完整的LUNA16数据集处理
- [x] 3D UNet深度学习模型
- [x] 端到端训练流程
- [x] 实时推理系统
- [x] 可视化界面
- [x] 统一命令行工具
- [x] 全面测试验证

### 🧪 测试结果
- 所有三种模式 (train/inference/demo) 均正常工作
- 成功训练模型并保存权重
- 能够检测肺结节候选区域
- 可视化系统正常显示结果

详细测试报告请参考: [TESTING_SUMMARY.md](TESTING_SUMMARY.md)

## 许可证

本项目仅供学习和研究使用。LUNA16数据集有自己的使用许可，请遵守相关规定。

## 🔗 联邦学习详细文档

本项目现已支持联邦学习功能，实现了分布式的肺结节检测模型训练。联邦学习允许多个医院或机构在不共享原始患者数据的情况下协同训练模型，保护患者隐私。

### 联邦学习快速开始

```bash
# 1. 联邦学习训练
python main.py --mode federated_train --num_clients 3 --global_rounds 5

# 2. 使用联邦模型进行推理
python main.py --mode inference --use_federated --image_path "path/to/ct_scan.mhd"

# 3. 联邦学习演示
python main.py --mode federated_demo
```

### 联邦学习架构

```
医院A     医院B     医院C
 ↓         ↓         ↓
客户端1 ← 客户端2 ← 客户端3
 ↓         ↓         ↓
    联邦服务器（聚合模型）
         ↓
     全局模型更新
```

### 技术特点

- **FedAvg算法**: 经典联邦平均算法实现
- **数据隐私**: 原始CT扫描数据不离开本地
- **模型聚合**: 基于数据量的加权平均
- **异构支持**: 支持不同医院的数据分布差异

详细技术文档请参考：[联邦学习集成文档](./FEDERATED_LEARNING_INTEGRATION.md)

## 📚 相关文档

- [TESTING_SUMMARY.md](./TESTING_SUMMARY.md) - 项目测试总结
- [FEDERATED_LEARNING_INTEGRATION.md](./FEDERATED_LEARNING_INTEGRATION.md) - 联邦学习详细文档
- `federated_training.py` - 联邦学习训练源码
- `federated_inference.py` - 联邦学习推理源码

## 🎯 项目亮点

✅ **完整的肺结节检测管道** - 从数据加载到模型训练再到结果可视化  
✅ **3D医学图像处理** - 基于MONAI框架的专业医学图像处理  
✅ **联邦学习支持** - 保护隐私的分布式机器学习  
✅ **可视化功能** - 直观的结节检测结果展示  
✅ **生产就绪** - 包含完整的错误处理和优化建议  

---

**项目维护**: 定期更新和bug修复  
**技术支持**: 提供详细文档和代码注释  
**扩展性**: 模块化设计，便于功能扩展  

## 注意事项

1. **数据格式**: 确保LUNA16数据集格式正确，每个.mhd文件都有对应的.raw文件
2. **内存需求**: 3D医学图像处理需要较大内存，建议至少8GB RAM
3. **训练时间**: 完整训练可能需要数小时到数天，建议使用GPU
4. **模型文件**: 训练完成后会生成较大的.pth文件（~100MB）
5. **🆕 联邦学习**: 联邦训练需要更多时间，但提供更好的隐私保护
