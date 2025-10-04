#!/usr/bin/env python3
"""
测试优化后的识别系统
"""
import os
import sys
from PIL import Image

# 添加当前目录到路径
sys.path.append('.')

def test_optimized_recognition():
    """测试优化后的识别系统"""
    # 模拟用户输入
    image_path = "/Users/jameszhenyu/Desktop/test/-250908-8256 x 5504-F.jpg"
    
    try:
        # 导入必要模块
        import torch
        from bird_database_manager import BirdDatabaseManager
        from ebird_country_filter import eBirdCountryFilter
        
        print("=== 优化后的鸟类识别测试 ===")
        
        # 加载模型
        classifier = torch.jit.load('birdid2024.pt')
        classifier.eval()
        print("✓ PyTorch模型加载成功")
        
        # 加载数据库
        db_manager = BirdDatabaseManager()
        bird_data = db_manager.get_bird_data_for_model()
        print(f"✓ SQLite数据库加载成功: {len(bird_data)} 条记录")
        
        # 自动为澳洲启用eBird过滤
        user_region = "Australia"
        print(f"✓ 选择地理区域: {user_region}")
        
        country_filter = eBirdCountryFilter("60nan25sogpo")
        ebird_species_set = country_filter.get_country_species_list("australia")
        print(f"✓ 自动启用eBird澳洲物种过滤: {len(ebird_species_set)} 个物种")
        
        # 加载图片
        image = Image.open(image_path).convert("RGB")
        print(f"✓ 图片加载成功: {image.size}")
        
        # 运行识别 (使用优化后的函数)
        from SuperBirdId import run_ultimate_classification
        
        print(f"\n{'='*60}")
        print("开始优化后的鸟类识别...")
        print(f"{'='*60}")
        
        # 模拟endemic_info
        endemic_info = {}
        
        run_ultimate_classification(
            classifier, 
            image, 
            bird_data, 
            endemic_info,
            user_region=user_region,
            country_filter=country_filter,
            ebird_species_set=ebird_species_set
        )
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_optimized_recognition()