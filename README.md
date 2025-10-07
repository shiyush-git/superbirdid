# SuperBird ID - 鸟类智能识别系统

## 📁 项目结构

### 🎯 核心文件
- **SuperBirdId.py** - 主要识别系统，集成YOLO检测+地理区域智能筛选
- **SuperBirdId_GeographicComparison.py** - 地理筛选效果对比版本

### 🤖 AI模型文件
- **birdid2024.pt** - PyTorch鸟类分类模型 (22MB)
- **yolo11l.pt** - YOLO11-Large鸟类检测模型 (49MB)
- **birdinfo.json** - 鸟类信息数据库 (1MB)
- **endemic.json** - 特有物种信息

### 🧪 实验与测试文件
- **yolo_bird_detection_test.py** - YOLO鸟类检测功能测试
- **image_preprocessing_comparison.py** - 图像预处理方法对比测试
- **direct_224_comparison.py** - 直接224x224处理对比测试

### 🗺️ 地理数据文件
- **cindex.json** - 中文索引文件 (299KB)
- **eindex.json** - 英文索引文件 (1.3MB)

### 📦 存档目录
- **archive/onnx_tests/** - ONNX模型测试文件（已存档）
- **archive/experimental_versions/** - 实验版本（已存档）
  - SuperBirdId_Enhanced.py - 增强版本
  - SuperBirdId_Ensemble.py - 集成学习版本  
  - SuperBirdId_TTA.py - 测试时增强版本
  - SuperBirdId_FiveCrop.py - 五裁剪版本
  - SuperBirdId_MultiScale.py - 多尺度版本
  - SuperBirdId_Australia.py - 澳大利亚专版

## 🚀 使用方法

### 基本识别
```bash
python3 SuperBirdId.py
```

### 地理筛选对比测试
```bash
python3 SuperBirdId_GeographicComparison.py
```

### YOLO鸟类检测测试
```bash
python3 yolo_bird_detection_test.py
```

### 图像预处理方法对比
```bash
python3 image_preprocessing_comparison.py
python3 direct_224_comparison.py
```

## ✨ 核心功能

### 🔍 YOLO智能检测
- **自动鸟类检测**: 使用YOLO11-Large模型自动检测图像中的鸟类区域
- **智能裁剪**: 自动裁剪出鸟类主体，提高识别精度
- **置信度阈值**: 可调节检测置信度(默认0.25)
- **边界框优化**: 支持边界框扩展和多检测结果处理

### 🎯 智能地理区域筛选
- **Australia**: australian, australasian, new zealand
- **Africa**: african, south african  
- **Europe**: european, eurasian, scandinavian, caucasian
- **Asia**: asian, indian, siberian, himalayan, chinese, ryukyu, oriental
- **North_America**: american, canadian, north american
- **South_America**: brazilian, patagonian, south american, west indian
- **Pacific**: pacific
- **Arctic**: arctic

### 📈 置信度智能调整
- 本区域物种：+50% 置信度提升
- 其他区域物种：-20% 置信度降低
- 未知区域物种：不调整

### 🖼️ 图像预处理技术
- **多种预处理方法**: 支持拉伸、中心裁剪、直接224等多种方式
- **UnsharpMask增强**: 锐化图像细节
- **高对比度+边缘增强**: 突出鸟类特征
- **饱和度调整**: 优化色彩表现
- **BGR色彩空间优化**: 提升识别效果

### 🧪 实验功能
- **多尺度测试**: MultiScale版本支持不同分辨率输入
- **测试时增强**: TTA(Test Time Augmentation)版本
- **集成学习**: Ensemble版本结合多个模型
- **五裁剪技术**: FiveCrop版本提高识别稳定性
- **区域专版**: Australia专门优化版本

## 📊 性能指标
- **识别准确度**: 基于11000+种鸟类数据库
- **YOLO检测速度**: 快速鸟类区域定位
- **分类处理速度**: ~0.16s/张 (PyTorch)
- **支持格式**: JPG, PNG, JPEG等常见图片格式
- **输入尺寸**: 自动适应(YOLO检测→224x224分类)
- **模型大小**: 分类模型22MB + 检测模型49MB

## 🏗️ 技术架构

### 两阶段识别流程
1. **YOLO检测阶段**: 使用YOLO11-Large模型检测图像中的鸟类区域
2. **分类识别阶段**: 将检测到的鸟类区域输入分类模型进行物种识别
3. **地理筛选优化**: 根据地理信息调整识别置信度

### 依赖环境
- Python 3.7+
- PyTorch
- Ultralytics YOLO
- OpenCV
- PIL/Pillow
- NumPy

### 安装依赖
```bash
pip install torch torchvision
pip install ultralytics
pip install opencv-python pillow numpy
```

## 🔄 版本历史
- **v1.0**: 基础鸟类识别功能
- **v2.0**: 增加地理区域智能筛选系统
- **v3.0**: 优化图像预处理和增强功能  
- **v4.0**: 集成YOLO11-Large检测，支持自动鸟类区域检测
- **v4.1**: 添加多种实验版本和预处理对比测试

---
*🤖 Generated with Claude Code*