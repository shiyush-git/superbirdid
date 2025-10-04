import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import json
import cv2

import os

# --- 获取脚本所在目录 ---
script_dir = os.path.dirname(os.path.abspath(__file__))

# --- 加载模型和数据 ---
PYTORCH_CLASSIFICATION_MODEL_PATH = os.path.join(script_dir, 'birdid2024.pt')
BIRD_INFO_PATH = os.path.join(script_dir, 'birdinfo.json')
ENDEMIC_PATH = os.path.join(script_dir, 'endemic.json')

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

except Exception as e:
    print(f"Error loading files: {e}")
    exit()

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

def preprocess_image_for_scale(image, input_size):
    """为指定尺寸预处理图像"""
    # 计算resize的目标尺寸，保持长宽比
    resize_size = int(input_size * 256 / 224)  # 按比例缩放
    
    # Resize图像
    resized_image = image.resize((resize_size, resize_size), Image.LANCZOS)
    
    # 中心裁剪到目标尺寸
    left = (resize_size - input_size) // 2
    top = (resize_size - input_size) // 2
    final_image = resized_image.crop((left, top, left + input_size, top + input_size))
    
    return final_image

def run_single_scale_inference(model, image, bird_data, input_size):
    """对单个尺寸进行推理"""
    # 预处理到指定尺寸
    processed_image = preprocess_image_for_scale(image, input_size)
    
    # 转换为numpy数组
    img_array = np.array(processed_image)
    
    # 转换为BGR通道顺序
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
    max_confidence = probabilities.max().item() * 100
    
    # 获取Top-5结果
    results = []
    k = min(len(probabilities), len(bird_data), 1000)
    all_probs, all_catid = torch.topk(probabilities, k)
    
    count = 0
    for i in range(all_probs.size(0)):
        if count >= 5:
            break
        
        class_id = all_catid[i].item()
        confidence = all_probs[i].item() * 100
        
        if confidence < 1.0:
            continue
        
        try:
            if class_id < len(bird_data) and len(bird_data[class_id]) >= 2:
                bird_name_cn = bird_data[class_id][0]
                bird_name_en = bird_data[class_id][1]
                name = f"{bird_name_cn} ({bird_name_en})"
            else:
                name = f"Unknown (ID: {class_id})"
        except (IndexError, TypeError):
            name = f"Unknown (ID: {class_id})"
        
        results.append({
            'class_id': class_id,
            'confidence': confidence,
            'name': name
        })
        count += 1
    
    return max_confidence, results

def run_multi_scale_classification(model, image, bird_data, endemic_data, region_filter=None):
    """
    多尺度版本：测试多种输入尺寸，选择最佳结果
    """
    # 定义测试的输入尺寸
    scales = [224, 256, 288]  # 由小到大
    
    # 增强方法
    enhancement_methods = [
        ("无增强", "none"),
        ("UnsharpMask增强", "unsharp_mask"),
        ("高对比度+边缘增强", "contrast_edge"),
        ("降低饱和度", "desaturate")
    ]
    
    best_confidence = 0
    best_method = ""
    best_scale = 0
    best_results = []
    all_test_results = []
    
    print("\n=== 多尺度测试开始 ===")
    
    # 对每种增强方法进行测试
    for method_name, method_key in enhancement_methods:
        print(f"\n--- 测试增强方法: {method_name} ---")
        
        # 应用图像增强
        if method_key == "none":
            enhanced_image = image
        else:
            enhanced_image = apply_enhancement(image, method_key)
        
        # 对每个尺度进行测试
        scale_results = []
        for scale in scales:
            confidence, results = run_single_scale_inference(model, enhanced_image, bird_data, scale)
            scale_results.append((scale, confidence, results))
            print(f"  尺寸 {scale}x{scale}: 最高置信度 {confidence:.2f}%")
        
        # 找到当前增强方法下的最佳尺度
        best_scale_for_method = max(scale_results, key=lambda x: x[1])
        current_scale, current_confidence, current_results = best_scale_for_method
        
        # 记录测试结果
        all_test_results.append({
            'method': method_name,
            'scale': current_scale,
            'confidence': current_confidence,
            'results': current_results
        })
        
        print(f"  {method_name} 最佳: {current_scale}x{current_scale}, 置信度: {current_confidence:.2f}%")
        
        # 更新全局最佳结果
        if current_confidence > best_confidence:
            best_confidence = current_confidence
            best_method = method_name
            best_scale = current_scale
            best_results = current_results
    
    # 打印详细的测试总结
    print(f"\n=== 多尺度测试总结 ===")
    for result in all_test_results:
        print(f"{result['method']:20} | {result['scale']}x{result['scale']} | {result['confidence']:6.2f}%")
    
    # 打印最佳结果
    print(f"\n=== 最佳组合结果 ===")
    print(f"最佳方法: {best_method}")
    print(f"最佳尺寸: {best_scale}x{best_scale}")
    print(f"最高置信度: {best_confidence:.2f}%")
    print("识别结果:")
    
    if best_results:
        for result in best_results:
            print(f"  - Class ID: {result['class_id']}, Confidence: {result['confidence']:.2f}%, Name: {result['name']}")
    else:
        print("  - 无法识别 (所有结果置信度低于1%)")
    
    return best_confidence, best_method, best_scale, best_results

# --- 主程序 ---
if __name__ == "__main__":
    image_path = input("请输入图片文件的完整路径: ")
    try:
        original_image = Image.open(image_path).convert("RGB")
    except FileNotFoundError:
        print(f"错误: 文件未找到, 请检查路径 '{image_path}' 是否正确。")
        exit()
    except Exception as e:
        print(f"加载图片时发生错误: {e}")
        exit()
    
    # 运行多尺度版本识别
    run_multi_scale_classification(
        classifier, original_image, bird_info, endemic_info, region_filter=12
    )