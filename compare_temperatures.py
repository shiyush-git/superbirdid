#!/usr/bin/env python3
"""
快速对比 0.4, 0.5, 0.6 三个温度值
"""

import torch
import numpy as np
import cv2
from PIL import Image
import sys

from SuperBirdId import (
    load_image, lazy_load_classifier, lazy_load_bird_info,
    YOLOBirdDetector, YOLO_AVAILABLE
)

def test_three_temps(image_path):
    """对比三个候选温度"""
    TEMPS = [0.4, 0.5, 0.6]

    print(f"\n测试图片: {image_path}")
    print("="*80)

    # 加载
    model = lazy_load_classifier()
    bird_info = lazy_load_bird_info()
    image = load_image(image_path)

    # YOLO
    processed = image
    if YOLO_AVAILABLE:
        detector = YOLOBirdDetector()
        cropped, msg = detector.detect_and_crop_bird(image)
        if cropped:
            processed = cropped
            print(f"YOLO: {msg}\n")

    # 预处理
    resized = processed.resize((256, 256), Image.Resampling.LANCZOS)
    cropped_img = resized.crop((16, 16, 240, 240))
    arr = np.array(cropped_img)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    normalized = (bgr / 255.0 - np.array([0.406, 0.456, 0.485])) / np.array([0.225, 0.224, 0.229])
    tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

    # 推理
    with torch.no_grad():
        output = model(tensor)[0]

    # 对比结果
    print(f"{'温度':<8} {'鸟类名称':<20} {'置信度':<10} {'Top2-Top1差距':<15} {'评价'}")
    print("-"*80)

    for temp in TEMPS:
        probs = torch.nn.functional.softmax(output / temp, dim=0)
        top3_probs, top3_idx = torch.topk(probs, 3)

        top1_conf = top3_probs[0].item() * 100
        top1_name = bird_info[top3_idx[0].item()][0]

        gap = (top3_probs[0] - top3_probs[1]).item() * 100

        # 评价
        if top1_conf > 80:
            rating = "很确定 ✓✓✓"
        elif top1_conf > 50:
            rating = "较确定 ✓✓"
        elif top1_conf > 20:
            rating = "一般 ✓"
        else:
            rating = "不确定 ?"

        print(f"T={temp:<6.1f} {top1_name:<20} {top1_conf:6.2f}%    {gap:6.2f}%          {rating}")

        # 显示Top3
        for i in range(3):
            idx = top3_idx[i].item()
            conf = top3_probs[i].item() * 100
            name = bird_info[idx][0]
            print(f"         {i+1}. {name:<20} {conf:6.2f}%")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python compare_temperatures.py <图片路径>")
        sys.exit(1)

    test_three_temps(sys.argv[1])
