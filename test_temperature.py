#!/usr/bin/env python3
"""
温度参数测试工具
同时测试多个温度值，对比识别效果
"""

import torch
import numpy as np
import cv2
from PIL import Image
from pathlib import Path
import sys

# 导入核心模块
from SuperBirdId import (
    load_image, lazy_load_classifier, lazy_load_bird_info,
    lazy_load_database, extract_gps_from_exif, get_region_from_gps,
    YOLOBirdDetector, YOLO_AVAILABLE
)

# 要测试的温度值
TEMPERATURES = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

def preprocess_image(image):
    """图片预处理"""
    resized = image.resize((256, 256), Image.Resampling.LANCZOS)
    cropped = resized.crop((16, 16, 240, 240))

    arr = np.array(cropped)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    normalized = (bgr / 255.0 - np.array([0.406, 0.456, 0.485])) / np.array([0.225, 0.224, 0.229])
    tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

    return tensor

def predict_with_temperature(output, temperature, bird_info, top_k=10):
    """使用指定温度进行预测"""
    probabilities = torch.nn.functional.softmax(output / temperature, dim=0)
    top_probs, top_indices = torch.topk(probabilities, min(top_k, len(probabilities)))

    results = []
    for i in range(len(top_indices)):
        idx = top_indices[i].item()
        conf = top_probs[i].item() * 100

        if conf < 0.1:  # 极低置信度过滤
            continue

        if idx < len(bird_info) and len(bird_info[idx]) >= 2:
            cn_name = bird_info[idx][0]
            en_name = bird_info[idx][1]
            results.append({
                'cn_name': cn_name,
                'en_name': en_name,
                'confidence': conf
            })

    return results

def analyze_temperature_distribution(output, temperatures):
    """分析不同温度下的置信度分布"""
    print("\n" + "="*100)
    print("温度参数对置信度分布的影响分析")
    print("="*100)

    for temp in temperatures:
        probs = torch.nn.functional.softmax(output / temp, dim=0)
        top_prob = probs.max().item() * 100
        top_5_avg = probs.topk(5)[0].mean().item() * 100
        entropy = -(probs * torch.log(probs + 1e-10)).sum().item()

        print(f"\n温度 T={temp:.1f}:")
        print(f"  最高置信度: {top_prob:6.2f}%")
        print(f"  Top-5平均: {top_5_avg:6.2f}%")
        print(f"  熵值(不确定性): {entropy:6.3f} {'(低-集中)' if entropy < 3 else '(中)' if entropy < 5 else '(高-分散)'}")

def test_single_image(image_path, model, bird_info, temperatures=TEMPERATURES):
    """测试单张图片在不同温度下的表现"""
    print(f"\n{'='*100}")
    print(f"测试图片: {Path(image_path).name}")
    print(f"{'='*100}")

    # 加载和预处理
    image = load_image(image_path)

    # YOLO检测（如果可用）
    processed_image = image
    if YOLO_AVAILABLE:
        detector = YOLOBirdDetector()
        cropped, msg = detector.detect_and_crop_bird(image)
        if cropped:
            processed_image = cropped
            print(f"\n✓ YOLO检测: {msg}")

    # 预处理
    tensor = preprocess_image(processed_image)

    # 推理
    with torch.no_grad():
        output = model(tensor)[0]

    # 分析温度分布
    analyze_temperature_distribution(output, temperatures)

    # 对比不同温度的Top-3结果
    print(f"\n{'='*100}")
    print("不同温度下的Top-3识别结果对比")
    print(f"{'='*100}\n")

    for temp in temperatures:
        results = predict_with_temperature(output, temp, bird_info, top_k=3)

        print(f"温度 T={temp:.1f}:")
        if results:
            for i, r in enumerate(results, 1):
                conf_bar = "█" * int(r['confidence'] / 5)
                print(f"  {i}. {r['cn_name']:<15} ({r['en_name']:<30}) {r['confidence']:6.2f}% {conf_bar}")
        else:
            print("  (无结果)")
        print()

    # 稳定性分析
    print(f"{'='*100}")
    print("Top-1结果稳定性分析")
    print(f"{'='*100}\n")

    top1_species = {}
    for temp in temperatures:
        results = predict_with_temperature(output, temp, bird_info, top_k=1)
        if results:
            species = results[0]['cn_name']
            conf = results[0]['confidence']
            if species not in top1_species:
                top1_species[species] = []
            top1_species[species].append((temp, conf))

    for species, temp_confs in top1_species.items():
        temps = [t for t, c in temp_confs]
        confs = [c for t, c in temp_confs]
        print(f"  {species}:")
        print(f"    出现在温度: {temps}")
        print(f"    置信度范围: {min(confs):.2f}% - {max(confs):.2f}%")
        print(f"    稳定性: {'高 ✓' if len(temp_confs) >= 5 else '中' if len(temp_confs) >= 3 else '低'}")
        print()

def recommend_temperature(image_paths, model, bird_info):
    """基于多张图片推荐最佳温度"""
    print(f"\n{'='*100}")
    print("综合推荐最佳温度参数")
    print(f"{'='*100}\n")

    temp_scores = {temp: [] for temp in TEMPERATURES}

    for image_path in image_paths:
        image = load_image(image_path)
        processed_image = image

        if YOLO_AVAILABLE:
            detector = YOLOBirdDetector()
            cropped, _ = detector.detect_and_crop_bird(image)
            if cropped:
                processed_image = cropped

        tensor = preprocess_image(processed_image)

        with torch.no_grad():
            output = model(tensor)[0]

        # 为每个温度计算得分
        for temp in TEMPERATURES:
            probs = torch.nn.functional.softmax(output / temp, dim=0)
            top1_conf = probs.max().item() * 100
            top3_gap = (probs.topk(3)[0][0] - probs.topk(3)[0][2]).item() * 100
            entropy = -(probs * torch.log(probs + 1e-10)).sum().item()

            # 综合评分：高置信度 + 适中差距 + 低熵值
            score = (top1_conf * 0.5) + (min(top3_gap, 30) * 0.3) + ((10 - entropy) * 2)
            temp_scores[temp].append(score)

    # 计算平均得分
    avg_scores = {temp: np.mean(scores) for temp, scores in temp_scores.items()}

    print("温度    平均得分    评价")
    print("-" * 50)
    for temp in sorted(avg_scores.keys()):
        score = avg_scores[temp]
        rating = "★★★★★" if score > 50 else "★★★★" if score > 45 else "★★★" if score > 40 else "★★"
        print(f"T={temp:.1f}    {score:6.2f}      {rating}")

    best_temp = max(avg_scores.keys(), key=lambda k: avg_scores[k])
    print(f"\n🎯 推荐温度: T={best_temp:.1f} (得分: {avg_scores[best_temp]:.2f})")

    # 给出建议
    print("\n建议:")
    if best_temp <= 0.4:
        print("  • 低温度(≤0.4): 结果非常锐化，适合高质量图片和专业识别")
        print("  • 注意: 可能对模糊图片过于自信")
    elif best_temp <= 0.6:
        print("  • 中低温度(0.5-0.6): 平衡的选择，适合大多数场景")
        print("  • 优点: 置信度明确，结果稳定")
    elif best_temp <= 0.8:
        print("  • 中高温度(0.7-0.8): 结果较平滑，适合不确定场景")
        print("  • 优点: 给出更多可能性，避免过度自信")
    else:
        print("  • 高温度(≥0.9): 结果很平滑，置信度分散")
        print("  • 适用: 图片质量差或需要更多候选结果的场景")

    return best_temp

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python test_temperature.py <图片路径1> [图片路径2] ...")
        print("示例: python test_temperature.py test_images/*.jpg")
        sys.exit(1)

    image_paths = sys.argv[1:]

    print("温度参数测试工具")
    print("="*100)
    print(f"测试图片数量: {len(image_paths)}")
    print(f"测试温度范围: {TEMPERATURES}")
    print("="*100)

    # 加载模型
    print("\n加载模型...")
    model = lazy_load_classifier()
    bird_info = lazy_load_bird_info()
    print("✓ 模型加载完成")

    # 测试每张图片
    for image_path in image_paths:
        try:
            test_single_image(image_path, model, bird_info, TEMPERATURES)
        except Exception as e:
            print(f"\n✗ 处理 {image_path} 时出错: {e}")
            continue

    # 综合推荐
    if len(image_paths) > 1:
        try:
            best_temp = recommend_temperature(image_paths, model, bird_info)

            # 生成配置代码
            print(f"\n{'='*100}")
            print("可直接使用的代码:")
            print(f"{'='*100}")
            print(f"\nTEMPERATURE = {best_temp}  # 推荐温度参数")
            print(f"probabilities = torch.nn.functional.softmax(output / TEMPERATURE, dim=0)")

        except Exception as e:
            print(f"\n✗ 综合分析出错: {e}")

if __name__ == "__main__":
    main()
