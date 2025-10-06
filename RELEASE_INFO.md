# SuperBirdID v1.0.0 发布信息

## 📦 打包完成

**发布文件:** `SuperBirdID-1.0.0.dmg`  
**文件大小:** 634 MB  
**应用大小:** 1.8 GB (解压后)  
**构建日期:** 2025年10月6日  
**平台:** macOS (Apple Silicon & Intel)

## ✅ DMG 验证结果

- ✓ DMG 完整性验证通过 (CRC32 校验)
- ✓ 挂载/卸载测试通过
- ✓ 应用结构完整
- ✓ Applications 快捷方式正常

## 📋 安装说明

1. 双击打开 `SuperBirdID-1.0.0.dmg`
2. 将 `SuperBirdID.app` 拖到 `Applications` 文件夹
3. 从 Launchpad 或 Applications 文件夹启动应用

## 🎯 核心功能

### 鸟类识别
- ✓ 加密模型保护 (birdid2024.pt.enc)
- ✓ YOLO 鸟类检测 (yolo11x.pt)
- ✓ 支持格式: JPG, PNG, TIFF, RAW
- ✓ 剪贴板粘贴支持

### eBird 地理筛选
- ✓ GPS 三级回退策略
  - 🎯 GPS位置30天数据 (最精确)
  - 📍 区域年度数据 (AU-NT)
  - 🌏 国家离线数据 (AU)
- ✓ 数据来源显示在结果区域
- ✓ 全球模式支持

### 用户界面
- ✓ 暗色主题
- ✓ 响应式布局
- ✓ 全区域可点击上传
- ✓ 鼠标悬停效果
- ✓ 结果卡片展示

### API 服务
- ✓ HTTP API (端口 5156)
- ✓ GUI 控制服务器
- ✓ Lightroom 插件支持

### 数据管理
- ✓ SQLite 数据库 (54 MB)
- ✓ eBird 缓存系统
- ✓ EXIF 元数据写入
- ✓ ExifTool 集成

## 📁 包含文件

### 核心资源
- `birdid2024.pt.enc` - 加密识别模型 (22 MB)
- `yolo11x.pt` - YOLO检测模型 (109 MB)
- `bird_reference.sqlite` - 鸟类数据库 (54 MB)
- `birdinfo.json` - 鸟类信息 (1 MB)
- `labelmap.csv` - 标签映射 (263 KB)
- `scmapping.json` - 中英文映射 (78 KB)
- `exiftool` - EXIF工具 (330 KB)

### 离线数据
- `offline_ebird_data/` - eBird 离线数据
- `Plugins/SuperBirdIDPlugin.lrplugin/` - Lightroom 插件

## 🔧 技术栈

- **框架:** Python 3.12 + Tkinter
- **深度学习:** PyTorch + Ultralytics
- **打包工具:** PyInstaller 6.x
- **依赖项:** PIL, NumPy, Requests, RawPy

## ⚠️ 系统要求

- macOS 11.0 (Big Sur) 或更高版本
- 4 GB 可用磁盘空间
- 8 GB RAM (推荐)

## 🐛 已知问题

- 首次启动可能需要几秒钟加载模型
- 某些 RAW 格式可能需要额外时间处理
- 需要网络连接使用 eBird API 功能

## 📝 更新日志

### v1.0.0 (2025-10-06)

**新功能:**
- ✓ GPS 三级地理筛选策略
- ✓ 数据来源信息显示
- ✓ 全区域可点击上传
- ✓ 模型加密保护

**改进:**
- ✓ 优化 UI/UX 交互
- ✓ 改进错误处理
- ✓ 增强数据缓存
- ✓ 完善文档

**修复:**
- ✓ 修复区域代码识别
- ✓ 修复数据源显示位置
- ✓ 修复警告弹窗问题
- ✓ 修复占位符点击区域

---

**生成时间:** $(date)
**构建平台:** $(uname -s) $(uname -m)
