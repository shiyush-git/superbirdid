#!/usr/bin/env python3
"""
快速优化测试工具
对单张图像进行快速的关键优化对比测试
"""
import os
import sys
import time
import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2

# 导入原始模块
try:
    from SuperBirdId import lazy_load_classifier, lazy_load_bird_info
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在SuperBirdID目录中运行此脚本")
    sys.exit(1)

def preprocess_original(image):
    """原始预处理方法"""
    width, height = image.size
    max_dimension = max(width, height)

    if max_dimension < 1000:
        final_image = image.resize((224, 224), Image.LANCZOS)
        method = "原始-直接224"
    else:
        resized_256 = image.resize((256, 256), Image.LANCZOS)
        left = top = 16  # (256-224)//2
        final_image = resized_256.crop((left, top, left + 224, top + 224))
        method = "原始-256→224"

    return final_image, method

def preprocess_optimized(image):
    """优化预处理方法"""
    width, height = image.size
    aspect_ratio = width / height

    # 智能自适应预处理
    if 0.8 <= aspect_ratio <= 1.2:  # 接近正方形
        final_image = image.resize((224, 224), Image.LANCZOS)
        method = "优化-直接调整"
    elif aspect_ratio > 1.2:  # 宽图
        new_width = int(224 * aspect_ratio)
        resized = image.resize((new_width, 224), Image.LANCZOS)
        left = (new_width - 224) // 2
        final_image = resized.crop((left, 0, left + 224, 224))
        method = "优化-宽图裁剪"
    else:  # 高图
        new_height = int(224 / aspect_ratio)
        resized = image.resize((224, new_height), Image.LANCZOS)
        top = (new_height - 224) // 2
        final_image = resized.crop((0, top, 224, top + 224))
        method = "优化-高图裁剪"

    return final_image, method

def image_to_tensor(image):
    """图像转张量"""
    img_array = np.array(image)
    bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # ImageNet标准化 (BGR)
    mean = np.array([0.406, 0.456, 0.485])
    std = np.array([0.225, 0.224, 0.229])

    normalized_array = (bgr_array / 255.0 - mean) / std
    input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()

    return input_tensor

def apply_enhancement(image, method):
    """应用图像增强"""
    if method == "unsharp":
        return image.filter(ImageFilter.UnsharpMask())
    elif method == "contrast":
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(1.3)
    else:
        return image

def run_inference(model, input_tensor):
    """运行推理"""
    start_time = time.time()
    with torch.no_grad():
        output = model(input_tensor)
    inference_time = time.time() - start_time

    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    return probabilities, inference_time

def extract_top_results(probabilities, bird_info, threshold=1.0, top_k=3):
    """提取顶部结果"""
    k = min(len(probabilities), len(bird_info), 100)
    all_probs, all_catid = torch.topk(probabilities, k)

    results = []
    for i in range(min(top_k, all_probs.size(0))):
        class_id = all_catid[i].item()
        confidence = all_probs[i].item() * 100

        if confidence < threshold:
            break

        try:
            if class_id < len(bird_info) and len(bird_info[class_id]) >= 2:
                bird_name_cn = bird_info[class_id][0]
                bird_name_en = bird_info[class_id][1]

                results.append({
                    'rank': i + 1,
                    'confidence': confidence,
                    'chinese_name': bird_name_cn,
                    'english_name': bird_name_en
                })
        except:
            continue

    return results

def quick_test_image(image_path):
    """快速测试单张图像"""
    print(f"🔍 测试图像: {os.path.basename(image_path)}")

    # 加载组件
    print("正在加载模型...")
    model = lazy_load_classifier()
    bird_info = lazy_load_bird_info()

    # 加载图像
    try:
        original_image = Image.open(image_path).convert('RGB')
        print(f"图像尺寸: {original_image.size}")
    except Exception as e:
        print(f"❌ 图像加载失败: {e}")
        return

    # 测试配置
    test_configs = [
        ("原始", "无增强", "原始预处理", preprocess_original, "none"),
        ("优化1", "无增强", "优化预处理", preprocess_optimized, "none"),
        ("优化2", "锐化增强", "优化预处理", preprocess_optimized, "unsharp"),
        ("优化3", "对比度增强", "优化预处理", preprocess_optimized, "contrast"),
    ]

    results = []
    print(f"\n{'='*80}")

    for name, enh_desc, prep_desc, prep_func, enh_method in test_configs:
        print(f"\n🧪 {name}: {enh_desc} + {prep_desc}")

        try:
            # 图像增强
            enhanced_image = apply_enhancement(original_image, enh_method)

            # 预处理
            processed_image, method_detail = prep_func(enhanced_image)

            # 转换为张量
            input_tensor = image_to_tensor(processed_image)

            # 推理
            probabilities, inference_time = run_inference(model, input_tensor)

            # 提取结果
            top_results = extract_top_results(probabilities, bird_info, threshold=0.5, top_k=3)
            max_confidence = probabilities.max().item() * 100

            # 记录结果
            result = {
                'name': name,
                'method_detail': method_detail,
                'enhancement': enh_desc,
                'max_confidence': max_confidence,
                'inference_time': inference_time,
                'top_results': top_results
            }
            results.append(result)

            # 显示结果
            print(f"  ⏱️  推理时间: {inference_time:.3f}s")
            print(f"  📊 最高置信度: {max_confidence:.2f}%")
            print(f"  🎯 识别结果:")

            if top_results:
                for res in top_results:
                    print(f"    {res['rank']}. {res['chinese_name']} ({res['english_name']}) - {res['confidence']:.2f}%")
            else:
                print(f"    无结果 (置信度均低于0.5%)")

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            continue

    # 比较分析
    print(f"\n{'='*80}")
    print("📈 对比分析:")

    if len(results) >= 2:
        # 按最高置信度排序
        sorted_results = sorted(results, key=lambda x: x['max_confidence'], reverse=True)
        best = sorted_results[0]
        baseline = next((r for r in results if r['name'] == '原始'), results[0])

        print(f"\n🏆 最佳配置: {best['name']}")
        print(f"  方法: {best['enhancement']} + {best['method_detail']}")
        print(f"  最高置信度: {best['max_confidence']:.2f}%")
        print(f"  推理时间: {best['inference_time']:.3f}s")

        if baseline != best:
            confidence_improvement = best['max_confidence'] - baseline['max_confidence']
            time_change = best['inference_time'] - baseline['inference_time']

            print(f"\n📊 相对于原始方法的改进:")
            print(f"  置信度变化: {confidence_improvement:+.2f}%")
            print(f"  时间变化: {time_change:+.3f}s")

            if confidence_improvement > 2:
                print("  ✅ 置信度有明显提升")
            elif confidence_improvement > 0:
                print("  ↗️  置信度有轻微提升")
            else:
                print("  ⚠️  置信度无明显改善")

        # 速度分析
        fastest = min(results, key=lambda x: x['inference_time'])
        print(f"\n⚡ 最快配置: {fastest['name']}")
        print(f"  推理时间: {fastest['inference_time']:.3f}s")

        # 推荐
        print(f"\n💡 建议:")

        if best['name'] != '原始':
            print(f"  • 推荐使用 {best['name']} 配置以获得更好的识别率")

        if fastest != best and fastest['max_confidence'] > best['max_confidence'] * 0.95:
            print(f"  • 如需要更快速度，可考虑 {fastest['name']} 配置")

        # 检查是否有改进
        has_improvement = any(r['max_confidence'] > baseline['max_confidence'] + 1 for r in results if r != baseline)
        if has_improvement:
            print(f"  • 优化方法确实能提升识别效果")
        else:
            print(f"  • 当前图像下优化效果不明显，原始方法已足够")

    print(f"\n{'='*80}")

def main():
    """主函数"""
    print("🚀 SuperBirdID 快速优化测试")
    print("="*50)

    image_path = input("请输入图像文件路径: ").strip().strip("'\"")

    if not os.path.exists(image_path):
        print(f"❌ 图像文件不存在: {image_path}")
        return

    quick_test_image(image_path)

if __name__ == "__main__":
    main()