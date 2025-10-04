# SuperBirdID - 最终版鸟类识别系统

## 🎯 **核心功能**

这是一个集成了SQLite数据库和eBird API的智能鸟类识别系统，具备：

- ✅ **精准识别**: PyTorch深度学习模型 + YOLO自动检测
- ✅ **SQLite数据库**: 10,965条鸟类记录，95.3% eBird代码覆盖率  
- ✅ **eBird集成**: 50+国家物种过滤，自动缓存30天
- ✅ **智能提升**: 本土鸟类置信度提升，最高限制99%
- ✅ **用户友好**: 简化交互，自动匹配地理区域到国家

## 📁 **文件结构**

### 核心文件
```
SuperBirdID/
├── SuperBirdId.py                    # 主程序 ⭐
├── bird_database_manager.py          # SQLite数据库管理器
├── ebird_country_filter.py           # eBird API集成
├── birdid2024.pt                     # PyTorch识别模型
├── bird_reference.sqlite             # SQLite鸟类数据库
├── birdinfo.json                     # 模型兼容数据
├── endemic.json                      # 特有种数据
└── yolo11x.pt                       # YOLO检测模型
```

### 缓存目录
```
ebird_cache/
├── species_list_AU.json             # 澳洲物种缓存
├── species_list_CN.json             # 中国物种缓存
└── ...                              # 其他国家缓存
```

### 存档目录
```
archive/
├── confidence_fixes/                 # 置信度修复相关文件
├── experimental_versions/            # 实验版本和比较文件
└── onnx_tests/                      # ONNX测试文件
```

## 🚀 **使用方法**

### 基本使用
```bash
python SuperBirdId.py
```

### 交互流程
1. **输入图片路径** - 支持大图自动YOLO检测
2. **选择地理区域** - 1=Australia, 4=Asia, 等
3. **确认国家** - 自动匹配或手动指定
4. **查看结果** - 智能排序，本土物种优先

### 示例输出
```
=== 最佳组合结果 ===
最佳方法: UnsharpMask增强 + 传统方法(256→224) + BGR格式 + 智能置信度调整 + 地理区域筛选(Australia)
最高置信度: 78.06%
识别结果:
  - Class ID: 9590, 原始: 78.06%, 调整后: 99.00%, Name: 艳火尾雀 (Beautiful Firetail) [调整: eBird1.2x] [eBird: ✓]
  - Class ID: 9591, 原始: 2.15%, 调整后: 2.58%, Name: 红耳火尾雀 (Red-eared Firetail) [调整: eBird1.2x] [eBird: ✓]
```

## ⚙️ **技术特性**

### 置信度调整策略
- **地理区域匹配**: +20% (基于鸟名关键词)
- **eBird国家匹配**: +20% (基于权威数据库)
- **最高限制**: 99% (避免超过100%)
- **显示阈值**: 原生置信度≥1%

### 数据库优势
| 特性 | JSON文件 | SQLite数据库 |
|------|---------|--------------|
| 记录数量 | ~11K | **10,965条** |
| eBird覆盖率 | 手工映射 | **95.3%** |
| 查询速度 | 线性 | **索引优化** |
| 多语言 | 基础 | **中简/繁/英/学名** |

### eBird API集成
- **数据来源**: Cornell Lab权威数据
- **支持国家**: 50+ (澳洲963种，中国1,427种)
- **缓存机制**: 自动缓存30天
- **匹配率**: 91.7% (澳洲数据)

## 🔧 **配置选项**

### API密钥
在`ebird_country_filter.py`中修改：
```python
EBIRD_API_KEY = "your_api_key_here"
```

### 置信度参数
在`SuperBirdId.py`中调整：
```python
region_boost = 1.2      # 地理区域提升20%
ebird_boost = 1.2       # eBird匹配提升20%
max_confidence = 99.0   # 最高置信度限制
min_confidence = 1.0    # 显示阈值
```

## 📊 **性能指标**

### 识别准确性
- **模型**: PyTorch JIT优化
- **预处理**: 8种组合自动测试
- **增强**: UnsharpMask最佳效果
- **检测**: YOLO自动裁剪大图

### 系统效率  
- **数据库**: 索引优化查询
- **缓存**: eBird数据本地存储
- **并行**: 多方法同时测试
- **内存**: 智能资源管理

## 🎉 **主要优势**

1. **准确性高**: 权威数据库+智能算法
2. **用户友好**: 简化交互流程
3. **扩展性强**: 支持50+国家
4. **维护简单**: 自动缓存更新
5. **性能优秀**: 数据库索引优化

## 📝 **更新日志**

### v2.0 (最新)
- ✅ 集成SQLite数据库替代JSON
- ✅ eBird API国家物种过滤
- ✅ 智能置信度调整算法
- ✅ 用户交互流程优化
- ✅ 代码清理和存档整理

### v1.x (存档)
- 基础PyTorch识别
- 简单地理区域匹配
- JSON数据文件

---

**系统要求**: Python 3.8+, PyTorch, PIL, OpenCV, SQLite3  
**推荐硬件**: 8GB+ RAM, GPU支持(可选)  
**数据来源**: eBird/Cornell Lab, 遵守使用条款