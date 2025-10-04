#!/usr/bin/env python3
"""
SuperBirdID API服务器
提供HTTP REST API供外部程序调用鸟类识别功能
可被Lightroom插件等外部应用调用
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import base64
from io import BytesIO
from PIL import Image
import tempfile

# 导入核心识别模块
from SuperBirdId import (
    load_image, lazy_load_classifier, lazy_load_bird_info, lazy_load_database,
    extract_gps_from_exif, get_region_from_gps,
    write_bird_name_to_exif, get_bird_description_from_db,
    write_bird_caption_to_exif,
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
            ebird_filter = eBirdCountryFilter()
            print("✓ eBird过滤器加载完成")
        except Exception as e:
            print(f"⚠️ eBird过滤器加载失败: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'service': 'SuperBirdID API',
        'version': '1.0.0',
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
        if use_gps and image_path:
            lat, lon, location_info = extract_gps_from_exif(image_path)
            if lat and lon:
                region = get_region_from_gps(lat, lon)
                gps_info = {
                    'latitude': lat,
                    'longitude': lon,
                    'region': region,
                    'info': location_info
                }

        # 执行识别
        predictions = classifier.predict(processed_image)

        # 处理结果
        results = []
        for i, (class_idx, confidence) in enumerate(predictions[:top_k], 1):
            if class_idx in bird_info_dict:
                bird = bird_info_dict[class_idx]

                # eBird匹配检查
                ebird_match = False
                if use_gps and gps_info and DATABASE_AVAILABLE and db_manager:
                    ebird_match = db_manager.check_species_in_region(
                        bird['scientific_name'],
                        gps_info['region']
                    )

                results.append({
                    'rank': i,
                    'cn_name': bird['cn_name'],
                    'en_name': bird['en_name'],
                    'scientific_name': bird['scientific_name'],
                    'confidence': float(confidence),
                    'ebird_match': ebird_match
                })

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
            'gps_info': gps_info
        }

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
    parser.add_argument('--port', type=int, default=5000, help='监听端口（默认5000）')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')

    args = parser.parse_args()

    print("=" * 60)
    print("🐦 SuperBirdID API 服务器")
    print("=" * 60)
    print(f"监听地址: http://{args.host}:{args.port}")
    print(f"健康检查: http://{args.host}:{args.port}/health")
    print(f"识别接口: POST http://{args.host}:{args.port}/recognize")
    print(f"鸟种信息: GET http://{args.host}:{args.port}/bird/info?cn_name=白头鹎")
    print("=" * 60)
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    # 预加载模型
    print("\n正在预加载模型...")
    ensure_models_loaded()
    print("✓ 模型预加载完成\n")

    # 启动服务器
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
