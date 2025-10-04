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

def build_australia_bird_set(endemic_data):
    """构建澳洲鸟类集合"""
    australia_birds = set()
    
    # 从endemic数据中找出澳洲地区的鸟类
    # 通过测试发现12是澳洲的region code
    AUSTRALIA_REGION_CODE = 12
    
    for class_id, region_code in endemic_data.items():
        if region_code == AUSTRALIA_REGION_CODE:
            australia_birds.add(int(class_id))
    
    print(f"Found {len(australia_birds)} birds endemic to Australia")
    return australia_birds

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

def filter_results_by_region(probabilities, bird_data, australia_birds, confidence_threshold=1.0):
    """按地域过滤识别结果"""
    results = []
    k = min(len(probabilities), len(bird_data), 1000)
    all_probs, all_catid = torch.topk(probabilities, k)
    
    # 分别收集澳洲鸟类和非澳洲鸟类结果
    australia_results = []
    other_results = []
    
    for i in range(all_probs.size(0)):
        class_id = all_catid[i].item()
        confidence = all_probs[i].item() * 100
        
        if confidence < confidence_threshold:
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
        
        result_info = {
            'class_id': class_id,
            'confidence': confidence,
            'name': name,
            'is_australia': class_id in australia_birds
        }
        
        if class_id in australia_birds:
            australia_results.append(result_info)
        else:
            other_results.append(result_info)
    
    return australia_results, other_results

def run_australia_classification(model, image, bird_data, endemic_data, region_filter=None):
    """
    澳洲地域过滤版本：优先显示澳洲鸟类，但也显示其他结果供参考
    """
    # 构建澳洲鸟类集合
    australia_birds = build_australia_bird_set(endemic_data)
    
    enhancement_methods = [
        ("无增强", "none"),
        ("UnsharpMask增强", "unsharp_mask"),
        ("高对比度+边缘增强", "contrast_edge"),
        ("降低饱和度", "desaturate")
    ]
    
    best_confidence = 0
    best_strategy = ""
    best_australia_results = []
    best_other_results = []
    
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
            
            # 按地域过滤结果
            australia_results, other_results = filter_results_by_region(
                probabilities, bird_data, australia_birds
            )
            
            # 如果是当前最佳结果，则保存
            if max_confidence > best_confidence:
                best_confidence = max_confidence
                best_strategy = f"{method_name} + {crop_name}裁剪"
                best_australia_results = australia_results[:5]  # Top 5 澳洲鸟类
                best_other_results = other_results[:3]           # Top 3 其他地区鸟类
        
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
            
            australia_results, other_results = filter_results_by_region(
                fused_probabilities, bird_data, australia_birds
            )
            best_australia_results = australia_results[:5]
            best_other_results = other_results[:3]
    
    # 打印结果
    print(f"=== 最佳组合结果 (Australia Regional Filter) ===")
    print(f"最佳策略: {best_strategy}")
    print(f"最高置信度: {best_confidence:.2f}%")
    
    # 优先显示澳洲鸟类
    if best_australia_results:
        print("\n🇦🇺 澳洲鸟类识别结果:")
        for result in best_australia_results:
            print(f"  ✅ Class ID: {result['class_id']}, Confidence: {result['confidence']:.2f}%, Name: {result['name']}")
    else:
        print("\n🇦🇺 未识别到澳洲鸟类")
    
    # 显示其他地区鸟类供参考
    if best_other_results:
        print("\n🌍 其他地区鸟类 (仅供参考):")
        for result in best_other_results:
            print(f"  ⚠️  Class ID: {result['class_id']}, Confidence: {result['confidence']:.2f}%, Name: {result['name']}")
    
    return best_confidence, best_strategy, best_australia_results, best_other_results

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
    
    # 运行澳洲地域过滤版识别
    run_australia_classification(
        classifier, original_image, bird_info, endemic_info, region_filter=12
    )