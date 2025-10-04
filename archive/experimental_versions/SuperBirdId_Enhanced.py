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

def get_crop_candidates(image, crop_size=224):
    """生成裁剪候选区域"""
    resize_size = 256
    resized_image = image.resize((resize_size, resize_size), Image.LANCZOS)
    
    crops = []
    crop_names = []
    
    # 五个裁剪位置：四角 + 中心
    positions = [
        (0, 0, "top_left"),
        (resize_size - crop_size, 0, "top_right"),
        (0, resize_size - crop_size, "bottom_left"),
        (resize_size - crop_size, resize_size - crop_size, "bottom_right"),
        ((resize_size - crop_size) // 2, (resize_size - crop_size) // 2, "center")
    ]
    
    for x, y, name in positions:
        crop = resized_image.crop((x, y, x + crop_size, y + crop_size))
        crops.append(crop)
        crop_names.append(name)
    
    return crops, crop_names

def run_single_inference(model, crop_image, bird_data):
    """对单个裁剪进行推理"""
    img_array = np.array(crop_image)
    bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # ImageNet标准化 (BGR格式)
    mean = np.array([0.406, 0.456, 0.485])  # BGR: B, G, R
    std = np.array([0.225, 0.224, 0.229])   # BGR: B, G, R
    
    normalized_array = (bgr_array / 255.0 - mean) / std
    input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()
    
    with torch.no_grad():
        output = model(input_tensor)
    
    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    return probabilities

def get_results_from_probabilities(probabilities, bird_data):
    """从概率向量提取识别结果"""
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
        
        results.append(f"  - Class ID: {class_id}, Confidence: {confidence:.2f}%, Name: {name}")
        count += 1
    
    return results if results else ["  - 无法识别 (所有结果置信度低于1%)"]

def run_enhanced_classification(model, image, bird_data, endemic_data, region_filter=None):
    """
    增强版本：图像增强 + 五点裁剪策略，自动选择最佳结果
    """
    enhancement_methods = [
        ("无增强", "none"),
        ("UnsharpMask增强", "unsharp_mask"),
        ("高对比度+边缘增强", "contrast_edge"),
        ("降低饱和度", "desaturate")
    ]
    
    best_confidence = 0
    best_strategy = ""
    best_results = []
    
    for method_name, method_key in enhancement_methods:
        # 应用图像增强
        if method_key == "none":
            enhanced_image = image
        else:
            enhanced_image = apply_enhancement(image, method_key)
        
        # 获取五点裁剪
        crops, crop_names = get_crop_candidates(enhanced_image)
        
        # 测试每个裁剪位置
        for crop, crop_name in zip(crops, crop_names):
            probabilities = run_single_inference(model, crop, bird_data)
            max_confidence = probabilities.max().item() * 100
            
            # 如果是当前最佳结果，则保存
            if max_confidence > best_confidence:
                best_confidence = max_confidence
                best_strategy = f"{method_name} + {crop_name}裁剪"
                best_results = get_results_from_probabilities(probabilities, bird_data)
        
        # 可选：尝试五点融合
        all_probabilities = []
        for crop in crops:
            prob = run_single_inference(model, crop, bird_data)
            all_probabilities.append(prob)
        
        # 融合结果
        fused_probabilities = torch.mean(torch.stack(all_probabilities), dim=0)
        fused_confidence = fused_probabilities.max().item() * 100
        
        if fused_confidence > best_confidence:
            best_confidence = fused_confidence
            best_strategy = f"{method_name} + 五点融合"
            best_results = get_results_from_probabilities(fused_probabilities, bird_data)
    
    # 只打印最终最佳结果
    print(f"=== 最佳组合结果 (Enhanced) ===")
    print(f"最佳策略: {best_strategy}")
    print(f"最高置信度: {best_confidence:.2f}%")
    print("识别结果:")
    for result in best_results:
        print(result)
    
    return best_confidence, best_strategy, best_results

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
    
    # 运行增强版识别
    run_enhanced_classification(
        classifier, original_image, bird_info, endemic_info, region_filter=12
    )