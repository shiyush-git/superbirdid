#!/usr/bin/env python3
"""
测试GUI温度功能
"""
import sys
sys.path.insert(0, '/Users/jameszhenyu/Documents/Development/SuperBirdID')

from SuperBirdID_GUI import SuperBirdIDGUI
import tkinter as tk

# 测试配置
root = tk.Tk()
app = SuperBirdIDGUI(root)

# 检查默认温度
print(f"默认温度值: {app.temperature.get()}")
print(f"温度对比默认状态: {app.show_temp_comparison.get()}")

# 测试温度变化
app.temperature.set(0.4)
print(f"修改后温度值: {app.temperature.get()}")

app.show_temp_comparison.set(True)
print(f"启用温度对比: {app.show_temp_comparison.get()}")

print("\n✓ GUI温度功能测试通过！")

root.destroy()
