#!/usr/bin/env python3
"""
演示eBird国家过滤功能
展示如何使用eBird API获取国家鸟类列表并进行过滤
"""
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ebird_country_filter import eBirdCountryFilter
from english_to_ebird_mapping import EnglishToEbirdMapper

def demo_country_filtering():
    """演示国家过滤功能"""
    
    # 初始化
    api_key = "60nan25sogpo"
    country_filter = eBirdCountryFilter(api_key)
    mapper = EnglishToEbirdMapper()
    
    print("=== eBird国家鸟类过滤演示 ===\n")
    
    # 演示1: 获取澳洲鸟类列表
    print("1. 获取澳洲鸟类物种列表")
    au_species = country_filter.get_country_species_list("australia")
    if au_species:
        print(f"   澳洲鸟类物种数量: {len(au_species)}")
        print(f"   前10个物种代码: {list(au_species)[:10]}")
    print()
    
    # 演示2: 获取中国鸟类列表
    print("2. 获取中国鸟类物种列表")
    cn_species = country_filter.get_country_species_list("china")
    if cn_species:
        print(f"   中国鸟类物种数量: {len(cn_species)}")
        print(f"   前10个物种代码: {list(cn_species)[:10]}")
    print()
    
    # 演示3: 模拟鸟类识别结果过滤
    print("3. 模拟鸟类识别结果过滤")
    
    # 模拟识别结果（包含澳洲和非澳洲鸟类）
    mock_results = [
        {"english_name": "Australian Magpie", "confidence": 85.5, "class_id": 1},
        {"english_name": "House Sparrow", "confidence": 78.2, "class_id": 2},
        {"english_name": "Laughing Kookaburra", "confidence": 72.1, "class_id": 3},
        {"english_name": "American Robin", "confidence": 68.9, "class_id": 4},
        {"english_name": "Galah", "confidence": 65.3, "class_id": 5}
    ]
    
    print("   原始识别结果:")
    for i, result in enumerate(mock_results, 1):
        print(f"   {i}. {result['english_name']}: {result['confidence']:.1f}%")
    
    # 对澳洲进行过滤
    if au_species:
        print("\n   使用澳洲eBird数据过滤后:")
        filtered_results = []
        
        for result in mock_results:
            # 获取eBird代码
            ebird_code = mapper.name_to_ebird_code(result["english_name"])
            
            # 检查是否在澳洲物种列表中
            is_au_species = ebird_code and ebird_code in au_species
            
            # 应用置信度调整
            original_confidence = result["confidence"]
            if is_au_species:
                adjusted_confidence = original_confidence * 1.3  # 澳洲鸟类加30%
                country_status = "✓ 澳洲本土"
            else:
                adjusted_confidence = original_confidence * 0.9  # 非澳洲鸟类减10%
                country_status = "✗ 非本土"
            
            filtered_results.append({
                **result,
                "adjusted_confidence": adjusted_confidence,
                "ebird_code": ebird_code,
                "is_local": is_au_species,
                "country_status": country_status
            })
        
        # 按调整后置信度重新排序
        filtered_results.sort(key=lambda x: x["adjusted_confidence"], reverse=True)
        
        for i, result in enumerate(filtered_results, 1):
            print(f"   {i}. {result['english_name']}: ")
            print(f"      原始: {result['confidence']:.1f}% → 调整: {result['adjusted_confidence']:.1f}%")
            print(f"      eBird代码: {result['ebird_code']}")
            print(f"      状态: {result['country_status']}")
    
    print("\n=== 缓存信息 ===")
    cache_files = []
    cache_dir = country_filter.cache_dir
    if os.path.exists(cache_dir):
        for file in os.listdir(cache_dir):
            if file.endswith('.json'):
                cache_files.append(file)
    
    print(f"缓存目录: {cache_dir}")
    print(f"缓存文件: {len(cache_files)} 个")
    for file in cache_files:
        print(f"  - {file}")
    
    print("\n=== 支持的国家 ===")
    supported_countries = country_filter.get_supported_countries()
    print(f"总共支持 {len(supported_countries)} 个国家")
    print("部分示例:")
    for name, code in list(supported_countries.items())[:10]:
        print(f"  {name}: {code}")
    print("  ... 等更多")

def test_specific_country():
    """测试特定国家的功能"""
    api_key = "60nan25sogpo"
    country_filter = eBirdCountryFilter(api_key)
    
    print("\n=== 特定国家测试 ===")
    
    # 让用户选择国家进行测试
    test_countries = ["australia", "china", "usa", "canada", "brazil"]
    print("可测试的国家:")
    for i, country in enumerate(test_countries, 1):
        print(f"{i}. {country}")
    
    try:
        choice = input("\n选择要测试的国家 (输入数字): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(test_countries):
            selected_country = test_countries[int(choice) - 1]
            print(f"\n正在测试 {selected_country}...")
            
            species_set = country_filter.get_country_species_list(selected_country)
            if species_set:
                print(f"成功获取 {selected_country} 的 {len(species_set)} 个鸟类物种")
                print("前20个物种代码:")
                for i, species_code in enumerate(list(species_set)[:20], 1):
                    print(f"  {i:2d}. {species_code}")
            else:
                print(f"获取 {selected_country} 的鸟类物种失败")
        else:
            print("无效选择")
    except KeyboardInterrupt:
        print("\n测试被中断")

if __name__ == "__main__":
    try:
        demo_country_filtering()
        test_specific_country()
    except KeyboardInterrupt:
        print("\n\n演示被中断")
    except Exception as e:
        print(f"\n演示过程中出错: {e}")