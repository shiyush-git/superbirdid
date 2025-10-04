#!/usr/bin/env python3
"""
测试GUI新功能是否存在
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("SuperBirdID GUI 功能检查")
print("=" * 60)

# 1. 检查SuperBirdID_GUI.py文件
gui_file = "SuperBirdID_GUI.py"
if not os.path.exists(gui_file):
    print(f"✗ 找不到 {gui_file}")
    sys.exit(1)

with open(gui_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 2. 检查关键功能
features = {
    "eBird过滤复选框": "启用 eBird 地理过滤",
    "国家下拉菜单": "ttk.Combobox",
    "国家列表加载": "load_available_countries",
    "YOLO裁剪图片发送": 'progress_queue.put(("cropped_image"',
    "裁剪图片显示处理": 'msg_type == "cropped_image"',
    "eBird确认标记": "✓ eBird确认",
}

print("\n功能检查结果:")
print("-" * 60)

all_ok = True
for name, keyword in features.items():
    if keyword in content:
        print(f"✓ {name}")
    else:
        print(f"✗ {name} - 未找到")
        all_ok = False

print("-" * 60)

if all_ok:
    print("\n✅ 所有功能代码都已添加到GUI文件中")
    print("\n📋 使用说明:")
    print("1. 启动GUI: python SuperBirdID_GUI.py")
    print("2. 加载一张图片")
    print("3. 点击【⚙️ 高级选项】按钮（重要！）")
    print("4. 你会看到:")
    print("   - ✓ 启用 YOLO 智能鸟类检测")
    print("   - ✓ 启用 GPS 地理位置分析")
    print("   - ✓ 启用 eBird 地理过滤 ← 新增")
    print("   - 选择国家/地区: [下拉菜单] ← 新增")
    print("5. 勾选「启用 eBird 地理过滤」")
    print("6. 从下拉菜单选择国家")
    print("7. 点击「🔍 开始识别」")
    print("\n💡 YOLO裁剪图片会自动替换显示，无需额外操作")
else:
    print("\n✗ 部分功能缺失，请检查代码")

print("\n" + "=" * 60)
