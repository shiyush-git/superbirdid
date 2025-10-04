# SuperBirdID 可执行文件使用说明

## 文件位置
```
/Users/jameszhenyu/Documents/Development/SuperBirdID/dist/SuperBirdID
```

## 使用方法

### 1. 直接运行
```bash
cd /Users/jameszhenyu/Documents/Development/SuperBirdID
./dist/SuperBirdID
```

### 2. 程序运行流程
1. 启动后会提示：`请输入图片文件的完整路径:`
2. 输入您要识别的鸟类图片路径
3. 选择地理区域（1-5，直接回车默认澳洲）
4. 等待识别结果

### 3. 示例使用
```bash
./dist/SuperBirdID
# 输入: /path/to/your/bird/image.jpg
# 选择: 2 (或直接回车选择澳洲)
```

## 特性
- ✅ 支持YOLO鸟类检测
- ✅ 支持eBird地理过滤
- ✅ 多种图像增强方法
- ✅ 地理区域智能筛选
- ✅ 完全独立运行，无需Python环境

## 文件大小
约 545MB（包含所有AI模型和数据）

## 故障排除
如果程序启动后无响应，可能是在等待输入。确保：
1. 程序确实在运行（终端会显示提示信息）
2. 输入完整的图片文件路径
3. 图片文件存在且可访问