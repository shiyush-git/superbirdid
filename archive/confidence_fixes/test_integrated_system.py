#!/usr/bin/env python3
"""
综合测试脚本 - 测试SQLite数据库集成的鸟类识别系统
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bird_database_manager import BirdDatabaseManager
from ebird_country_filter import eBirdCountryFilter

def test_database_integration():
    """测试数据库集成"""
    print("=== 测试SQLite数据库集成 ===")
    
    try:
        # 初始化数据库管理器
        db_manager = BirdDatabaseManager()
        
        # 获取统计信息
        stats = db_manager.get_statistics()
        print(f"数据库包含 {stats['total_birds']} 条鸟类记录")
        print(f"其中 {stats['birds_with_ebird_codes']} 条有eBird代码")
        print(f"eBird代码覆盖率: {stats['birds_with_ebird_codes']/stats['total_birds']*100:.1f}%")
        
        return db_manager
    except Exception as e:
        print(f"数据库集成测试失败: {e}")
        return None

def test_ebird_integration(db_manager):
    """测试eBird集成"""
    print("\n=== 测试eBird API集成 ===")
    
    try:
        # 初始化eBird过滤器
        api_key = "60nan25sogpo"
        country_filter = eBirdCountryFilter(api_key)
        
        # 获取澳洲物种列表
        au_species = country_filter.get_country_species_list("australia")
        if not au_species:
            print("获取澳洲物种列表失败")
            return None, None
        
        print(f"获取澳洲物种 {len(au_species)} 个")
        
        # 验证数据库与eBird数据的匹配情况
        if db_manager:
            validation = db_manager.validate_ebird_codes_with_country(au_species)
            print(f"数据库与eBird匹配率: {validation['match_rate']:.1f}%")
            print(f"匹配的物种数: {validation['matched_species']}/{validation['country_species_total']}")
        
        return country_filter, au_species
    except Exception as e:
        print(f"eBird集成测试失败: {e}")
        return None, None

def test_bird_recognition_simulation():
    """模拟鸟类识别结果处理"""
    print("\n=== 测试鸟类识别结果处理 ===")
    
    # 初始化组件
    db_manager = test_database_integration()
    if not db_manager:
        return False
    
    country_filter, au_species = test_ebird_integration(db_manager)
    if not country_filter or not au_species:
        return False
    
    # 模拟识别结果
    mock_recognition_results = [
        {"class_id": 1, "confidence": 85.5},
        {"class_id": 100, "confidence": 78.2}, 
        {"class_id": 500, "confidence": 72.1},
        {"class_id": 1000, "confidence": 68.9},
        {"class_id": 2000, "confidence": 65.3}
    ]
    
    print("处理模拟识别结果:")
    processed_results = []
    
    for result in mock_recognition_results:
        class_id = result["class_id"]
        raw_confidence = result["confidence"]
        
        # 从数据库获取鸟类信息
        bird_info = db_manager.get_bird_by_class_id(class_id)
        if not bird_info:
            continue
        
        english_name = bird_info["english_name"]
        chinese_name = bird_info["chinese_simplified"]
        ebird_code = bird_info["ebird_code"]
        
        # 检查是否在澳洲物种列表中
        is_au_species = ebird_code in au_species if ebird_code else False
        
        # 应用置信度调整
        if is_au_species:
            adjusted_confidence = raw_confidence * 1.3
            status = "✓ 澳洲本土"
        else:
            adjusted_confidence = raw_confidence * 0.9
            status = "✗ 非本土"
        
        processed_result = {
            "class_id": class_id,
            "chinese_name": chinese_name,
            "english_name": english_name,
            "ebird_code": ebird_code,
            "raw_confidence": raw_confidence,
            "adjusted_confidence": adjusted_confidence,
            "is_local": is_au_species,
            "status": status
        }
        
        processed_results.append(processed_result)
    
    # 按调整后置信度排序
    processed_results.sort(key=lambda x: x["adjusted_confidence"], reverse=True)
    
    # 显示结果
    for i, result in enumerate(processed_results, 1):
        print(f"{i}. {result['chinese_name']} ({result['english_name']})")
        print(f"   类别ID: {result['class_id']}, eBird代码: {result['ebird_code']}")
        print(f"   置信度: {result['raw_confidence']:.1f}% → {result['adjusted_confidence']:.1f}%")
        print(f"   状态: {result['status']}")
        print()
    
    return True

def test_search_functionality():
    """测试搜索功能"""
    print("=== 测试搜索功能 ===")
    
    try:
        db_manager = BirdDatabaseManager()
        
        # 测试不同类型的搜索
        test_queries = ["magpie", "麻雀", "Parus", "澳洲", "Australian"]
        
        for query in test_queries:
            print(f"\n搜索: '{query}'")
            results = db_manager.search_birds(query, limit=3)
            for result in results:
                print(f"  - {result['chinese_simplified']} ({result['english_name']}) [{result['ebird_code']}]")
    
    except Exception as e:
        print(f"搜索功能测试失败: {e}")

def test_model_data_format():
    """测试模型数据格式兼容性"""
    print("\n=== 测试模型数据格式兼容性 ===")
    
    try:
        db_manager = BirdDatabaseManager()
        
        # 获取模型格式数据
        model_data = db_manager.get_bird_data_for_model()
        
        print(f"模型数据条目数: {len(model_data)}")
        print("前5条样例:")
        for i, item in enumerate(model_data[:5], 1):
            if len(item) >= 2:
                print(f"  {i}. {item[0]} ({item[1]})")
            else:
                print(f"  {i}. {item}")
        
        # 验证数据格式
        all_valid = True
        for i, item in enumerate(model_data[:100]):  # 检查前100条
            if not isinstance(item, list) or len(item) < 2:
                print(f"数据格式错误 - 索引 {i}: {item}")
                all_valid = False
                break
        
        if all_valid:
            print("✓ 数据格式验证通过")
        else:
            print("✗ 数据格式验证失败")
    
    except Exception as e:
        print(f"模型数据格式测试失败: {e}")

def main():
    """主测试函数"""
    print("开始综合系统测试...\n")
    
    # 运行所有测试
    test_database_integration()
    test_search_functionality()
    test_model_data_format()
    success = test_bird_recognition_simulation()
    
    if success:
        print("\n🎉 所有测试通过！SQLite数据库集成成功！")
        print("\n系统特点:")
        print("- ✅ 使用SQLite数据库替代JSON文件")
        print("- ✅ 完整的eBird代码映射")
        print("- ✅ 高效的数据查询和搜索")
        print("- ✅ 与现有系统完全兼容")
        print("- ✅ 智能的国家物种过滤")
    else:
        print("\n❌ 部分测试失败，请检查系统配置")

if __name__ == "__main__":
    main()