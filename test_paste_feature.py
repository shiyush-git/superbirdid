#!/usr/bin/env python3
"""
测试剪贴板粘贴功能
"""
import tkinter as tk
from SuperBirdID_GUI import SuperBirdIDGUI
from PIL import Image, ImageDraw
import io

def test_paste_feature():
    """测试粘贴功能"""
    print("剪贴板粘贴功能测试")
    print("="*50)

    root = tk.Tk()
    app = SuperBirdIDGUI(root)

    # 测试1: 检查快捷键绑定
    print("\n测试1: 快捷键绑定")
    bindings = root.bind()
    print(f"  已绑定的快捷键: {bindings}")

    ctrl_v_bound = '<Control-v>' in str(root.bind())
    cmd_v_bound = '<Command-v>' in str(root.bind())
    print(f"  Ctrl+V 绑定: {'✓' if ctrl_v_bound else '✗'}")
    print(f"  Cmd+V 绑定: {'✓' if cmd_v_bound else '✗'}")

    # 测试2: 检查方法存在
    print("\n测试2: 方法检查")
    has_paste_method = hasattr(app, 'paste_from_clipboard')
    print(f"  paste_from_clipboard 方法存在: {'✓' if has_paste_method else '✗'}")

    # 测试3: 检查占位符提示文字
    print("\n测试3: 占位符提示")
    root.update()
    print(f"  占位符高度: {app.upload_placeholder.winfo_height()}px")
    print(f"  占位符可见: {'✓' if app.upload_placeholder.winfo_viewable() else '✗'}")

    # 测试4: 模拟创建剪贴板图片（仅测试流程）
    print("\n测试4: 剪贴板图片流程")
    try:
        # 创建一个测试图片
        test_img = Image.new('RGB', (100, 100), color='red')
        draw = ImageDraw.Draw(test_img)
        draw.text((10, 40), "Test", fill='white')

        # 将图片放入剪贴板（仅在支持的平台）
        try:
            from PIL import ImageGrab
            # 注意: 实际粘贴需要手动操作，这里只是测试导入
            print(f"  PIL.ImageGrab 可用: ✓")
        except ImportError:
            print(f"  PIL.ImageGrab 可用: ✗ (某些平台不支持)")

    except Exception as e:
        print(f"  流程测试失败: {e}")

    # 测试5: UI提示文字
    print("\n测试5: UI提示检查")
    # 遍历占位符子组件查找文字
    def find_labels(widget, depth=0):
        labels = []
        if isinstance(widget, tk.Label):
            text = widget.cget('text')
            if text:
                labels.append(text)
        for child in widget.winfo_children():
            labels.extend(find_labels(child, depth+1))
        return labels

    all_labels = find_labels(app.upload_placeholder)
    print(f"  发现的提示文字:")
    for label in all_labels:
        print(f"    - {label}")

    has_paste_hint = any('Ctrl+V' in label or '粘贴' in label for label in all_labels)
    print(f"  包含粘贴提示: {'✓' if has_paste_hint else '✗'}")

    print("\n" + "="*50)
    print("测试完成!")
    print("\n使用说明:")
    print("1. 复制任意图片 (右键图片 -> 复制)")
    print("2. 在SuperBirdID窗口按 Ctrl+V (Mac用Cmd+V)")
    print("3. 图片将自动加载并可识别")

    root.destroy()

if __name__ == "__main__":
    test_paste_feature()
