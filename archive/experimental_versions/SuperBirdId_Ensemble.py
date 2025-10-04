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

def run_ensemble_classification(model, image, bird_data, endemic_data, region_filter=None):
    """
    Ensemble版本：融合多种图像增强策略的预测结果
    """
    enhancement_methods = [
        ("无增强", "none"),
        ("UnsharpMask增强", "unsharp_mask"),
        ("高对比度+边缘增强", "contrast_edge"),
        ("降低饱和度", "desaturate")
    ]
    
    all_probabilities = []
    
    for method_name, method_key in enhancement_methods:
        # 1. 应用图像增强
        if method_key == "none":
            enhanced_image = image
        else:
            enhanced_image = apply_enhancement(image, method_key)
        
        # 2. 标准预处理 (中心裁剪)
        input_size = 224
        resized_image = enhanced_image.resize((256, 256), Image.LANCZOS)
        left = (256 - input_size) // 2
        top = (256 - input_size) // 2
        final_image = resized_image.crop((left, top, left + input_size, top + input_size))
        
        img_array = np.array(final_image)
        bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        mean = np.array([0.406, 0.456, 0.485])  # BGR: B, G, R
        std = np.array([0.225, 0.224, 0.229])   # BGR: B, G, R
        
        normalized_array = (bgr_array / 255.0 - mean) / std
        input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()
        
        # 3. 推理并收集概率
        with torch.no_grad():
            output = model(input_tensor)
        
        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        all_probabilities.append(probabilities)

    # 4. 融合所有概率向量
    if not all_probabilities:
        print("没有有效的预测结果可以融合。")
        return 0, "N/A", ["无法识别"]

    mean_probabilities = torch.mean(torch.stack(all_probabilities), dim=0)
    
    # 5. 从融合后的结果中提取信息
    best_confidence = mean_probabilities.max().item() * 100
    
    results = []
    k = min(len(mean_probabilities), len(bird_data), 1000)
    all_probs, all_catid = torch.topk(mean_probabilities, k)
    
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
    
    final_results = results if results else ["  - 无法识别 (所有结果置信度低于1%)"]

    # 6. 打印最终结果
    print(f"=== 最佳组合结果 (Enhancement Ensemble) ===")
    print(f"融合策略: 平均全部4种增强方法的预测概率")
    print(f"最高置信度: {best_confidence:.2f}%")
    print("识别结果:")
    for result in final_results:
        print(result)
    
    return best_confidence, "Ensemble", final_results

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
    
    # 运行Ensemble版本识别
    run_ensemble_classification(
        classifier, original_image, bird_info, endemic_info, region_filter=12
    )

