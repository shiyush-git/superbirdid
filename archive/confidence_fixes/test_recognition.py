#!/usr/bin/env python3
"""
鸟类识别测试脚本
方便测试升级后的识别系统
"""
import os
import sys
from PIL import Image

# 确保能导入本地模块
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

def test_recognition_with_image(image_path, country=None, region=None):
    """
    使用指定图片测试识别功能
    
    Args:
        image_path: 图片路径
        country: 国家名称 (如 'australia', 'china')
        region: 地理区域 (如 'Australia', 'Asia')
    """
    try:
        # 导入必要的模块
        import torch
        from bird_database_manager import BirdDatabaseManager
        from ebird_country_filter import eBirdCountryFilter
        
        # 加载模型
        model_path = os.path.join(script_dir, 'birdid2024.pt')
        classifier = torch.jit.load(model_path)
        classifier.eval()
        print("✓ PyTorch模型加载成功")
        
        # 加载数据库
        db_manager = BirdDatabaseManager()
        print(f"✓ 数据库加载成功: {db_manager.get_statistics()['total_birds']} 条记录")
        
        # 设置eBird过滤器
        country_filter = None
        ebird_species_set = None
        
        if country:
            api_key = "60nan25sogpo"
            country_filter = eBirdCountryFilter(api_key)
            ebird_species_set = country_filter.get_country_species_list(country)
            if ebird_species_set:
                print(f"✓ 获取 {country} 的 {len(ebird_species_set)} 个物种数据")
            else:
                print(f"✗ 获取 {country} 物种数据失败")
        
        # 加载和处理图片
        original_image = Image.open(image_path).convert("RGB")
        print(f"✓ 图片加载成功: {original_image.size}")
        
        # 导入识别函数
        from SuperBirdId import run_ultimate_classification
        
        # 模拟endemic_info（如果需要的话）
        endemic_info = {}
        
        print(f"\n{'='*50}")
        print("开始鸟类识别...")
        print(f"{'='*50}")
        
        # 运行识别
        bird_data = db_manager.get_bird_data_for_model()
        run_ultimate_classification(
            classifier, 
            original_image, 
            bird_data, 
            endemic_info,
            user_region=region,
            country_filter=country_filter,
            ebird_species_set=ebird_species_set
        )
        
    except Exception as e:
        print(f"识别测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数 - 提供交互式测试"""
    print("🐦 鸟类识别测试工具")
    print("=" * 40)
    
    # 检查是否有示例图片
    sample_images = []
    for ext in ['jpg', 'jpeg', 'png', 'bmp']:
        sample_images.extend([f for f in os.listdir('.') if f.lower().endswith(ext)])
    
    if sample_images:
        print(f"发现 {len(sample_images)} 个图片文件:")
        for i, img in enumerate(sample_images[:10], 1):  # 最多显示10个
            print(f"  {i}. {img}")
    
    print("\n请选择测试方式:")
    print("1. 输入图片路径")
    if sample_images:
        print("2. 使用当前目录的图片")
    print("3. 退出")
    
    try:
        choice = input("\n选择 (1-3): ").strip()
        
        if choice == "1":
            image_path = input("请输入图片完整路径: ").strip().strip("'\"")
        elif choice == "2" and sample_images:
            print("\n可用图片:")
            for i, img in enumerate(sample_images, 1):
                print(f"  {i}. {img}")
            img_choice = input(f"选择图片 (1-{len(sample_images)}): ").strip()
            if img_choice.isdigit() and 1 <= int(img_choice) <= len(sample_images):
                image_path = sample_images[int(img_choice) - 1]
            else:
                print("无效选择")
                return
        elif choice == "3":
            print("退出测试")
            return
        else:
            print("无效选择")
            return
        
        # 检查图片文件
        if not os.path.exists(image_path):
            print(f"图片文件不存在: {image_path}")
            return
        
        # 询问是否启用国家过滤
        use_country = input("\n启用国家物种过滤? (y/n): ").strip().lower()
        country = None
        if use_country in ['y', 'yes', '是']:
            country = input("输入国家名称 (如 australia, china, usa): ").strip()
        
        # 询问地理区域
        region = input("输入地理区域 (可选，如 Australia, Asia): ").strip()
        if not region:
            region = None
        
        print(f"\n开始测试图片: {image_path}")
        if country:
            print(f"国家过滤: {country}")
        if region:
            print(f"地理区域: {region}")
        
        # 执行识别测试
        test_recognition_with_image(image_path, country, region)
        
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"测试过程中出错: {e}")

if __name__ == "__main__":
    main()