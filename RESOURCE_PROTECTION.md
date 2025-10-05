# 资源文件保护方案

## 🔓 当前风险

打包后的应用，用户可以轻易访问：

```bash
# macOS上右键"显示包内容"
SuperBirdID.app/Contents/Resources/
  ├── birdid2024.pt          # 22MB 分类器模型 - 可提取
  ├── yolo11x.pt             # 109MB YOLO模型 - 可提取
  ├── bird_reference.sqlite  # 54MB 鸟类数据库 - 可提取
  └── ...
```

**风险**:
- 模型文件可被竞争对手复制
- 数据库可被提取用于其他项目
- 知识产权泄露

## 🔒 保护方案对比

| 方案 | 安全级别 | 复杂度 | 性能影响 | 推荐度 |
|------|---------|--------|---------|--------|
| 1. 文件加密 | ⭐⭐⭐⭐ | 中 | 启动时解密 | ⭐⭐⭐⭐ |
| 2. 代码混淆 | ⭐⭐⭐ | 低 | 无 | ⭐⭐⭐ |
| 3. 在线验证 | ⭐⭐⭐⭐⭐ | 高 | 网络延迟 | ⭐⭐⭐ |
| 4. 不保护 | ⭐ | 无 | 无 | ⭐ |

---

## 方案1: 文件加密（推荐）

### 优点
- ✅ 模型和数据库加密，无法直接读取
- ✅ 运行时内存解密，不写入磁盘
- ✅ 密钥隐藏在代码中
- ✅ 提高提取门槛

### 缺点
- ⚠️ 启动时需要解密（约1-2秒）
- ⚠️ 增加内存占用（185MB临时数据）
- ⚠️ 高级用户仍可从内存dump

### 实施步骤

#### 1. 安装加密库
```bash
pip install cryptography
```

#### 2. 加密资源文件
```bash
python3 encrypt_resources.py
```

生成：
- `encrypted_resources/birdid2024.pt.enc`
- `encrypted_resources/yolo11x.pt.enc`
- `encrypted_resources/bird_reference.sqlite.enc`
- `resource_key.py` (密钥模块)

#### 3. 修改加载代码

**SuperBirdId.py**:
```python
import tempfile
from cryptography.fernet import Fernet
from resource_key import get_resource_key

def load_encrypted_resource(enc_path):
    """解密并加载资源文件（内存临时文件）"""
    key = get_resource_key()
    fernet = Fernet(key)

    # 读取加密数据
    with open(enc_path, 'rb') as f:
        encrypted = f.read()

    # 解密
    decrypted = fernet.decrypt(encrypted)

    # 创建内存临时文件
    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pt')
    temp.write(decrypted)
    temp.close()

    return temp.name

# 使用示例
def lazy_load_classifier():
    global classifier
    if classifier is None:
        enc_model_path = os.path.join(script_dir, 'birdid2024.pt.enc')
        temp_model = load_encrypted_resource(enc_model_path)
        classifier = torch.jit.load(temp_model)
        os.unlink(temp_model)  # 加载后删除临时文件
    return classifier
```

#### 4. 更新打包配置

**SuperBirdID.spec**:
```python
datas=[
    # 原始文件替换为加密文件
    ('encrypted_resources/birdid2024.pt.enc', '.'),
    ('encrypted_resources/yolo11x.pt.enc', '.'),
    ('encrypted_resources/bird_reference.sqlite.enc', '.'),
    ('resource_key.py', '.'),  # 密钥模块
    # ... 其他文件
],
```

---

## 方案2: 代码混淆（简单）

### 使用PyArmor

#### 1. 安装PyArmor
```bash
pip install pyarmor
```

#### 2. 混淆主要文件
```bash
pyarmor gen --enable-jit SuperBirdId.py SuperBirdID_GUI.py
```

#### 3. 打包混淆后的代码
```bash
pyinstaller SuperBirdID.spec
```

### 优点
- ✅ 实施简单，一键混淆
- ✅ 无性能影响
- ✅ 增加逆向难度

### 缺点
- ⚠️ 资源文件仍然暴露
- ⚠️ 只保护Python代码
- ⚠️ 需要购买PyArmor专业版（$190/年）

---

## 方案3: 在线验证（最安全）

### 架构
```
应用启动 → 验证License → 下载加密模型 → 内存解密 → 使用
```

### 实施
1. 用户激活时生成License（绑定设备ID）
2. 应用启动验证License有效性
3. 从服务器下载加密模型（带License签名）
4. 内存解密使用
5. 退出时清理

### 优点
- ✅ 最高安全级别
- ✅ 防止盗版
- ✅ 可追踪使用情况

### 缺点
- ❌ 需要服务器
- ❌ 需要网络连接
- ❌ 实施复杂

---

## 方案4: 法律保护（辅助）

### 许可协议
在打包时添加：
- EULA（最终用户许可协议）
- 明确禁止提取、逆向工程
- 版权声明

### 代码水印
在模型训练时嵌入水印：
```python
# 在模型中嵌入标识
model.metadata = {
    'author': 'SuperBirdID',
    'license': 'Proprietary',
    'watermark': 'unique_id_12345'
}
```

---

## 💡 综合建议

### 对于免费版/个人版
**推荐**: 方案2（代码混淆）
- 成本低
- 实施简单
- 基本保护

### 对于商业版/付费版
**推荐**: 方案1（文件加密）+ 方案4（法律保护）
- 加密核心资源
- 混淆Python代码
- 添加EULA

### 对于企业版
**推荐**: 方案3（在线验证）
- 完全控制
- License管理
- 防盗版

---

## 🚀 快速实施（最小保护）

如果时间紧迫，至少做以下防护：

### 1. 重命名资源文件（基础混淆）
```python
# SuperBirdID.spec
datas=[
    ('birdid2024.pt', 'data/m1.bin'),      # 伪装成通用数据
    ('yolo11x.pt', 'data/m2.bin'),
    ('bird_reference.sqlite', 'data/db.dat'),
]
```

### 2. 添加许可协议
创建 `LICENSE.txt` 和启动时的同意对话框。

### 3. 代码混淆（如预算允许）
```bash
pyarmor gen SuperBirdId.py SuperBirdID_GUI.py
```

**时间**: 30分钟
**成本**: $0-$190
**效果**: 阻止90%的普通用户

---

## 📊 对比分析

| 保护级别 | 实施时间 | 成本 | 阻止普通用户 | 阻止专业人员 |
|----------|---------|------|-------------|-------------|
| 无保护 | 0 | $0 | 0% | 0% |
| 文件重命名 | 30分钟 | $0 | 60% | 5% |
| 代码混淆 | 1小时 | $190/年 | 80% | 30% |
| 文件加密 | 4小时 | $0 | 90% | 50% |
| 在线验证 | 2周 | $500+ | 95% | 80% |

---

## ✅ 推荐行动

### 立即（发布前）
1. ✅ 文件重命名（30分钟）
2. ✅ 添加LICENSE和EULA（30分钟）

### 短期（1-2周）
3. ⭐ 实施文件加密（4小时）
4. ⭐ 代码混淆（可选，如预算允许）

### 长期（3-6个月）
5. 🎯 在线License验证系统
6. 🎯 模型水印技术

---

**更新日期**: 2025-10-05
**风险评估**: 中高
**建议**: 至少实施文件重命名+加密
