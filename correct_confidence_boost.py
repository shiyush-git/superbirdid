#!/usr/bin/env python3
"""
修正版置信度提升工具
基于实际测试结果的正确优化策略
"""
import torch
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import cv2
from typing import List, Dict, Tuple
import time

from SuperBirdId import lazy_load_classifier, lazy_load_bird_info, lazy_load_database


def boost_confidence_correct(image_path: str,
                             strategy: str = 'sharp',
                             ebird_country: str = 'australia') -> List[Dict]:
    """
    正确的置信度提升策略

    Args:
        image_path: 图像路径
        strategy: 'sharp' (锐化分布), 'tta' (测试时增强), 'both' (组合)
        ebird_country: eBird国家过滤

    Returns:
        识别结果列表
    """
    print("="*60)
    print("🚀 修正版置信度提升工具")
    print("="*60)
    print(f"策略: {strategy}")
    print()

    # 加载资源
    model = lazy_load_classifier()
    bird_info = lazy_load_bird_info()
    db_manager = lazy_load_database()

    # eBird过滤
    ebird_species = None
    if ebird_country:
        try:
            from ebird_country_filter import eBirdCountryFilter
            filter_obj = eBirdCountryFilter("60nan25sogpo", offline_dir="offline_ebird_data")
            ebird_species = filter_obj.get_country_species_list(ebird_country)
            if ebird_species:
                print(f"✓ eBird过滤: {ebird_country}, {len(ebird_species)}个物种")
        except:
            print("⚠ eBird过滤失败，继续无过滤模式")

    # 加载图像
    original = Image.open(image_path).convert('RGB')
    print(f"✓ 图像: {original.size}")
    print()

    if strategy == 'sharp':
        return _sharp_strategy(original, model, bird_info, db_manager, ebird_species)
    elif strategy == 'tta':
        return _tta_strategy(original, model, bird_info, db_manager, ebird_species)
    elif strategy == 'both':
        return _combined_strategy(original, model, bird_info, db_manager, ebird_species)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def _sharp_strategy(image: Image.Image, model, bird_info: List,
                   db_manager, ebird_species: set) -> List[Dict]:
    """
    策略1: 锐化分布 (Temperature < 1.0)
    优点: 速度快，置信度大幅提升
    """
    print("🔵 策略: 温度锐化 (T=0.6)")

    # 预处理
    resized = image.resize((256, 256), Image.LANCZOS)
    cropped = resized.crop((16, 16, 240, 240))

    arr = np.array(cropped)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    normalized = (bgr / 255.0 - np.array([0.406, 0.456, 0.485])) / np.array([0.225, 0.224, 0.229])
    tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

    # 推理
    start = time.time()
    with torch.no_grad():
        logits = model(tensor)[0]

    # 温度锐化: T=0.6 (经验值)
    TEMPERATURE = 0.6
    probs = torch.nn.functional.softmax(logits / TEMPERATURE, dim=0)

    elapsed = time.time() - start
    print(f"⏱️  推理时间: {elapsed:.3f}秒")

    # 提取结果
    results = _extract_results(probs.numpy(), bird_info, db_manager, ebird_species, top_k=10)

    _print_results(results, "温度锐化")

    return results


def _tta_strategy(image: Image.Image, model, bird_info: List,
                 db_manager, ebird_species: set) -> List[Dict]:
    """
    策略2: TTA测试时增强
    优点: 稳定性高，适合难以识别的图片
    """
    print("🟢 策略: TTA (6种变换 + 温度锐化)")

    # 定义增强
    augmentations = [
        ('原始', lambda x: x),
        ('水平翻转', lambda x: x.transpose(Image.FLIP_LEFT_RIGHT)),
        ('锐化', lambda x: x.filter(ImageFilter.SHARPEN)),
        ('对比度+20%', lambda x: ImageEnhance.Contrast(x).enhance(1.2)),
        ('亮度+10%', lambda x: ImageEnhance.Brightness(x).enhance(1.1)),
        ('中心裁剪98%', lambda x: center_crop(x, 0.98)),
    ]

    all_probs = []
    start = time.time()

    for name, aug_func in augmentations:
        aug_img = aug_func(image)

        # 预处理
        resized = aug_img.resize((256, 256), Image.LANCZOS)
        cropped = resized.crop((16, 16, 240, 240))

        arr = np.array(cropped)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        normalized = (bgr / 255.0 - np.array([0.406, 0.456, 0.485])) / np.array([0.225, 0.224, 0.229])
        tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

        # 推理 + 温度锐化
        with torch.no_grad():
            logits = model(tensor)[0]

        probs = torch.nn.functional.softmax(logits / 0.6, dim=0).numpy()
        all_probs.append(probs)

    # 平均
    avg_probs = np.mean(all_probs, axis=0)

    elapsed = time.time() - start
    print(f"⏱️  总时间: {elapsed:.3f}秒 (6次推理)")

    # 提取结果
    results = _extract_results(avg_probs, bird_info, db_manager, ebird_species, top_k=10)

    _print_results(results, "TTA + 温度锐化")

    return results


def _combined_strategy(image: Image.Image, model, bird_info: List,
                      db_manager, ebird_species: set) -> List[Dict]:
    """
    策略3: 组合策略
    优点: 最高准确性
    """
    print("🟡 策略: 组合 (TTA + 多尺度 + 温度锐化)")

    scales = [224, 256, 288]
    augmentations = [
        lambda x: x,
        lambda x: x.transpose(Image.FLIP_LEFT_RIGHT),
        lambda x: x.filter(ImageFilter.SHARPEN),
    ]

    all_probs = []
    start = time.time()

    for scale in scales:
        for aug_func in augmentations:
            aug_img = aug_func(image)

            # 预处理到指定尺寸
            resized = aug_img.resize((scale, scale), Image.LANCZOS)

            arr = np.array(resized)
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            normalized = (bgr / 255.0 - np.array([0.406, 0.456, 0.485])) / np.array([0.225, 0.224, 0.229])
            tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

            # 推理
            with torch.no_grad():
                logits = model(tensor)[0]

            probs = torch.nn.functional.softmax(logits / 0.6, dim=0).numpy()
            all_probs.append(probs)

    # 加权平均 (大尺寸权重更高)
    weights = np.repeat([1.0, 1.1, 1.2], 3)  # 每个尺寸3种增强
    weights = weights / weights.sum()

    avg_probs = np.average(all_probs, axis=0, weights=weights)

    elapsed = time.time() - start
    print(f"⏱️  总时间: {elapsed:.3f}秒 (9次推理)")

    # 提取结果
    results = _extract_results(avg_probs, bird_info, db_manager, ebird_species, top_k=10)

    _print_results(results, "组合策略")

    return results


def _extract_results(probs: np.ndarray, bird_info: List, db_manager,
                    ebird_species: set, top_k: int = 10) -> List[Dict]:
    """提取并处理结果"""
    top_indices = np.argsort(probs)[-top_k:][::-1]

    results = []
    for idx in top_indices:
        if idx >= len(bird_info) or len(bird_info[idx]) < 2:
            continue

        cn_name = bird_info[idx][0]
        en_name = bird_info[idx][1]
        conf = probs[idx] * 100

        # eBird匹配
        ebird_match = False
        ebird_boost = 1.0

        if ebird_species and db_manager:
            ebird_code = db_manager.get_ebird_code_by_english_name(en_name)
            if ebird_code and ebird_code in ebird_species:
                ebird_match = True
                ebird_boost = 1.3  # 30%提升
                conf *= ebird_boost

        results.append({
            'class_id': int(idx),
            'confidence': conf,
            'original_confidence': probs[idx] * 100,
            'chinese_name': cn_name,
            'english_name': en_name,
            'ebird_match': ebird_match
        })

    # 重新排序
    results.sort(key=lambda x: x['confidence'], reverse=True)

    return results


def _print_results(results: List[Dict], method_name: str):
    """打印结果"""
    print()
    print("="*60)
    print(f"📊 识别结果 ({method_name})")
    print("="*60)

    for i, r in enumerate(results[:5], 1):
        ebird_tag = " 🌍" if r['ebird_match'] else ""
        print(f"{i}. {r['chinese_name']} ({r['english_name']})")
        print(f"   置信度: {r['confidence']:.2f}%{ebird_tag}")


def center_crop(img: Image.Image, ratio: float) -> Image.Image:
    """中心裁剪"""
    w, h = img.size
    new_w, new_h = int(w * ratio), int(h * ratio)
    left = (w - new_w) // 2
    top = (h - new_h) // 2
    return img.crop((left, top, left + new_w, top + new_h))


def compare_all_strategies(image_path: str, ebird_country: str = 'australia'):
    """对比所有策略"""
    print("\n" + "="*60)
    print("🔬 完整策略对比测试")
    print("="*60 + "\n")

    strategies = [
        ('sharp', '温度锐化'),
        ('tta', 'TTA增强'),
        ('both', '组合策略')
    ]

    all_results = {}

    for strategy_key, strategy_name in strategies:
        print(f"\n{'='*60}")
        print(f"测试策略: {strategy_name}")
        print(f"{'='*60}\n")

        results = boost_confidence_correct(image_path, strategy=strategy_key,
                                          ebird_country=ebird_country)
        all_results[strategy_name] = results

        print()

    # 打印对比表
    print("\n" + "="*60)
    print("📊 策略对比总结")
    print("="*60)
    print(f"{'策略':<15} {'Top-1置信度':<15} {'Top-1识别'}")
    print("-"*60)

    for name, results in all_results.items():
        if results:
            top1 = results[0]
            print(f"{name:<15} {top1['confidence']:>6.2f}%        {top1['chinese_name']}")

    print("="*60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  单策略: python correct_confidence_boost.py <图片> [策略] [国家]")
        print("  对比:   python correct_confidence_boost.py --compare <图片> [国家]")
        print()
        print("策略: sharp (快速), tta (稳定), both (最佳)")
        print()
        print("示例:")
        print("  python correct_confidence_boost.py bird.jpg sharp australia")
        print("  python correct_confidence_boost.py --compare bird.jpg")
        sys.exit(1)

    if sys.argv[1] == '--compare':
        img_path = sys.argv[2]
        country = sys.argv[3] if len(sys.argv) > 3 else 'australia'
        compare_all_strategies(img_path, country)
    else:
        img_path = sys.argv[1]
        strategy = sys.argv[2] if len(sys.argv) > 2 else 'sharp'
        country = sys.argv[3] if len(sys.argv) > 3 else 'australia'
        boost_confidence_correct(img_path, strategy, country)
