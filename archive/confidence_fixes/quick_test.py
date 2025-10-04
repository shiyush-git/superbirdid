#!/usr/bin/env python3
"""
快速识别测试
"""
import os
import sys
from PIL import Image
import torch
import json

# 导入我们的模块
from bird_database_manager import BirdDatabaseManager
from ebird_country_filter import eBirdCountryFilter

# 导入识别函数 (需要修复导入)
sys.path.append('.')

def quick_recognition_test(image_path="cropped_bird.jpg", country="australia"):
    """快速识别测试"""
    print("=== 鸟类识别测试 ===")
    
    try:
        # 1. 加载模型
        classifier = torch.jit.load('birdid2024.pt')
        classifier.eval()
        print("✓ 模型加载成功")
        
        # 2. 加载数据库
        db_manager = BirdDatabaseManager()
        bird_data = db_manager.get_bird_data_for_model()
        print(f"✓ 数据库加载成功: {len(bird_data)} 条记录")
        
        # 3. 设置eBird过滤
        country_filter = eBirdCountryFilter("60nan25sogpo")
        ebird_species_set = country_filter.get_country_species_list(country)
        print(f"✓ 获取 {country} 的 {len(ebird_species_set)} 个物种")
        
        # 4. 加载图片
        image = Image.open(image_path).convert("RGB")
        print(f"✓ 图片加载成功: {image.size}")
        
        # 5. 加载JSON格式的鸟类数据 (与模型兼容)
        import json
        with open('birdinfo.json', 'r') as f:
            bird_data = json.load(f)
        print(f"✓ 加载JSON鸟类数据: {len(bird_data)} 条记录")
        
        # 手动实现识别逻辑 (简化版)
        import numpy as np
        import cv2
        
        # 图片预处理
        img_resized = image.resize((224, 224))
        img_array = np.array(img_resized)
        bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 标准化
        mean = np.array([0.406, 0.456, 0.485])
        std = np.array([0.225, 0.224, 0.229])
        normalized = (bgr_array / 255.0 - mean) / std
        input_tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()
        
        # 推理
        with torch.no_grad():
            output = classifier(input_tensor)
        
        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        
        # 获取Top 10结果
        top_probs, top_indices = torch.topk(probabilities, 10)
        
        print(f"\n🔍 识别结果 (使用 {country} 物种过滤):")
        print("=" * 60)
        
        for i, (prob, idx) in enumerate(zip(top_probs, top_indices), 1):
            class_id = idx.item()
            confidence = prob.item() * 100
            
            # 获取鸟类信息 (使用JSON数据)
            if class_id < len(bird_data):
                chinese_name = bird_data[class_id][0]
                english_name = bird_data[class_id][1]
                
                # 获取eBird代码
                ebird_code = db_manager.get_ebird_code_by_english_name(english_name)
                
                # 检查是否在目标国家
                is_local = ebird_code in ebird_species_set if ebird_code and ebird_species_set else False
                
                # 应用置信度调整，并限制最高99%
                if is_local:
                    adjusted_confidence = min(confidence * 1.3, 99.0)  # 限制最高99%
                    status = f"✓ {country.title()}本土"
                else:
                    adjusted_confidence = confidence * 0.9
                    status = "✗ 非本土"
                
                print(f"{i:2d}. {chinese_name} ({english_name})")
                print(f"    类别ID: {class_id}, eBird: {ebird_code or 'N/A'}")
                print(f"    置信度: {confidence:.2f}% → {adjusted_confidence:.2f}%")
                print(f"    状态: {status}")
                print()
        
        print("🎉 识别完成！")
        
    except Exception as e:
        print(f"识别测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 你可以修改这些参数
    IMAGE_PATH = "cropped_bird.jpg"  # 图片路径
    COUNTRY = "australia"             # 测试国家
    
    print(f"测试图片: {IMAGE_PATH}")
    print(f"目标国家: {COUNTRY}")
    print()
    
    quick_recognition_test(IMAGE_PATH, COUNTRY)