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

def get_five_crop_transforms(image, crop_size=224):
    """生成五点裁剪所需的图片列表"""
    # 首先resize到适当大小
    resize_size = 256  # 标准的resize尺寸
    resized_image = image.resize((resize_size, resize_size), Image.LANCZOS)
    
    crops = []
    crop_names = []
    
    # 定义五个裁剪位置
    crop_positions = [
        (0, 0, "top_left"),                                           # 左上角
        (resize_size - crop_size, 0, "top_right"),                  # 右上角  
        (0, resize_size - crop_size, "bottom_left"),                # 左下角
        (resize_size - crop_size, resize_size - crop_size, "bottom_right"), # 右下角
        ((resize_size - crop_size) // 2, (resize_size - crop_size) // 2, "center")  # 中心
    ]
    
    for x, y, name in crop_positions:
        crop = resized_image.crop((x, y, x + crop_size, y + crop_size))
        crops.append(crop)
        crop_names.append(name)
    
    return crops, crop_names

def run_single_crop_inference(model, crop_image, bird_data):
    """对单个裁剪进行推理"""
    # 转换为numpy数组
    img_array = np.array(crop_image)
    
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
    
    return probabilities

def run_five_crop_classification(model, image, bird_data, endemic_data, region_filter=None):
    """
    五点裁剪版本：四角裁剪 + 中心裁剪，融合结果
    """
    enhancement_methods = [
        ("无增强", "none"),
        ("UnsharpMask增强", "unsharp_mask"),
        ("高对比度+边缘增强", "contrast_edge"),
        ("降低饱和度", "desaturate")
    ]
    
    best_confidence = 0
    best_method = ""
    best_crop = ""
    best_results = []
    all_test_results = []
    
    print("\n=== 五点裁剪测试开始 ===")
    
    # 对每种增强方法进行测试
    for method_name, method_key in enhancement_methods:
        print(f"\n--- 测试增强方法: {method_name} ---")
        
        # 应用图像增强
        if method_key == "none":
            enhanced_image = image
        else:
            enhanced_image = apply_enhancement(image, method_key)
        
        # 获取五点裁剪
        crops, crop_names = get_five_crop_transforms(enhanced_image)
        
        # 方案A: 选择最佳裁剪
        crop_results = []
        for i, (crop, crop_name) in enumerate(zip(crops, crop_names)):
            probabilities = run_single_crop_inference(model, crop, bird_data)
            max_confidence = probabilities.max().item() * 100
            crop_results.append((crop_name, max_confidence, probabilities))
            print(f"  {crop_name:12}: 置信度 {max_confidence:.2f}%")
        
        # 找到当前增强方法下的最佳裁剪
        best_crop_for_method = max(crop_results, key=lambda x: x[1])
        current_crop, current_confidence, current_probs = best_crop_for_method
        
        # 方案B: 融合五点裁剪结果
        all_probabilities = [result[2] for result in crop_results]
        fused_probabilities = torch.mean(torch.stack(all_probabilities), dim=0)
        fused_confidence = fused_probabilities.max().item() * 100
        
        print(f"  最佳裁剪: {current_crop}, 置信度: {current_confidence:.2f}%")
        print(f"  融合结果: 置信度: {fused_confidence:.2f}%")
        
        # 选择更好的结果（最佳裁剪 vs 融合结果）
        if fused_confidence > current_confidence:
            final_confidence = fused_confidence
            final_probabilities = fused_probabilities
            strategy = f"{method_name} + 五点融合"
        else:
            final_confidence = current_confidence
            final_probabilities = current_probs
            strategy = f"{method_name} + {current_crop}裁剪"
        
        # 获取Top-5结果
        results = []
        k = min(len(final_probabilities), len(bird_data), 1000)
        all_probs, all_catid = torch.topk(final_probabilities, k)
        
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
        
        # 记录测试结果
        all_test_results.append({
            'method': method_name,
            'strategy': strategy,
            'confidence': final_confidence,
            'results': results
        })
        
        print(f"  最终选择: {strategy}, 置信度: {final_confidence:.2f}%")
        
        # 更新全局最佳结果
        if final_confidence > best_confidence:
            best_confidence = final_confidence
            best_method = strategy
            best_results = results
    
    # 打印详细的测试总结
    print(f"\n=== 五点裁剪测试总结 ===")
    for result in all_test_results:
        print(f"{result['method']:20} | {result['confidence']:6.2f}% | {result['strategy']}")
    
    # 打印最佳结果
    print(f"\n=== 最佳组合结果 ===")
    print(f"最佳策略: {best_method}")
    print(f"最高置信度: {best_confidence:.2f}%")
    print("识别结果:")
    
    if best_results:
        for result in best_results:
            print(f"  - Class ID: {result['class_id']}, Confidence: {result['confidence']:.2f}%, Name: {result['name']}")
    else:
        print("  - 无法识别 (所有结果置信度低于1%)")
    
    return best_confidence, best_method, best_results

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
    
    # 运行五点裁剪版本识别
    run_five_crop_classification(
        classifier, original_image, bird_info, endemic_info, region_filter=12
    )