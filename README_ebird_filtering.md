# eBird国家鸟类过滤系统

## 概述

这个系统集成了eBird API，可以获取特定国家的鸟类物种列表，并在鸟类识别过程中优先显示该国家的本土鸟类。这大大提高了识别准确性，特别是对于特定地理区域的鸟类。

## 主要功能

### 1. eBird API集成
- 使用eBird API 2.0获取国家物种列表
- 支持50+个国家的鸟类数据
- 自动缓存数据，避免重复API调用
- 缓存有效期30天

### 2. 智能过滤
- 基于国家物种列表过滤识别结果
- 本国鸟类置信度提升30%
- 非本国鸟类置信度适度降低
- 结合原有的地理区域过滤

### 3. 缓存系统
- 自动创建`ebird_cache`目录
- JSON格式存储物种列表
- 包含缓存时间和物种数量信息
- 支持手动清理缓存

## 文件结构

```
SuperBirdID/
├── SuperBirdId.py                    # 主程序（已更新）
├── ebird_country_filter.py           # eBird API集成和缓存
├── english_to_ebird_mapping.py       # 英文名到eBird代码映射
├── demo_country_filtering.py         # 功能演示脚本
├── README_ebird_filtering.md         # 本说明文件
└── ebird_cache/                      # 缓存目录
    ├── species_list_AU.json          # 澳洲鸟类列表
    ├── species_list_CN.json          # 中国鸟类列表
    └── ...                           # 其他国家的缓存文件
```

## 使用方法

### 1. 基本使用

运行主程序时，系统会询问是否启用eBird国家过滤：

```bash
python SuperBirdId.py
```

选择步骤：
1. 输入图片路径
2. 选择地理区域（可选）
3. 选择是否启用eBird过滤 (y/n)
4. 如果启用，输入国家名称或代码

### 2. 支持的国家输入格式

可以使用以下任意格式：
- 英文全名：`australia`, `china`, `united states`
- 简短形式：`us`, `au`, `cn`
- ISO代码：`US`, `AU`, `CN`

### 3. 演示脚本

运行演示脚本查看功能：

```bash
python demo_country_filtering.py
```

## 示例输出

```
=== 最佳组合结果 ===
最佳方法: 无增强 + 直接调整224x224 + BGR格式 + 智能置信度调整(Australia)
最高置信度: 89.50%
目标区域: Australia  
地理匹配规则: 本区域物种 +50%, 其他区域物种 -20%
eBird过滤: 启用 (AU - 963个物种)
识别结果:
  - Class ID: 123, 原始: 85.5%, 调整后: 111.2%, Name: 澳洲喜鹊 (Australian Magpie) [区域: Australia] [调整: 1.5x] [eBird: ✓]
  - Class ID: 456, 原始: 78.2%, 调整后: 101.7%, Name: 家麻雀 (House Sparrow) [eBird: ✓]
```

## 技术细节

### API端点
- 物种列表：`https://api.ebird.org/v2/product/spplist/{countryCode}`
- 需要API密钥：在请求头中包含`x-ebirdapitoken`

### 缓存机制
- 缓存文件格式：`species_list_{COUNTRY_CODE}.json`
- 包含字段：物种列表、缓存时间、物种数量
- 自动检查缓存有效性

### 置信度调整策略
1. **地理区域匹配**：基于鸟类名称中的地理关键词
   - 本区域：+50%
   - 其他区域：-20%

2. **eBird国家匹配**：基于eBird物种数据库
   - 本国物种：+30%
   - 无调整非本国物种

3. **综合调整**：两种调整策略可以叠加

## 配置选项

### API设置
在`SuperBirdId.py`中修改API密钥：
```python
EBIRD_API_KEY = "your_api_key_here"
```

### 缓存设置
在`eBirdCountryFilter`类中修改：
```python
self.cache_validity_days = 30  # 缓存有效期
```

### 置信度调整
调整置信度提升系数：
```python
ebird_boost = 1.3  # eBird匹配提升30%
region_boost = 1.5  # 地理区域匹配提升50%
```

## 故障排除

### 常见问题

1. **API请求失败**
   - 检查网络连接
   - 验证API密钥是否有效
   - 检查是否超出API限制

2. **国家代码无法识别**
   - 使用标准国家名称或ISO代码
   - 查看支持国家列表：`country_filter.get_supported_countries()`

3. **缓存相关问题**
   - 手动清理缓存：`country_filter.clear_cache()`
   - 检查缓存目录权限

### 调试方法

启用详细输出：
```python
python demo_country_filtering.py  # 查看详细演示
```

检查缓存状态：
```python
from ebird_country_filter import eBirdCountryFilter
filter = eBirdCountryFilter("your_key")
print(filter.get_supported_countries())
```

## 性能优化

1. **缓存优化**：首次获取后，国家数据从缓存加载，响应速度快
2. **API限制**：内置延迟机制，避免超出eBird API限制
3. **内存效率**：使用集合(set)进行快速物种查找

## 扩展性

### 添加新的映射
在`english_to_ebird_mapping.py`中添加：
```python
mapper.add_known_mapping("新鸟类英文名", "ebird_code")
```

### 支持新国家
在`ebird_country_filter.py`的`country_codes`字典中添加：
```python
'country_name': 'ISO_CODE'
```

## 数据来源

- **eBird API 2.0**：由Cornell Lab of Ornithology提供
- **物种数据**：基于全球鸟类观察记录
- **分类系统**：遵循eBird/Clements分类系统

## 许可和限制

- 请遵守eBird API使用条款
- 合理使用API，避免过度请求
- 数据仅用于鸟类识别和研究目的