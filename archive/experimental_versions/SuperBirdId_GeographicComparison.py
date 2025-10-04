import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import json
import cv2
import csv
import os

# --- 获取脚本所在目录 ---
script_dir = os.path.dirname(os.path.abspath(__file__))

# --- 地理区域识别配置 ---
GEOGRAPHIC_REGIONS = {
    'Australia': ['australian', 'australasian', 'new zealand'],
    'Africa': ['african', 'south african'],
    'Europe': ['european', 'eurasian', 'scandinavian', 'caucasian'],
    'Asia': ['asian', 'indian', 'siberian', 'himalayan', 'chinese', 'ryukyu', 'oriental'],
    'North_America': ['american', 'canadian', 'north american'],
    'South_America': ['brazilian', 'patagonian', 'south american', 'west indian'],
    'Pacific': ['pacific'],
    'Arctic': ['arctic']
}

# --- 国家代码到地理区域映射 ---
COUNTRY_CODE_TO_REGION = {
    # 亚洲
    'CN': 'Asia', 'CHN': 'Asia',  # 中国
    'JP': 'Asia', 'JPN': 'Asia',  # 日本
    'KR': 'Asia', 'KOR': 'Asia',  # 韩国
    'IN': 'Asia', 'IND': 'Asia',  # 印度
    'TH': 'Asia', 'THA': 'Asia',  # 泰国
    'VN': 'Asia', 'VNM': 'Asia',  # 越南
    'MY': 'Asia', 'MYS': 'Asia',  # 马来西亚
    'SG': 'Asia', 'SGP': 'Asia',  # 新加坡
    'ID': 'Asia', 'IDN': 'Asia',  # 印尼
    'PH': 'Asia', 'PHL': 'Asia',  # 菲律宾
    
    # 欧洲
    'GB': 'Europe', 'GBR': 'Europe', 'UK': 'Europe',  # 英国
    'DE': 'Europe', 'DEU': 'Europe', 'GER': 'Europe', # 德国
    'FR': 'Europe', 'FRA': 'Europe',  # 法国
    'IT': 'Europe', 'ITA': 'Europe',  # 意大利
    'ES': 'Europe', 'ESP': 'Europe',  # 西班牙
    'NL': 'Europe', 'NLD': 'Europe',  # 荷兰
    'SE': 'Europe', 'SWE': 'Europe',  # 瑞典
    'NO': 'Europe', 'NOR': 'Europe',  # 挪威
    'FI': 'Europe', 'FIN': 'Europe',  # 芬兰
    'DK': 'Europe', 'DNK': 'Europe',  # 丹麦
    'CH': 'Europe', 'CHE': 'Europe',  # 瑞士
    'AT': 'Europe', 'AUT': 'Europe',  # 奥地利
    'BE': 'Europe', 'BEL': 'Europe',  # 比利时
    'PL': 'Europe', 'POL': 'Europe',  # 波兰
    'RU': 'Europe', 'RUS': 'Europe',  # 俄罗斯
    
    # 北美
    'US': 'North_America', 'USA': 'North_America',  # 美国
    'CA': 'North_America', 'CAN': 'North_America',  # 加拿大
    'MX': 'North_America', 'MEX': 'North_America',  # 墨西哥
    
    # 南美
    'BR': 'South_America', 'BRA': 'South_America',  # 巴西
    'AR': 'South_America', 'ARG': 'South_America',  # 阿根廷
    'CL': 'South_America', 'CHL': 'South_America',  # 智利
    'CO': 'South_America', 'COL': 'South_America',  # 哥伦比亚
    'PE': 'South_America', 'PER': 'South_America',  # 秘鲁
    'VE': 'South_America', 'VEN': 'South_America',  # 委内瑞拉
    
    # 大洋洲
    'AU': 'Australia', 'AUS': 'Australia',  # 澳大利亚
    'NZ': 'Australia', 'NZL': 'Australia',  # 新西兰
    
    # 非洲
    'ZA': 'Africa', 'ZAF': 'Africa',  # 南非
    'KE': 'Africa', 'KEN': 'Africa',  # 肯尼亚
    'TZ': 'Africa', 'TZA': 'Africa',  # 坦桑尼亚
    'UG': 'Africa', 'UGA': 'Africa',  # 乌干达
    'EG': 'Africa', 'EGY': 'Africa',  # 埃及
    'MA': 'Africa', 'MAR': 'Africa',  # 摩洛哥
    'NG': 'Africa', 'NGA': 'Africa',  # 尼日利亚
    'GH': 'Africa', 'GHA': 'Africa',  # 加纳
}

# --- 加载模型和数据 ---
PYTORCH_CLASSIFICATION_MODEL_PATH = os.path.join(script_dir, 'birdid2024.pt')
BIRD_INFO_PATH = os.path.join(script_dir, 'birdinfo.json')
ENDEMIC_PATH = os.path.join(script_dir, 'endemic.json')
LABELMAP_PATH = os.path.join(script_dir, 'labelmap.csv')

try:
    classifier = torch.jit.load(PYTORCH_CLASSIFICATION_MODEL_PATH)
    classifier.eval()
    print("PyTorch classification model loaded successfully.")

    with open(BIRD_INFO_PATH, 'r') as f:
        bird_info = json.load(f)
    print("Bird info file loaded successfully.")

    with open(ENDEMIC_PATH, 'r') as f:
        endemic_info = json.load(f)
    print("Endemic info file loaded successfully.")
    
    # 加载labelmap.csv用于地理区域识别
    labelmap_data = {}
    if os.path.exists(LABELMAP_PATH):
        with open(LABELMAP_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if len(row) >= 2:
                    try:
                        class_id = int(row[0])
                        name = row[1]
                        labelmap_data[class_id] = name
                    except ValueError:
                        continue
        print(f"Label map loaded successfully. {len(labelmap_data)} entries.")
    else:
        print("Label map not found, geographic filtering disabled.")

except Exception as e:
    print(f"Error loading files: {e}")
    exit()

def get_region_from_country_code(country_code):
    """根据国家代码获取地理区域"""
    if not country_code:
        return None
    
    # 转换为大写进行匹配
    country_code = country_code.upper().strip()
    return COUNTRY_CODE_TO_REGION.get(country_code)

def get_bird_region(species_name):
    """根据鸟类名称推断地理区域"""
    if not species_name:
        return 'Unknown'
    
    species_lower = species_name.lower()
    
    for region, keywords in GEOGRAPHIC_REGIONS.items():
        for keyword in keywords:
            if keyword in species_lower:
                return region
    
    return 'Unknown'

def calculate_regional_confidence_boost(species_name, user_region=None):
    """
    基于地理区域匹配计算置信度提升系数
    - 如果物种名称包含用户所在区域的关键词，给予置信度提升
    - 如果是其他已知区域的物种，给予轻微惩罚
    """
    if not user_region or not species_name:
        return 1.0  # 无区域信息时不调整
    
    bird_region = get_bird_region(species_name)
    
    if bird_region == user_region:
        return 1.5  # 本区域物种置信度提升50%
    elif bird_region != 'Unknown':
        return 0.8  # 其他区域物种置信度降低20%
    else:
        return 1.0  # 未知区域物种不调整

def apply_enhancement(image, method="unsharp_mask"):
    """应用最佳图像增强方法"""
    if method == "unsharp_mask":
        return image.filter(ImageFilter.UnsharpMask())
    elif method == "contrast_edge":
        enhancer = ImageEnhance.Brightness(image)
        enhanced = enhancer.enhance(1.2)
        enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = enhancer.enhance(1.3)
        return enhanced.filter(ImageFilter.EDGE_ENHANCE)
    elif method == "desaturate":
        enhancer = ImageEnhance.Color(image)
        return enhancer.enhance(0.5)  # 降低饱和度50%
    else:
        return image

def run_bird_identification(model, image, bird_data, endemic_data, country_code=None, user_region=None):
    """
    鸟类识别主函数
    
    Args:
        model: PyTorch模型
        image: PIL图像对象
        bird_data: 鸟类信息数据
        endemic_data: 特有种信息数据
        country_code: 国家代码 (可选，如 'CN', 'US', 'AU')
        user_region: 用户指定区域 (可选，会被country_code自动转换覆盖)
    
    Returns:
        tuple: (原始识别结果, 地理调整后结果)
    """
    # 如果提供了country_code，自动转换为user_region
    if country_code:
        detected_region = get_region_from_country_code(country_code)
        if detected_region:
            user_region = detected_region
            print(f"🌍 检测到国家代码 '{country_code.upper()}' -> 地理区域: {user_region}")
        else:
            print(f"⚠️  未识别的国家代码 '{country_code}'，将不使用地理筛选")
            user_region = None
    # 使用最佳增强方法：UnsharpMask
    enhanced_image = apply_enhancement(image, "unsharp_mask")
    
    # 标准预处理
    input_size = 224
    resized_image = enhanced_image.resize((256, 256), Image.LANCZOS)
    
    left = (256 - input_size) // 2
    top = (256 - input_size) // 2
    final_image = resized_image.crop((left, top, left + input_size, top + input_size))
    
    # 转换为numpy数组
    img_array = np.array(final_image)
    
    # 关键：转换为BGR通道顺序
    bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # ImageNet标准化 (BGR格式)
    mean = np.array([0.406, 0.456, 0.485])  # BGR: B, G, R
    std = np.array([0.225, 0.224, 0.229])   # BGR: B, G, R
    
    normalized_array = (bgr_array / 255.0 - mean) / std
    input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()
    
    # 推理
    with torch.no_grad():
        output = model(input_tensor)
    
    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    
    # 获取top结果
    k = min(len(probabilities), len(bird_data), 1000)
    all_probs, all_catid = torch.topk(probabilities, k)
    
    # 处理结果 - 原始版本（无地理区域调整）
    original_results = []
    geographic_results = []
    
    candidates = []
    
    for i in range(all_probs.size(0)):
        class_id = all_catid[i].item()
        raw_confidence = all_probs[i].item() * 100
        
        if raw_confidence < 0.5:
            continue
        
        try:
            if class_id < len(bird_data) and len(bird_data[class_id]) >= 2:
                bird_name_cn = bird_data[class_id][0]
                bird_name_en = bird_data[class_id][1]
                name = f"{bird_name_cn} ({bird_name_en})"
                
                # 应用地理区域置信度调整
                region_boost = calculate_regional_confidence_boost(bird_name_en, user_region)
                adjusted_confidence = raw_confidence * region_boost
                
                # 获取鸟类区域信息
                bird_region = get_bird_region(bird_name_en)
                region_info = f" [区域: {bird_region}]" if bird_region != 'Unknown' else ""
                boost_info = f" [调整: {region_boost:.1f}x]" if region_boost != 1.0 else ""
                
                candidates.append({
                    'class_id': class_id,
                    'raw_confidence': raw_confidence,
                    'adjusted_confidence': adjusted_confidence,
                    'name': name,
                    'region': bird_region,
                    'boost': region_boost,
                    'display_info': region_info + boost_info
                })
            else:
                name = f"Unknown (ID: {class_id})"
                candidates.append({
                    'class_id': class_id,
                    'raw_confidence': raw_confidence,
                    'adjusted_confidence': raw_confidence,
                    'name': name,
                    'region': 'Unknown',
                    'boost': 1.0,
                    'display_info': ""
                })
        except (IndexError, TypeError):
            name = f"Unknown (ID: {class_id})"
            candidates.append({
                'class_id': class_id,
                'raw_confidence': raw_confidence,
                'adjusted_confidence': raw_confidence,
                'name': name,
                'region': 'Unknown',
                'boost': 1.0,
                'display_info': ""
            })
    
    # 原始排序（按原始置信度）
    original_candidates = sorted(candidates, key=lambda x: x['raw_confidence'], reverse=True)
    for candidate in original_candidates[:5]:
        if candidate['raw_confidence'] >= 1.0:
            original_results.append(
                f"  - {candidate['raw_confidence']:.2f}% | {candidate['name']}"
            )
    
    # 地理调整排序（按调整后置信度）
    geographic_candidates = sorted(candidates, key=lambda x: x['adjusted_confidence'], reverse=True)
    for candidate in geographic_candidates[:5]:
        if candidate['adjusted_confidence'] >= 1.0:
            geographic_results.append(
                f"  - 原始: {candidate['raw_confidence']:.2f}% → 调整: {candidate['adjusted_confidence']:.2f}% | {candidate['name']}{candidate['display_info']}"
            )
    
    # 打印对比结果
    # 显示识别结果
    print("="*80)
    print("🔍 鸟类识别结果")
    print("="*80)
    
    print(f"\n📍 目标区域: {user_region if user_region else '全球范围'}")
    if user_region:
        print(f"📋 调整规则: {user_region}地区物种置信度 +50%, 其他地区物种 -20%")
    
    print(f"\n📊 原始识别结果 (按模型置信度排序):")
    if original_results:
        for result in original_results:
            print(result)
    else:
        print("  - 无满足条件的识别结果")
    
    if user_region:
        print(f"\n🌍 地理区域调整后结果 (按调整后置信度排序):")
        if geographic_results:
            for result in geographic_results:
                print(result)
        else:
            print("  - 无满足条件的识别结果")
        
        # 分析排序变化
        original_top = original_candidates[0]['name'] if original_candidates else None
        geographic_top = geographic_candidates[0]['name'] if geographic_candidates else None
        
        if original_top and geographic_top:
            if original_top != geographic_top:
                print(f"\n🎯 排序变化检测:")
                print(f"   原始第一名: {original_top}")
                print(f"   调整第一名: {geographic_top}")
                print("   ✅ 地理区域筛选影响了结果排序!")
            else:
                print(f"\n🎯 排序保持不变: {original_top}")
    
    return original_results, geographic_results

def identify_bird_from_image_path(image_path, country_code=None):
    """
    从图片路径识别鸟类的便捷函数 - 为API接口准备
    
    Args:
        image_path: 图片文件路径
        country_code: 国家代码 (可选)
    
    Returns:
        tuple: (原始识别结果, 地理调整后结果)
    """
    try:
        original_image = Image.open(image_path).convert("RGB")
        return run_bird_identification(
            classifier, original_image, bird_info, endemic_info, 
            country_code=country_code
        )
    except FileNotFoundError:
        print(f"错误: 文件未找到, 请检查路径 '{image_path}' 是否正确。")
        return None, None
    except Exception as e:
        print(f"识别过程中发生错误: {e}")
        return None, None

def identify_bird_from_pil_image(image, country_code=None):
    """
    从PIL图像对象识别鸟类的便捷函数 - 为API接口准备
    
    Args:
        image: PIL图像对象
        country_code: 国家代码 (可选)
    
    Returns:
        tuple: (原始识别结果, 地理调整后结果)
    """
    try:
        return run_bird_identification(
            classifier, image, bird_info, endemic_info, 
            country_code=country_code
        )
    except Exception as e:
        print(f"识别过程中发生错误: {e}")
        return None, None

def get_structured_bird_identification(image_path, country_code=None, top_k=5):
    """
    返回结构化的鸟类识别结果 - API友好的函数
    
    Args:
        image_path: 图片路径
        country_code: 国家代码 (可选)
        top_k: 返回结果数量
    
    Returns:
        dict: {
            'status': 'success'|'error',
            'message': '错误信息(仅在错误时)',
            'country_code': '传入的国家代码',
            'detected_region': '检测到的地理区域',
            'results': [
                {
                    'rank': 排名,
                    'confidence': 置信度,
                    'name_cn': '中文名称',
                    'name_en': '英文名称',
                    'region': '鸟类区域',
                    'is_boosted': 是否被地理优化
                }
            ]
        }
    """
    try:
        # 检测区域
        detected_region = None
        if country_code:
            detected_region = get_region_from_country_code(country_code)
        
        # 执行识别
        original_results, geographic_results = identify_bird_from_image_path(
            image_path, country_code
        )
        
        if original_results is None:
            return {
                'status': 'error',
                'message': '图片加载或识别失败',
                'country_code': country_code,
                'detected_region': detected_region,
                'results': []
            }
        
        # 解析结果
        structured_results = []
        results_to_parse = geographic_results if detected_region and geographic_results else original_results
        
        for i, result in enumerate(results_to_parse[:top_k]):
            # 解析结果字符串 (format: "- XX.XX% | 中文名 (English Name)")
            parts = result.split('|', 1)
            if len(parts) >= 2:
                confidence_part = parts[0].strip()
                name_part = parts[1].strip()
                
                # 提取置信度
                confidence = 0.0
                if '%' in confidence_part:
                    confidence_str = confidence_part.split('%')[0].split()[-1]
                    try:
                        confidence = float(confidence_str)
                    except:
                        pass
                
                # 提取名称
                name_cn = ''
                name_en = ''
                if '(' in name_part and ')' in name_part:
                    name_cn = name_part.split('(')[0].strip()
                    name_en = name_part.split('(')[1].split(')')[0].strip()
                else:
                    name_cn = name_part.strip()
                
                # 获取鸟类区域
                bird_region = get_bird_region(name_en) if name_en else 'Unknown'
                
                # 是否被优化
                is_boosted = detected_region and bird_region == detected_region
                
                structured_results.append({
                    'rank': i + 1,
                    'confidence': confidence,
                    'name_cn': name_cn,
                    'name_en': name_en,
                    'region': bird_region,
                    'is_boosted': is_boosted
                })
        
        return {
            'status': 'success',
            'country_code': country_code.upper() if country_code else None,
            'detected_region': detected_region,
            'results': structured_results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'识别过程错误: {str(e)}',
            'country_code': country_code,
            'detected_region': None,
            'results': []
        }

def interactive_bird_identification():
    """
    交互式鸟类识别 - 命令行界面
    """
    print("🦅 SuperBirdID 地理优化版")
    print("=" * 50)
    
    # 获取图片路径
    image_path = input("📸 请输入图片文件的完整路径: ")
    
    # 获取用户的国家代码 (可选)
    print("\n🌍 地理区域优化 (可选)")
    print("提示: 输入您的国家代码可以提高当地鸟类的识别准确度")
    print("常见代码: CN(中国), US(美国), AU(澳大利亚), GB(英国), CA(加拿大)")
    country_code = input("请输入您的国家代码 (直接回车跳过): ").strip()
    
    # 执行识别
    original_results, geographic_results = identify_bird_from_image_path(
        image_path, country_code
    )
    
    if original_results is None:
        print("❌ 识别失败")
        return
    
    print("\n✅ 识别完成!")

def batch_bird_identification(image_paths, country_code=None):
    """
    批量鸟类识别 - 适用于API调用
    
    Args:
        image_paths: 图片路径列表
        country_code: 国家代码 (可选)
    
    Returns:
        list: 识别结果列表
    """
    results = []
    for image_path in image_paths:
        print(f"\n处理图片: {image_path}")
        original_results, geographic_results = identify_bird_from_image_path(
            image_path, country_code
        )
        results.append({
            'image_path': image_path,
            'original_results': original_results,
            'geographic_results': geographic_results
        })
    return results

# === API 使用示例 ===
"""
API使用示例：

# 基本使用
from SuperBirdId_GeographicComparison import get_structured_bird_identification

# 方式1: 不指定地理区域
result = get_structured_bird_identification("/path/to/bird_image.jpg")

# 方式2: 指定国家代码，自动优化识别结果
result = get_structured_bird_identification("/path/to/bird_image.jpg", country_code="CN")

# 检查结果
if result['status'] == 'success':
    print(f"识别成功！检测到区域: {result['detected_region']}")
    for bird in result['results'][:3]:  # 显示Top 3结果
        boost_info = " (地理优化)" if bird['is_boosted'] else ""
        print(f"{bird['rank']}. {bird['name_cn']} ({bird['name_en']}) - {bird['confidence']:.2f}%{boost_info}")
else:
    print(f"识别失败: {result['message']}")

# 返回的数据结构:
# {
#     'status': 'success'|'error',
#     'country_code': '国家代码(如果提供)',
#     'detected_region': '检测到的地理区域',
#     'results': [
#         {
#             'rank': 1,
#             'confidence': 85.67,
#             'name_cn': '红嘴蓝鹊',
#             'name_en': 'Red-billed Blue Magpie',
#             'region': 'Asia',
#             'is_boosted': True  # 表示这个结果被地理优化提升了
#         },
#         ...
#     ]
# }

常见国家代码:
CN/CHN: 中国        US/USA: 美国        AU/AUS: 澳大利亚
GB/UK: 英国         CA/CAN: 加拿大      DE/GER: 德国
JP/JPN: 日本        FR/FRA: 法国        BR/BRA: 巴西
"""

# --- 主程序 ---
if __name__ == "__main__":
    interactive_bird_identification()