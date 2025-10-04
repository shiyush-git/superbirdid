#!/usr/bin/env python3
"""
SuperBirdID - 三模式对比测试
一次性测试快速/平衡/精确三个模式，都启用eBird GPS过滤
"""
import torch
import numpy as np
from PIL import Image
import cv2
import time

# 导入原始模块的所有功能
try:
    from SuperBirdId import *
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    exit(1)

def smart_resize_optimized(image, target_size=224):
    """优化的图像预处理方法"""
    width, height = image.size
    max_dimension = max(width, height)

    if max_dimension < 1000:
        final_image = image.resize((target_size, target_size), Image.LANCZOS)
        method_name = "直接调整(小图像)"
    else:
        # 使用传统256→224方法（测试验证最佳）
        resized_256 = image.resize((256, 256), Image.LANCZOS)
        left = (256 - target_size) // 2
        top = (256 - target_size) // 2
        final_image = resized_256.crop((left, top, left + target_size, top + target_size))
        method_name = "传统256→224(测试优化)"

    return final_image, method_name

def smart_resize_fast(image, target_size=224):
    """快速模式：直接224x224"""
    final_image = image.resize((target_size, target_size), Image.LANCZOS)
    return final_image, "直接224x224(快速模式)"

def smart_resize_adaptive(image, target_size=224):
    """智能自适应模式"""
    width, height = image.size
    aspect_ratio = width / height

    if 0.8 <= aspect_ratio <= 1.2:  # 接近正方形
        final_image = image.resize((target_size, target_size), Image.LANCZOS)
        method_name = "智能-直接调整"
    elif aspect_ratio > 1.2:  # 宽图
        new_width = int(target_size * aspect_ratio)
        resized = image.resize((new_width, target_size), Image.LANCZOS)
        left = (new_width - target_size) // 2
        final_image = resized.crop((left, 0, left + target_size, target_size))
        method_name = "智能-宽图裁剪"
    else:  # 高图
        new_height = int(target_size / aspect_ratio)
        resized = image.resize((target_size, new_height), Image.LANCZOS)
        top = (new_height - target_size) // 2
        final_image = resized.crop((0, top, target_size, top + target_size))
        method_name = "智能-高图裁剪"

    return final_image, method_name

def run_single_mode(image, mode_name, preprocessing_func, confidence_threshold,
                   bird_data, model, ebird_species_set, use_gps_precise, db_manager):
    """运行单个模式的识别"""

    print(f"\n🔍 {mode_name}模式:")
    print(f"   置信度阈值: {confidence_threshold}%")

    # 预处理
    final_image, method_desc = preprocessing_func(image, target_size=224)
    print(f"   预处理方法: {method_desc}")

    # 转换为张量
    img_array = np.array(final_image)
    bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # ImageNet标准化 (BGR格式)
    mean = np.array([0.406, 0.456, 0.485])
    std = np.array([0.225, 0.224, 0.229])

    normalized_array = (bgr_array / 255.0 - mean) / std
    input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()

    # 推理
    start_time = time.time()
    with torch.no_grad():
        output = model(input_tensor)
    inference_time = time.time() - start_time

    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    max_confidence = probabilities.max().item() * 100

    print(f"   推理时间: {inference_time:.3f}秒")
    print(f"   最高置信度: {max_confidence:.2f}%")

    # 提取结果
    results = []
    k = min(len(probabilities), len(bird_data), 1000)
    all_probs, all_catid = torch.topk(probabilities, k)

    candidates = []

    for i in range(all_probs.size(0)):
        class_id = all_catid[i].item()
        raw_confidence = all_probs[i].item() * 100

        if raw_confidence < confidence_threshold:
            continue

        try:
            if class_id < len(bird_data) and len(bird_data[class_id]) >= 2:
                bird_name_cn = bird_data[class_id][0]
                bird_name_en = bird_data[class_id][1]
                name = f"{bird_name_cn} ({bird_name_en})"

                # eBird过滤和置信度调整
                ebird_boost = 1.0
                ebird_match = False
                ebird_info = ""

                if ebird_species_set and db_manager:
                    ebird_code = db_manager.get_ebird_code_by_english_name(bird_name_en)
                    if ebird_code and ebird_code in ebird_species_set:
                        if use_gps_precise:
                            ebird_boost = 1.5  # 50%提升
                            ebird_info = " [GPS精确✓]"
                        else:
                            ebird_boost = 1.2  # 20%提升
                            ebird_info = " [eBird✓]"
                        ebird_match = True

                adjusted_confidence = min(raw_confidence * ebird_boost, 99.0)

                # 获取鸟类区域信息
                bird_region = get_bird_region(bird_name_en)
                region_info = f" [区域: {bird_region}]" if bird_region != 'Unknown' else ""

                candidates.append({
                    'class_id': class_id,
                    'raw_confidence': raw_confidence,
                    'adjusted_confidence': adjusted_confidence,
                    'name': name,
                    'ebird_match': ebird_match,
                    'display_info': region_info + ebird_info
                })
        except (IndexError, TypeError):
            continue

    # 按调整后置信度排序
    candidates.sort(key=lambda x: x['adjusted_confidence'], reverse=True)

    # 显示前5个结果
    print(f"   识别结果:")
    result_count = 0
    for candidate in candidates[:5]:
        results.append({
            'class_id': candidate['class_id'],
            'confidence': candidate['adjusted_confidence'],
            'name': candidate['name'],
            'display_info': candidate['display_info']
        })
        print(f"     {result_count+1}. {candidate['name']} - {candidate['adjusted_confidence']:.2f}%{candidate['display_info']}")
        result_count += 1

    if result_count == 0:
        print(f"     无结果 (所有结果置信度低于{confidence_threshold}%)")
        results = []

    return {
        'mode': mode_name,
        'inference_time': inference_time,
        'max_confidence': max_confidence,
        'method_desc': method_desc,
        'results': results,
        'result_count': result_count
    }

def test_all_modes(image_path):
    """测试所有三个模式"""

    print("🐦 SuperBirdID - 三模式对比测试")
    print("=" * 60)
    print("📊 同时测试: 快速/平衡/精确 + eBird GPS过滤")
    print("=" * 60)

    try:
        # 加载图像
        original_image = load_image(image_path)
        print(f"✓ 图像加载成功，尺寸: {original_image.size}")

        # GPS检测
        print("\n🌍 正在检测GPS位置信息...")
        latitude, longitude, gps_info = extract_gps_from_exif(image_path)

        if latitude is not None and longitude is not None:
            auto_region, auto_country, region_info = get_region_from_gps(latitude, longitude)
            print(f"✓ {region_info}")
        else:
            print(f"⚠ {gps_info}")
            auto_region, auto_country = None, None

        # YOLO检测
        width, height = original_image.size
        max_dimension = max(width, height)

        if max_dimension > 640 and YOLO_AVAILABLE:
            print(f"\n🔍 检测到大尺寸图像({max_dimension}px)，正在进行鸟类检测...")
            detector = YOLOBirdDetector()
            cropped_image, detection_msg = detector.detect_and_crop_bird(image_path)

            if cropped_image is not None:
                original_image = cropped_image
                print(f"✓ YOLO检测成功: {detection_msg}")
            else:
                print(f"⚠ YOLO检测失败: {detection_msg}")

        # eBird GPS过滤 - 自动启用
        ebird_species_set = None
        use_gps_precise = False

        if auto_country and EBIRD_FILTER_AVAILABLE:
            print(f"\n🌍 正在获取{auto_country}地区的eBird数据...")
            try:
                EBIRD_API_KEY = "60nan25sogpo"
                country_filter = eBirdCountryFilter(EBIRD_API_KEY, offline_dir="offline_ebird_data")

                if latitude is not None and longitude is not None:
                    print("使用GPS精确位置查询...")
                    ebird_species_set = country_filter.get_location_species_list(latitude, longitude, 25)
                    use_gps_precise = True
                else:
                    ebird_species_set = country_filter.get_country_species_list(auto_country)

                if ebird_species_set:
                    filter_type = "GPS精确" if use_gps_precise else "国家级"
                    print(f"✓ 成功获取 {len(ebird_species_set)} 个物种的eBird数据 ({filter_type})")
                else:
                    print("⚠ eBird数据获取失败")
            except Exception as e:
                print(f"⚠ eBird过滤器初始化失败: {e}")
        else:
            print("\n⚠ 无GPS数据或eBird过滤器不可用，将使用全局模式")

        # 加载模型和数据
        print(f"\n📚 正在加载AI模型和数据...")
        model = lazy_load_classifier()
        bird_data = lazy_load_bird_info()
        db_manager = lazy_load_database()
        print(f"✓ 模型和数据加载完成")

        # 定义三个模式的配置
        modes = [
            {
                'name': '快速模式',
                'func': smart_resize_fast,
                'threshold': 1.0,
                'description': '速度优先，直接224x224预处理'
            },
            {
                'name': '平衡模式',
                'func': smart_resize_optimized,
                'threshold': 1.0,
                'description': '测试验证的最佳配置'
            },
            {
                'name': '精确模式',
                'func': smart_resize_adaptive,
                'threshold': 2.0,
                'description': '智能自适应预处理，稍高阈值'
            }
        ]

        # 运行所有模式
        print(f"\n{'='*60}")
        print("🧪 开始三模式对比测试...")

        all_results = []

        for mode_config in modes:
            result = run_single_mode(
                original_image,
                mode_config['name'],
                mode_config['func'],
                mode_config['threshold'],
                bird_data,
                model,
                ebird_species_set,
                use_gps_precise,
                db_manager
            )
            all_results.append(result)

        # 对比分析
        print(f"\n{'='*60}")
        print("📊 三模式对比分析:")
        print(f"{'='*60}")

        # 按不同指标排序
        by_speed = sorted(all_results, key=lambda x: x['inference_time'])
        by_confidence = sorted(all_results, key=lambda x: x['max_confidence'], reverse=True)
        by_results = sorted(all_results, key=lambda x: x['result_count'], reverse=True)

        print(f"\n🏃 速度排行:")
        for i, result in enumerate(by_speed, 1):
            print(f"  {i}. {result['mode']}: {result['inference_time']:.3f}秒")

        print(f"\n📈 最高置信度排行:")
        for i, result in enumerate(by_confidence, 1):
            print(f"  {i}. {result['mode']}: {result['max_confidence']:.2f}%")

        print(f"\n🔢 结果数量排行:")
        for i, result in enumerate(by_results, 1):
            print(f"  {i}. {result['mode']}: {result['result_count']}个结果")

        # 推荐
        print(f"\n💡 推荐:")
        fastest = by_speed[0]
        most_confident = by_confidence[0]
        most_results = by_results[0]

        print(f"  🚀 最快: {fastest['mode']} ({fastest['inference_time']:.3f}s)")
        print(f"  🎯 最高置信度: {most_confident['mode']} ({most_confident['max_confidence']:.2f}%)")
        print(f"  📊 最多结果: {most_results['mode']} ({most_results['result_count']}个)")

        # 如果有eBird过滤，显示过滤效果
        if ebird_species_set:
            filter_info = "GPS精确过滤" if use_gps_precise else f"{auto_country}国家过滤"
            print(f"\n🌍 eBird过滤效果: 使用{filter_info} ({len(ebird_species_set)}个物种)")

            # 统计eBird匹配情况
            for result in all_results:
                if result['results']:
                    ebird_matches = sum(1 for r in result['results'] if 'eBird✓' in r['display_info'] or 'GPS精确✓' in r['display_info'])
                    print(f"  {result['mode']}: {ebird_matches}/{len(result['results'])} 个结果有eBird验证")

        print(f"\n{'='*60}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    image_path = input("📸 请输入图片文件的完整路径: ").strip().strip("'\"")
    test_all_modes(image_path)