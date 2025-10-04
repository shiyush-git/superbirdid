#!/usr/bin/env python3
"""
测试严格的eBird过滤效果
只显示在国家物种列表中的鸟类
"""
import os
import sys
from PIL import Image
import json

sys.path.append('.')

def test_strict_ebird_filter():
    """测试严格eBird过滤"""
    # 使用之前的测试图片
    image_path = "/Users/jameszhenyu/Desktop/test/-250908-8256 x 5504-F.jpg"  # 使用那张大图
    
    try:
        import torch
        from bird_database_manager import BirdDatabaseManager
        from ebird_country_filter import eBirdCountryFilter
        
        print("=== 测试严格eBird过滤 ===")
        
        # 加载组件
        classifier = torch.jit.load('birdid2024.pt')
        classifier.eval()
        db_manager = BirdDatabaseManager()
        
        # 加载澳洲物种列表
        country_filter = eBirdCountryFilter("60nan25sogpo")
        au_species = country_filter.get_country_species_list("australia")
        print(f"✓ 澳洲eBird物种列表: {len(au_species)} 个物种")
        
        # 加载JSON鸟类数据
        with open('birdinfo.json', 'r') as f:
            bird_data = json.load(f)
        
        # 加载和处理图片
        image = Image.open(image_path).convert("RGB")
        
        # 推理
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
        
        # 获取Top 20结果进行测试
        top_probs, top_indices = torch.topk(probabilities, 20)
        
        print(f"\n📊 严格过滤前后对比:")
        print("=" * 60)
        
        all_candidates = []
        filtered_candidates = []
        
        for i, (prob, idx) in enumerate(zip(top_probs, top_indices), 1):
            class_id = idx.item()
            confidence = prob.item() * 100
            
            if confidence < 1.0:  # 原生阈值
                continue
                
            if class_id < len(bird_data):
                chinese_name = bird_data[class_id][0]
                english_name = bird_data[class_id][1]
                
                # 获取eBird代码
                ebird_code = db_manager.get_ebird_code_by_english_name(english_name)
                is_au_species = ebird_code in au_species if ebird_code and au_species else False
                
                candidate = {
                    'rank': i,
                    'chinese_name': chinese_name,
                    'english_name': english_name,
                    'confidence': confidence,
                    'ebird_code': ebird_code,
                    'is_au_species': is_au_species
                }
                
                all_candidates.append(candidate)
                
                # 严格过滤：只有澳洲本土鸟类才进入过滤后列表
                if is_au_species:
                    filtered_candidates.append(candidate)
        
        # 显示对比结果
        print("🌍 过滤前 - 所有≥1%置信度的结果:")
        for i, candidate in enumerate(all_candidates[:10], 1):
            status = "✓澳洲" if candidate['is_au_species'] else "✗非澳洲"
            print(f"{i:2d}. {candidate['chinese_name']} ({candidate['english_name']})")
            print(f"    置信度: {candidate['confidence']:.2f}%, eBird: {candidate['ebird_code'] or 'N/A'}, 状态: {status}")
        
        print(f"\n🎯 严格eBird过滤后 - 仅澳洲本土物种:")
        if filtered_candidates:
            for i, candidate in enumerate(filtered_candidates[:5], 1):
                # 应用置信度提升
                boosted_confidence = min(candidate['confidence'] * 1.2, 99.0)
                print(f"{i}. {candidate['chinese_name']} ({candidate['english_name']})")
                print(f"   原始: {candidate['confidence']:.2f}% → 提升后: {boosted_confidence:.2f}%")
                print(f"   eBird代码: {candidate['ebird_code']} ✓")
        else:
            print("   无匹配结果")
        
        # 统计信息
        print(f"\n📈 过滤效果统计:")
        print(f"原始候选数: {len(all_candidates)} 个")
        print(f"过滤后数量: {len(filtered_candidates)} 个")
        print(f"过滤比例: {(1-len(filtered_candidates)/len(all_candidates))*100:.1f}% 被过滤")
        print(f"澳洲本土比例: {len(filtered_candidates)/len(all_candidates)*100:.1f}%")
        
        print(f"\n✅ 严格eBird过滤的优势:")
        print("- 🎯 结果更精准：只显示本国确实存在的鸟类")
        print("- 🚫 消除噪声：过滤掉不可能的识别结果") 
        print("- 📊 提高可信度：基于权威eBird数据库")
        print("- 🌍 地区相关性：适合当地观鸟需求")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_strict_ebird_filter()