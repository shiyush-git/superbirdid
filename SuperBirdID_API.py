#!/usr/bin/env python3
"""
SuperBirdID API服务器
提供HTTP REST API供外部程序调用鸟类识别功能
可被Lightroom插件等外部应用调用
"""

__version__ = "3.2.1"

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import base64
from io import BytesIO
from PIL import Image
import tempfile
import torch
import numpy as np
import cv2
import json

# 导入核心识别模块
from SuperBirdId import (
    load_image, lazy_load_classifier, lazy_load_bird_info, lazy_load_database,
    extract_gps_from_exif, get_region_from_gps,
    write_bird_name_to_exif, get_bird_description_from_db,
    write_bird_caption_to_exif, get_user_data_dir, script_dir,
    YOLOBirdDetector, YOLO_AVAILABLE, EBIRD_FILTER_AVAILABLE, DATABASE_AVAILABLE
)

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局变量存储模型（延迟加载）
classifier = None
bird_info_dict = None
db_manager = None
ebird_filter = None

# 全局配置（从 GUI 配置文件读取）
default_country_code = None
default_region_code = None
use_ebird_filter = True

def load_gui_settings():
    """
    读取 GUI 配置文件，获取用户最后设置的国家/地区
    返回: (country_code, region_code, use_ebird)
    """
    config_file = os.path.join(script_dir, 'gui_settings.json')

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                country_code = settings.get('country_code')
                region_code = settings.get('region_code')
                use_ebird = settings.get('use_ebird', True)

                print(f"📖 读取GUI配置: country_code={country_code}, region_code={region_code}, use_ebird={use_ebird}")
                return country_code, region_code, use_ebird
        except Exception as e:
            print(f"⚠️ 读取GUI配置失败: {e}")
    else:
        print(f"ℹ️ 未找到GUI配置文件: {config_file}")

    return None, None, True

def ensure_models_loaded():
    """确保模型已加载"""
    global classifier, bird_info_dict, db_manager, ebird_filter

    if classifier is None:
        print("⏳ 正在加载分类器模型...")
        classifier = lazy_load_classifier()
        print("✓ 分类器模型加载完成")

    if bird_info_dict is None:
        print("⏳ 正在加载鸟种信息...")
        bird_info_dict = lazy_load_bird_info()
        print("✓ 鸟种信息加载完成")

    if db_manager is None and DATABASE_AVAILABLE:
        print("⏳ 正在加载数据库...")
        db_manager = lazy_load_database()
        print("✓ 数据库加载完成")

    if ebird_filter is None and EBIRD_FILTER_AVAILABLE:
        try:
            from ebird_country_filter import eBirdCountryFilter
            # eBird API key (用于地理位置过滤)
            ebird_filter = eBirdCountryFilter(api_key="7erj90ufajtt")
            print("✓ eBird过滤器加载完成")
        except Exception as e:
            print(f"⚠️ eBird过滤器加载失败: {e}")

def predict_bird(image, top_k=3):
    """
    使用分类器预测鸟类
    返回: [(class_idx, confidence), ...]
    """
    # 确保图像是PIL Image
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)

    # 调整大小到224x224
    image = image.resize((224, 224), Image.LANCZOS)

    # 转换为numpy数组
    img_array = np.array(image)

    # 转换为BGR通道顺序（OpenCV格式）
    bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # ImageNet标准化 (BGR格式)
    mean = np.array([0.406, 0.456, 0.485])  # BGR: B, G, R
    std = np.array([0.225, 0.224, 0.229])

    normalized_array = (bgr_array / 255.0 - mean) / std
    input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()

    # 推理
    with torch.no_grad():
        output = classifier(input_tensor)

    # 温度锐化: 提升置信度 (T=0.6)
    TEMPERATURE = 0.6
    probabilities = torch.nn.functional.softmax(output[0] / TEMPERATURE, dim=0)

    # 获取top-k结果
    top_probs, top_indices = torch.topk(probabilities, min(top_k, len(probabilities)))

    # 返回结果: [(class_idx, confidence), ...]
    results = []
    for i in range(len(top_indices)):
        class_idx = top_indices[i].item()
        confidence = top_probs[i].item() * 100  # 转换为百分比
        results.append((class_idx, confidence))

    return results

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'service': 'SuperBirdID API',
        'version': '3.1.0',
        'yolo_available': YOLO_AVAILABLE,
        'ebird_available': EBIRD_FILTER_AVAILABLE
    })

@app.route('/recognize', methods=['POST'])
def recognize_bird():
    """
    识别鸟类

    请求体 (JSON):
    {
        "image_path": "/path/to/image.jpg",  // 图片路径（二选一）
        "image_base64": "base64_encoded_image",  // Base64编码的图片（二选一）
        "use_yolo": true,  // 是否使用YOLO裁剪（可选，默认true）
        "use_gps": true,  // 是否使用GPS过滤（可选，默认true）
        "top_k": 3  // 返回前K个结果（可选，默认3）
    }

    返回 (JSON):
    {
        "success": true,
        "results": [
            {
                "rank": 1,
                "cn_name": "白头鹎",
                "en_name": "Light-vented Bulbul",
                "scientific_name": "Pycnonotus sinensis",
                "confidence": 95.5,
                "ebird_match": true
            },
            ...
        ],
        "gps_info": {
            "latitude": 39.123,
            "longitude": 116.456,
            "region": "中国"
        }
    }
    """
    try:
        # 确保模型已加载
        ensure_models_loaded()

        # 解析请求参数
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': '无效的请求体'}), 400

        # 获取图片
        image = None
        image_path = data.get('image_path')
        image_base64 = data.get('image_base64')
        temp_file = None

        if image_path:
            # 从文件路径加载
            if not os.path.exists(image_path):
                return jsonify({'success': False, 'error': f'文件不存在: {image_path}'}), 404
            image = load_image(image_path)
        elif image_base64:
            # 从Base64解码
            try:
                image_data = base64.b64decode(image_base64)
                image = Image.open(BytesIO(image_data))

                # 创建临时文件用于EXIF读取
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                image.save(temp_file.name, 'JPEG')
                image_path = temp_file.name
            except Exception as e:
                return jsonify({'success': False, 'error': f'Base64解码失败: {e}'}), 400
        else:
            return jsonify({'success': False, 'error': '必须提供image_path或image_base64'}), 400

        # 获取参数
        use_yolo = data.get('use_yolo', True)
        use_gps = data.get('use_gps', True)
        top_k = data.get('top_k', 3)

        # YOLO裁剪（如果启用且图片足够大）
        processed_image = image
        yolo_msg = None
        if use_yolo and YOLO_AVAILABLE:
            width, height = image.size
            if max(width, height) > 640:
                detector = YOLOBirdDetector()
                cropped, msg = detector.detect_and_crop_bird(image)
                if cropped:
                    processed_image = cropped
                    yolo_msg = msg

        # GPS信息提取
        gps_info = None
        lat, lon = None, None
        if use_gps and image_path:
            lat, lon, location_info = extract_gps_from_exif(image_path)
            if lat and lon:
                region, country_code, region_info = get_region_from_gps(lat, lon)
                gps_info = {
                    'latitude': lat,
                    'longitude': lon,
                    'region': region,
                    'country_code': country_code,
                    'info': location_info
                }

        # ===== 新增：eBird 地理筛选逻辑 =====
        ebird_species_set = None
        filter_source = "全球模式"

        if use_ebird_filter and EBIRD_FILTER_AVAILABLE:
            try:
                # 初始化 eBird 过滤器
                from ebird_country_filter import eBirdCountryFilter
                EBIRD_API_KEY = os.environ.get('EBIRD_API_KEY', '60nan25sogpo')
                cache_dir = os.path.join(get_user_data_dir(), 'ebird_cache')
                offline_dir = os.path.join(script_dir, "offline_ebird_data")
                ebird_filter = eBirdCountryFilter(EBIRD_API_KEY, cache_dir=cache_dir, offline_dir=offline_dir)

                # 优先级 1：GPS 精确位置（25km 范围）
                if lat and lon:
                    print(f"🎯 使用 GPS 精确位置筛选: ({lat:.3f}, {lon:.3f})")
                    ebird_species_set = ebird_filter.get_location_species_list(lat, lon, 25)
                    if ebird_species_set:
                        filter_source = f"GPS 25km ({len(ebird_species_set)} 种)"
                        print(f"✓ GPS 筛选成功: {len(ebird_species_set)} 个物种")
                    else:
                        print("⚠️ GPS 筛选失败，尝试国家级别...")

                # 优先级 2：配置文件中的国家/地区
                if not ebird_species_set and default_country_code:
                    print(f"🌍 使用配置文件国家筛选: {default_country_code}")
                    region_code = default_region_code if default_region_code else default_country_code
                    ebird_species_set = ebird_filter.get_country_species_list(region_code)
                    if ebird_species_set:
                        filter_source = f"配置国家 {region_code} ({len(ebird_species_set)} 种)"
                        print(f"✓ 国家筛选成功: {len(ebird_species_set)} 个物种")
                    else:
                        print("⚠️ 国家筛选失败")

                # 优先级 3：GPS 推断的国家
                if not ebird_species_set and gps_info and gps_info.get('country_code'):
                    gps_country = gps_info['country_code']
                    print(f"🌍 使用 GPS 推断国家筛选: {gps_country}")
                    ebird_species_set = ebird_filter.get_country_species_list(gps_country)
                    if ebird_species_set:
                        filter_source = f"GPS 国家 {gps_country} ({len(ebird_species_set)} 种)"
                        print(f"✓ GPS 国家筛选成功: {len(ebird_species_set)} 个物种")

                if not ebird_species_set:
                    print("ℹ️ 所有筛选方法都失败，使用全球模式")
                    filter_source = "全球模式（无筛选）"

            except Exception as e:
                print(f"❌ eBird 筛选初始化失败: {e}")
                import traceback
                traceback.print_exc()
                filter_source = "全球模式（筛选失败）"

        # 执行识别（获取更多候选结果用于筛选）
        predict_top_k = 100 if ebird_species_set else top_k
        predictions = predict_bird(processed_image, top_k=predict_top_k)

        # 处理结果并应用 eBird 筛选
        results = []
        filtered_out = []  # 被筛选掉的结果

        for class_idx, confidence in predictions:
            # 跳过置信度过低的结果
            if confidence < 5.0:
                continue

            # bird_info_dict 是数组，检查索引范围
            if 0 <= class_idx < len(bird_info_dict):
                bird_data = bird_info_dict[class_idx]

                # bird_data 是列表: [cn_name, en_name, scientific_name, ...]
                cn_name = bird_data[0] if len(bird_data) > 0 else "未知"
                en_name = bird_data[1] if len(bird_data) > 1 else "Unknown"
                scientific_name = bird_data[2] if len(bird_data) > 2 else ""

                # eBird 筛选检查
                ebird_match = False
                should_filter_out = False

                if ebird_species_set and db_manager:
                    # 获取 eBird 代码
                    ebird_code = db_manager.get_ebird_code_by_english_name(en_name)

                    if ebird_code and ebird_code in ebird_species_set:
                        ebird_match = True
                    else:
                        # 不在列表中，过滤掉
                        should_filter_out = True
                        filtered_out.append({
                            'cn_name': cn_name,
                            'en_name': en_name,
                            'confidence': confidence
                        })

                # 如果不需要过滤，或者没有启用筛选，则添加到结果
                if not should_filter_out:
                    # 从数据库获取详细描述
                    description = None
                    if DATABASE_AVAILABLE and db_manager:
                        bird_detail = db_manager.get_bird_by_class_id(class_idx)
                        if bird_detail:
                            description = bird_detail.get('short_description_zh')

                    result_item = {
                        'rank': len(results) + 1,
                        'cn_name': cn_name,
                        'en_name': en_name,
                        'scientific_name': scientific_name,
                        'confidence': float(confidence),
                        'ebird_match': ebird_match
                    }

                    # 只在有描述时添加
                    if description:
                        result_item['description'] = description

                    results.append(result_item)

                    # 只保留 top_k 个结果
                    if len(results) >= top_k:
                        break

        # 如果筛选后没有结果，记录被筛选的前几个
        if ebird_species_set and len(results) == 0 and len(filtered_out) > 0:
            print(f"⚠️ eBird筛选导致所有结果被过滤")
            print(f"   被过滤的前3个: {filtered_out[:3]}")
            # 可以选择返回警告信息
            # 这里我们仍返回空结果，但在响应中添加提示

        # 清理临时文件
        if temp_file:
            try:
                os.unlink(temp_file.name)
            except:
                pass

        # 返回结果
        response = {
            'success': True,
            'results': results,
            'yolo_info': yolo_msg,
            'gps_info': gps_info,
            'filter_source': filter_source  # 添加筛选数据来源信息
        }

        # 如果所有结果都被过滤，添加警告
        if ebird_species_set and len(results) == 0 and len(filtered_out) > 0:
            response['warning'] = f"地理筛选：未找到匹配结果。AI识别的前3个物种不在{filter_source}列表中"
            response['filtered_top3'] = filtered_out[:3]

        return jsonify(response)

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/bird/info', methods=['GET'])
def get_bird_info():
    """
    获取鸟种详细信息

    参数:
    - cn_name: 中文名称

    返回:
    {
        "success": true,
        "info": {
            "cn_name": "白头鹎",
            "en_name": "Light-vented Bulbul",
            "scientific_name": "Pycnonotus sinensis",
            "short_description": "...",
            "full_description": "...",
            "ebird_code": "..."
        }
    }
    """
    try:
        cn_name = request.args.get('cn_name')

        if not cn_name:
            return jsonify({'success': False, 'error': '缺少cn_name参数'}), 400

        bird_info = get_bird_description_from_db(cn_name)

        if not bird_info:
            return jsonify({'success': False, 'error': f'未找到 {cn_name} 的信息'}), 404

        return jsonify({
            'success': True,
            'info': bird_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/exif/write-title', methods=['POST'])
def write_exif_title():
    """
    写入鸟种名称到EXIF Title

    请求体:
    {
        "image_path": "/path/to/image.jpg",
        "bird_name": "白头鹎"
    }
    """
    try:
        data = request.get_json()
        image_path = data.get('image_path')
        bird_name = data.get('bird_name')

        if not image_path or not bird_name:
            return jsonify({'success': False, 'error': '缺少必需参数'}), 400

        success, message = write_bird_name_to_exif(image_path, bird_name)

        return jsonify({
            'success': success,
            'message': message
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/exif/write-caption', methods=['POST'])
def write_exif_caption():
    """
    写入鸟种描述到EXIF Caption

    请求体:
    {
        "image_path": "/path/to/image.jpg",
        "caption": "鸟种描述文本"
    }
    """
    try:
        data = request.get_json()
        image_path = data.get('image_path')
        caption = data.get('caption')

        if not image_path or not caption:
            return jsonify({'success': False, 'error': '缺少必需参数'}), 400

        success, message = write_bird_caption_to_exif(image_path, caption)

        return jsonify({
            'success': success,
            'message': message
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='SuperBirdID API服务器')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址（默认127.0.0.1）')
    parser.add_argument('--port', type=int, default=5156, help='监听端口（默认5156）')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')

    args = parser.parse_args()

    print("=" * 60)
    print(f"🐦 SuperBirdID API 服务器 v{__version__}")
    print("=" * 60)
    print(f"监听地址: http://{args.host}:{args.port}")
    print(f"健康检查: http://{args.host}:{args.port}/health")
    print(f"识别接口: POST http://{args.host}:{args.port}/recognize")
    print(f"鸟种信息: GET http://{args.host}:{args.port}/bird/info?cn_name=白头鹎")
    print("=" * 60)
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    # 读取 GUI 配置
    print("\n📖 读取用户配置...")
    # 在模块顶层不需要 global 声明
    default_country_code, default_region_code, use_ebird_filter = load_gui_settings()

    if default_country_code:
        region_info = default_region_code if default_region_code else default_country_code
        print(f"✓ 默认地区: {region_info}")
    else:
        print("ℹ️ 未设置默认地区，将使用全球模式")

    print(f"✓ eBird筛选: {'启用' if use_ebird_filter else '禁用'}")

    # 预加载模型
    print("\n正在预加载模型...")
    ensure_models_loaded()
    print("✓ 模型预加载完成\n")

    # 启动服务器
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
