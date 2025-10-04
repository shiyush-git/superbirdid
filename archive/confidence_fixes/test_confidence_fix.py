#!/usr/bin/env python3
"""
测试置信度限制修复
"""
import os
import sys
from PIL import Image

sys.path.append('.')

def test_confidence_fix():
    """测试修复后的置信度限制"""
    # 模拟之前的高置信度情况
    image_path = "/Users/jameszhenyu/Desktop/test/_Z9W1868.jpg"  # 艳火尾雀图片
    
    try:
        import torch
        from bird_database_manager import BirdDatabaseManager
        from ebird_country_filter import eBirdCountryFilter
        import json
        
        print("=== 测试置信度修复 ===")
        
        # 加载所有组件
        classifier = torch.jit.load('birdid2024.pt')
        classifier.eval()
        
        db_manager = BirdDatabaseManager()
        country_filter = eBirdCountryFilter("60nan25sogpo")
        ebird_species_set = country_filter.get_country_species_list("australia")
        
        with open('birdinfo.json', 'r') as f:
            bird_data = json.load(f)
        
        image = Image.open(image_path).convert("RGB")
        print(f"✓ 测试图片: {image_path}")
        print(f"✓ 图片尺寸: {image.size}")
        
        # 手动推理
        import numpy as np
        import cv2
        
        img_resized = image.resize((224, 224))
        img_array = np.array(img_resized)
        bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        mean = np.array([0.406, 0.456, 0.485])
        std = np.array([0.225, 0.224, 0.229])
        normalized = (bgr_array / 255.0 - mean) / std
        input_tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()
        
        with torch.no_grad():
            output = classifier(input_tensor)
        
        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        top_probs, top_indices = torch.topk(probabilities, 5)
        
        print(f"\n🎯 置信度修复测试结果:")
        print("=" * 50)
        
        for i, (prob, idx) in enumerate(zip(top_probs, top_indices), 1):
            class_id = idx.item()
            raw_confidence = prob.item() * 100
            
            if class_id < len(bird_data):
                chinese_name = bird_data[class_id][0]
                english_name = bird_data[class_id][1]
                
                # 获取eBird代码并检查本土状态
                ebird_code = db_manager.get_ebird_code_by_english_name(english_name)
                is_au_species = ebird_code in ebird_species_set if ebird_code and ebird_species_set else False
                
                # 应用调整后的算法
                region_boost = 1.2 if is_au_species else 1.0  # 假设地理匹配
                ebird_boost = 1.2 if is_au_species else 1.0
                
                adjusted_confidence = raw_confidence * region_boost * ebird_boost
                capped_confidence = min(adjusted_confidence, 99.0)  # 限制最高99%
                
                # 计算实际提升幅度
                boost_percent = (capped_confidence / raw_confidence - 1) * 100 if raw_confidence > 0 else 0
                
                status = "✓ 澳洲本土" if is_au_species else "✗ 非本土"
                
                print(f"{i}. {chinese_name} ({english_name})")
                print(f"   原始置信度: {raw_confidence:.2f}%")
                if adjusted_confidence != raw_confidence:
                    print(f"   提升后: {adjusted_confidence:.2f}%")
                    print(f"   限制后: {capped_confidence:.2f}%")
                    print(f"   实际提升: {boost_percent:+.1f}%")
                else:
                    print(f"   最终置信度: {capped_confidence:.2f}% (无调整)")
                print(f"   eBird代码: {ebird_code or 'N/A'}")
                print(f"   状态: {status}")
                print()
        
        print("🎉 置信度修复测试完成！")
        print("\n✅ 修复要点:")
        print("- 地理区域提升: 50% → 20%")
        print("- eBird匹配提升: 30% → 20%") 
        print("- 最高置信度限制: 99%")
        print("- 合理的总提升幅度: ≤44% (1.2×1.2)")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_confidence_fix()