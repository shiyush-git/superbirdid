#!/usr/bin/env python3
"""
SuperBirdID API 客户端示例
演示如何从外部程序（如Lightroom插件）调用API
"""

import requests
import json
import base64
import os

# API服务器地址
API_BASE_URL = "http://127.0.0.1:5156"

def check_health():
    """检查API服务器健康状态"""
    response = requests.get(f"{API_BASE_URL}/health")
    print("健康检查:", json.dumps(response.json(), indent=2, ensure_ascii=False))
    return response.json()

def recognize_bird_from_path(image_path, use_yolo=True, use_gps=True, top_k=3):
    """
    从图片路径识别鸟类

    Args:
        image_path: 图片路径
        use_yolo: 是否使用YOLO裁剪
        use_gps: 是否使用GPS过滤
        top_k: 返回前K个结果
    """
    data = {
        "image_path": image_path,
        "use_yolo": use_yolo,
        "use_gps": use_gps,
        "top_k": top_k
    }

    response = requests.post(f"{API_BASE_URL}/recognize", json=data)
    result = response.json()

    if result.get('success'):
        print(f"\n✓ 识别成功！")
        print(f"YOLO信息: {result.get('yolo_info', 'N/A')}")

        if result.get('gps_info'):
            gps = result['gps_info']
            print(f"GPS信息: {gps['info']}")
            print(f"地区: {gps['region']}")

        print(f"\n识别结果:")
        for r in result['results']:
            ebird = "✓ eBird" if r['ebird_match'] else ""
            print(f"  {r['rank']}. {r['cn_name']} ({r['en_name']}) - {r['confidence']:.2f}% {ebird}")

        return result
    else:
        print(f"✗ 识别失败: {result.get('error')}")
        return None

def recognize_bird_from_base64(image_path):
    """
    从Base64编码的图片识别鸟类（适合跨网络传输）
    """
    # 读取图片并编码为Base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')

    data = {
        "image_base64": image_base64,
        "use_yolo": True,
        "use_gps": False,  # Base64模式通常无法读取EXIF GPS
        "top_k": 3
    }

    response = requests.post(f"{API_BASE_URL}/recognize", json=data)
    result = response.json()

    if result.get('success'):
        print(f"\n✓ Base64模式识别成功！")
        for r in result['results']:
            print(f"  {r['rank']}. {r['cn_name']} - {r['confidence']:.2f}%")
        return result
    else:
        print(f"✗ 识别失败: {result.get('error')}")
        return None

def get_bird_description(cn_name):
    """获取鸟种详细信息"""
    response = requests.get(f"{API_BASE_URL}/bird/info", params={'cn_name': cn_name})
    result = response.json()

    if result.get('success'):
        info = result['info']
        print(f"\n鸟种详细信息:")
        print(f"中文名: {info['cn_name']}")
        print(f"英文名: {info['en_name']}")
        print(f"学名: {info['scientific_name']}")
        print(f"eBird代码: {info['ebird_code']}")
        print(f"\n简介:")
        print(info['short_description'])
        return info
    else:
        print(f"✗ 获取失败: {result.get('error')}")
        return None

def write_exif_title(image_path, bird_name):
    """写入鸟种名称到EXIF Title"""
    data = {
        "image_path": image_path,
        "bird_name": bird_name
    }

    response = requests.post(f"{API_BASE_URL}/exif/write-title", json=data)
    result = response.json()

    if result.get('success'):
        print(f"✓ EXIF Title写入成功: {result['message']}")
    else:
        print(f"✗ 写入失败: {result.get('error')}")

    return result

def write_exif_caption(image_path, caption):
    """写入描述到EXIF Caption"""
    data = {
        "image_path": image_path,
        "caption": caption
    }

    response = requests.post(f"{API_BASE_URL}/exif/write-caption", json=data)
    result = response.json()

    if result.get('success'):
        print(f"✓ EXIF Caption写入成功: {result['message']}")
    else:
        print(f"✗ 写入失败: {result.get('error')}")

    return result

# 完整工作流程示例
def full_workflow_example(image_path):
    """
    完整工作流程示例:
    1. 健康检查
    2. 识别鸟类
    3. 获取详细信息
    4. 写入EXIF
    """
    print("=" * 60)
    print("SuperBirdID API 完整工作流程示例")
    print("=" * 60)

    # 1. 健康检查
    print("\n步骤 1: 健康检查")
    check_health()

    # 2. 识别鸟类
    print("\n步骤 2: 识别鸟类")
    result = recognize_bird_from_path(image_path)

    if not result or not result.get('success'):
        print("识别失败，退出")
        return

    # 3. 获取第一名的详细信息
    top_result = result['results'][0]
    bird_name = top_result['cn_name']

    print(f"\n步骤 3: 获取 {bird_name} 的详细信息")
    bird_info = get_bird_description(bird_name)

    # 4. 写入EXIF
    print(f"\n步骤 4: 写入EXIF元数据")
    write_exif_title(image_path, bird_name)

    if bird_info and bird_info.get('short_description'):
        write_exif_caption(image_path, bird_info['short_description'])

    print("\n" + "=" * 60)
    print("✓ 完整工作流程执行完成！")
    print("=" * 60)

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <图片路径>")
        print(f"\n示例:")
        print(f"  python {sys.argv[0]} /path/to/bird.jpg")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.exists(image_path):
        print(f"错误: 文件不存在: {image_path}")
        sys.exit(1)

    # 执行完整工作流程
    full_workflow_example(image_path)
