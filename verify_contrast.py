#!/usr/bin/env python3
"""
验证暗色主题的对比度和文字易读性
"""

def hex_to_rgb(hex_color):
    """转换十六进制颜色到RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def relative_luminance(rgb):
    """计算相对亮度"""
    r, g, b = [x / 255.0 for x in rgb]
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(color1, color2):
    """计算对比度（WCAG标准）"""
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)

    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)

def check_wcag_compliance(ratio, level='AA'):
    """检查是否符合WCAG标准"""
    # WCAG AA: 正常文字 >= 4.5, 大文字 >= 3.0
    # WCAG AAA: 正常文字 >= 7.0, 大文字 >= 4.5
    if level == 'AA':
        normal = ratio >= 4.5
        large = ratio >= 3.0
    else:  # AAA
        normal = ratio >= 7.0
        large = ratio >= 4.5

    return normal, large

if __name__ == "__main__":
    # SuperBirdID 暗色主题配色
    colors = {
        'bg': '#0f1419',           # 主背景
        'card': '#1e2432',         # 卡片背景
        'text': '#f9fafb',         # 主文字
        'text_secondary': '#9ca3af', # 次要文字
        'success': '#10b981',      # 成功色
        'primary': '#60a5fa',      # 主题色 (更新后)
    }

    print("=" * 70)
    print("SuperBirdID 暗色主题 - 对比度验证")
    print("=" * 70)
    print()

    # 关键组合测试
    tests = [
        ("主背景 + 主文字", colors['bg'], colors['text']),
        ("主背景 + 次要文字", colors['bg'], colors['text_secondary']),
        ("卡片背景 + 主文字", colors['card'], colors['text']),
        ("卡片背景 + 次要文字", colors['card'], colors['text_secondary']),
        ("卡片背景 + 成功色", colors['card'], colors['success']),
        ("卡片背景 + 主题色", colors['card'], colors['primary']),
    ]

    print("WCAG 标准说明:")
    print("  AA 级别: 正常文字 >= 4.5:1, 大文字 >= 3.0:1")
    print("  AAA 级别: 正常文字 >= 7.0:1, 大文字 >= 4.5:1")
    print()
    print("-" * 70)

    all_pass_aa = True
    all_pass_aaa = True

    for name, bg, fg in tests:
        ratio = contrast_ratio(bg, fg)
        aa_normal, aa_large = check_wcag_compliance(ratio, 'AA')
        aaa_normal, aaa_large = check_wcag_compliance(ratio, 'AAA')

        print(f"\n{name}")
        print(f"  背景: {bg}")
        print(f"  前景: {fg}")
        print(f"  对比度: {ratio:.2f}:1")

        # AA 级别
        aa_status = "✅" if aa_normal else "⚠️"
        print(f"  WCAG AA (正常): {aa_status} {'通过' if aa_normal else '未通过'}")

        aa_large_status = "✅" if aa_large else "⚠️"
        print(f"  WCAG AA (大字): {aa_large_status} {'通过' if aa_large else '未通过'}")

        # AAA 级别
        aaa_status = "✅" if aaa_normal else "⚠️"
        print(f"  WCAG AAA (正常): {aaa_status} {'通过' if aaa_normal else '未通过'}")

        if not aa_normal:
            all_pass_aa = False
        if not aaa_normal:
            all_pass_aaa = False

    print()
    print("=" * 70)
    print("总结:")
    print(f"  WCAG AA 级别: {'✅ 全部通过' if all_pass_aa else '⚠️ 部分未通过'}")
    print(f"  WCAG AAA 级别: {'✅ 全部通过' if all_pass_aaa else '⚠️ 部分未通过'}")
    print("=" * 70)
    print()

    if all_pass_aa:
        print("✅ 恭喜！所有文字组合都符合 WCAG AA 标准，易读性良好！")
    else:
        print("⚠️ 建议调整部分颜色组合以提高易读性")
