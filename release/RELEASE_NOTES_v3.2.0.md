# SuperBirdID v3.2.0 Release Notes

**发布日期**: 2025-10-23
**版本**: v3.2.0
**类型**: Feature Release（功能更新）

---

## 🎉 主要改进

### 1. GPS 地理定位大幅优化

**问题**: v3.1.0 中 GPS 地理定位只能返回大洲级别（"欧洲"、"亚洲"），导致不同国家的照片可能使用相同的鸟类列表筛选。

**解决方案**:
- ✅ 集成 **reverse_geocoder** 离线地理数据库
- ✅ GPS 坐标现在能准确转换为实际国家代码
- ✅ 完全离线，速度快（<10ms）
- ✅ 增加缓存机制，避免重复计算

**效果对比**:

| 地点 | v3.1.0 | v3.2.0 |
|------|--------|--------|
| 柏林 | 欧洲 (germany) | DE (德国) ✅ |
| 巴黎 | 欧洲 (germany) ❌ | FR (法国) ✅ |
| 布里斯班 | 澳大利亚 (australia) | AU (澳大利亚) ✅ |
| 北京 | 亚洲 (china) | CN (中国) ✅ |

**影响**:
- Lightroom 插件识别更准确
- 有 GPS 的照片使用正确的国家鸟类列表
- API 三级筛选的优先级3（GPS 推断国家）现在真正可用

---

### 2. 修复 GUI 国家列表显示问题

**问题**: v3.1.0 中有71个国家在下拉菜单中显示为 "None (AF)", "None (AS)" 等。

**原因**: `ebird_regions.json` 中部分国家的 `name_cn` 字段为 `null`，代码未正确处理。

**解决方案**:
```python
# 旧代码
cn_name = country.get('name_cn', name)  # 如果 name_cn 存在但为 None，返回 None

# 新代码
cn_name = country.get('name_cn') or name  # 如果 name_cn 为 None，回退到英文名
```

**效果**:
- ✅ 所有国家都能正常显示
- ✅ 有中文名显示中文，无中文名显示英文
- ✅ 用户体验更好

---

### 3. 修复 Lightroom 插件版本显示

**问题**: v3.1.0 中 Lightroom 插件显示版本为 "v2.0.0 - SuperBirdID本地版"，与主程序版本不一致。

**解决方案**:
```lua
-- 旧代码
local VERSION = "v2.0.0 - SuperBirdID本地版"

-- 新代码
local VERSION = "v3.2.0 - 慧眼识鸟 Lightroom 插件"
```

**效果**:
- ✅ 插件版本与主程序统一为 v3.2.0
- ✅ 识别完成提示显示 "慧眼识鸟 完成 - v3.2.0 - 慧眼识鸟 Lightroom 插件"
- ✅ 品牌名称统一

---

### 4. DMG 安装包改进

**新增**: Lightroom 插件目录快捷方式

在 DMG 中添加了 `Lightroom_Plugins` 快捷方式，直接指向：
```
~/Library/Application Support/Adobe/Lightroom/Modules
```

**优点**:
- ✅ 用户可以直接将插件拖拽到正确目录
- ✅ 无需手动查找隐藏的 Library 文件夹
- ✅ 安装更加便捷

---

## 🔧 技术改进

### 离线地理数据库

新增依赖：
```
reverse-geocoder>=1.5.1
```

特性：
- 完全离线工作
- 基于 GeoNames 数据集
- 覆盖全球所有国家和主要城市
- 精确到城市级别
- 增加包大小约 2MB（数据已压缩）

### GPS 查询缓存

实现了内存缓存机制：
```python
_gps_cache = {}  # 全局缓存
```

- 缓存键：坐标四舍五入到小数点后2位（约1km精度）
- 避免相同位置重复查询
- 加速批量识别

### 降级策略

如果 reverse_geocoder 失败，自动回退到粗粒度判断：
- 保留 v3.1.0 的大洲级别判断作为 fallback
- 确保任何情况下都能返回结果
- 提高系统稳定性

---

## 📊 版本统一

所有组件版本号统一为 **v3.2.0**:

| 组件 | 版本 |
|------|------|
| GUI (SuperBirdID_GUI.py) | 3.2.0 ✅ |
| API (SuperBirdID_API.py) | 3.2.0 ✅ |
| Core (SuperBirdId.py) | 3.2.0 ✅ |
| Lightroom Plugin (Info.lua) | 3.2.0 ✅ |
| App Bundle (Info.plist) | 3.2.0 ✅ |

---

## 🐛 已知问题

### 无重大问题

v3.2.0 经过充分测试，未发现重大 bug。

### 小问题

1. **reverse_geocoder 首次加载**
   - 首次使用时会加载地理数据库（约1秒）
   - 后续查询非常快速（<10ms）
   - 不影响使用体验

2. **旧版本兼容性**
   - GPS 缓存不会持久化，重启应用后清空
   - 不影响功能，只是性能优化

---

## 📦 安装说明

### 新用户

直接安装 v3.2.0 即可，无特殊要求。

### 从 v3.1.0 升级

**无需特殊操作**，直接覆盖安装即可：
1. 下载 `SuperBirdID-v3.2.0.dmg`
2. 打开 DMG
3. 拖拽 `SuperBirdID.app` 到 Applications 文件夹（覆盖旧版）
4. 重新安装 Lightroom 插件

**配置保留**:
- GUI 配置（国家/地区设置）会自动保留
- eBird 离线数据会自动保留
- 无需重新设置

### 从更早版本升级

如果从 v3.0.x 或更早版本升级，建议参考 v3.1.0 的升级指南。

---

## 🔍 测试验证

### GPS 地理定位测试

测试了以下位置，全部通过：

| 城市 | 坐标 | 返回国家代码 | 状态 |
|------|------|-------------|------|
| 柏林 | (52.52, 13.40) | DE | ✅ |
| 巴黎 | (48.86, 2.35) | FR | ✅ |
| 布里斯班 | (-27.47, 153.03) | AU | ✅ |
| 北京 | (39.90, 116.41) | CN | ✅ |
| 悉尼 | (-33.87, 151.21) | AU | ✅ |

### GUI 测试

- ✅ 国家列表不再显示 "None"
- ✅ 所有253个国家/地区都能正常显示
- ✅ 配置保存和加载正常
- ✅ API 启动成功

---

## 📈 性能影响

### 包大小

| 版本 | DMG 大小 | 变化 |
|------|---------|------|
| v3.1.0 | 318 MB | - |
| v3.2.0 | 320 MB | +2 MB |

增加的 2MB 主要是 reverse_geocoder 的地理数据库。

### 识别速度

- GPS 查询: <10ms（首次1秒用于加载数据）
- 对整体识别速度影响可忽略不计
- 缓存机制提高批量识别性能

---

## 🚀 下一步

### v3.2.1 (维护更新)

计划改进：
- 优化 reverse_geocoder 加载速度
- 添加更多中文国家名翻译
- 改进错误处理

### v3.3.0 (功能更新)

潜在新功能：
- 批量识别性能优化
- 更多 eBird 数据源
- 自定义识别参数
- 识别历史记录

---

## 📞 支持信息

**GitHub**: https://github.com/yourusername/SuperBirdID
**Issues**: https://github.com/yourusername/SuperBirdID/issues
**文档**: DMG 中包含完整文档

---

## 📝 完整更新日志

### 新增
- 集成 reverse_geocoder 离线地理数据库
- GPS 查询缓存机制
- 国家代码精确识别
- DMG 中添加 Lightroom_Plugins 目录快捷方式

### 修复
- 修复 GUI 国家列表显示 "None" 的问题
- 修复 GPS 地理定位返回大洲级别而非国家的问题
- 修复 Lightroom 插件版本显示为 v2.0.0 的问题

### 改进
- 优化 get_region_from_gps() 函数
- 增加 fallback 机制提高稳定性
- 统一所有组件版本号到 v3.2.0
- 统一品牌名称为 "慧眼识鸟"

### 变更
- GPS 地理信息格式变化（更详细）
- 国家代码使用 ISO 标准格式（DE, FR, AU, CN, IS）
- Lightroom 插件版本信息显示为 "v3.2.0 - 慧眼识鸟 Lightroom 插件"

---

## 🎊 致谢

感谢所有用户的反馈和建议！

v3.2.0 的主要改进都来自用户报告的实际使用问题。

---

**文件**: `SuperBirdID-v3.2.0.dmg`
**大小**: 318 MB
**SHA256**: `ce2c4e97d8d93242c61462ed05eb4f51270d269143754650dae9b762e8de9272`
**签名**: ✅ 已签名（等待公证）

**发布日期**: 2025-10-23
**下载**: [GitHub Releases](https://github.com/yourusername/SuperBirdID/releases/tag/v3.2.0)
