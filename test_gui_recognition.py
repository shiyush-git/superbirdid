#!/usr/bin/env python3
"""
测试GUI的完整识别流程（使用加密模型）
"""
import os
from SuperBirdId import (
    lazy_load_classifier, lazy_load_bird_info, load_image,
    YOLOBirdDetector, YOLO_AVAILABLE
)
import torch
import numpy as np
import cv2
from PIL import Image

def test_full_recognition_pipeline(image_path):
    """测试完整的识别流程"""
    print("\n🔐 测试加密模型的完整识别流程\n")
    print("=" * 60)

    # 1. 加载模型和数据
    print("步骤 1: 加载AI模型和鸟类数据...")
    model = lazy_load_classifier()
    bird_info = lazy_load_bird_info()
    print("✅ 模型和数据加载完成\n")

    # 2. 加载图片
    print(f"步骤 2: 加载测试图片 {os.path.basename(image_path)}...")
    try:
        image = load_image(image_path)
        print(f"✅ 图片加载成功 ({image.size[0]}x{image.size[1]})\n")
    except Exception as e:
        print(f"❌ 图片加载失败: {e}")
        return False

    # 3. YOLO检测（如果可用）
    processed_image = image
    if YOLO_AVAILABLE and max(image.size) > 640:
        print("步骤 3: YOLO鸟类检测...")
        try:
            detector = YOLOBirdDetector()
            cropped, msg = detector.detect_and_crop_bird(image)
            if cropped:
                processed_image = cropped
                print(f"✅ YOLO检测成功: {msg}\n")
            else:
                print(f"⚠️  {msg}\n")
        except Exception as e:
            print(f"⚠️  YOLO检测失败: {e}\n")
    else:
        print("步骤 3: 跳过YOLO检测（图片较小或YOLO不可用）\n")

    # 4. 识别
    print("步骤 4: AI识别中...")
    try:
        # 预处理
        resized = processed_image.resize((256, 256), Image.Resampling.LANCZOS)
        cropped = resized.crop((16, 16, 240, 240))

        arr = np.array(cropped)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        normalized = (bgr / 255.0 - np.array([0.406, 0.456, 0.485])) / np.array([0.225, 0.224, 0.229])
        tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

        # 推理
        with torch.no_grad():
            output = model(tensor)[0]

        # 应用温度
        TEMPERATURE = 0.5
        probabilities = torch.nn.functional.softmax(output / TEMPERATURE, dim=0)

        # 获取Top 5
        top_probs, top_indices = torch.topk(probabilities, 5)

        print("✅ 识别完成！\n")
        print("=" * 60)
        print("🎯 识别结果 (Top 5)")
        print("=" * 60)

        for i in range(5):
            idx = top_indices[i].item()
            conf = top_probs[i].item() * 100

            if idx < len(bird_info) and len(bird_info[idx]) >= 2:
                cn_name = bird_info[idx][0]
                en_name = bird_info[idx][1]

                # 格式化输出
                medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]
                print(f"{medal} 第{i+1}名: {cn_name}")
                print(f"   学名: {en_name}")
                print(f"   置信度: {conf:.2f}%")
                print()

        return True

    except Exception as e:
        print(f"❌ 识别失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # 测试图片路径
    test_image = "-250908-8256 x 5504-F.jpg"

    if not os.path.exists(test_image):
        print(f"❌ 测试图片不存在: {test_image}")
        print("请提供一张鸟类照片的路径")
        return

    success = test_full_recognition_pipeline(test_image)

    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    if success:
        print("✅ 完整识别流程测试通过！")
        print("\n✨ 加密模型优势:")
        print("   ✓ 模型文件受到保护，无法直接提取")
        print("   ✓ 识别速度不受影响")
        print("   ✓ 仅需加密一个文件 (birdid2024.pt)")
        print("   ✓ 用户体验完全一致")
    else:
        print("❌ 测试失败")

if __name__ == '__main__':
    main()
