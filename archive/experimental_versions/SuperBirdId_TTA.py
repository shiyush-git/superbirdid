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

def get_ten_crop_transforms(image, crop_size=224):
    """生成10-crop所需的图片列表"""
    resized_image = image.resize((256, 256), Image.LANCZOS)
    flipped_image = resized_image.transpose(Image.FLIP_LEFT_RIGHT)

    crops = []
    crop_positions = [
        (0, 0),  # Top-left
        (256 - crop_size, 0),  # Top-right
        (0, 256 - crop_size),  # Bottom-left
        (256 - crop_size, 256 - crop_size),  # Bottom-right
        ((256 - crop_size) // 2, (256 - crop_size) // 2)  # Center
    ]

    for img in [resized_image, flipped_image]:
        for x, y in crop_positions:
            crop = img.crop((x, y, x + crop_size, y + crop_size))
            crops.append(crop)
    return crops

def run_tta_classification(model, image, bird_data, endemic_data, region_filter=None):
    """
    TTA版本：10-crop + BGR格式 + 图像增强 + 区域筛选
    """
    enhancement_methods = [
        ("无增强", "none"),
        ("UnsharpMask增强", "unsharp_mask"),
        ("高对比度+边缘增强", "contrast_edge"),
        ("降低饱和度", "desaturate")
    ]
    
    best_confidence = 0
    best_method = ""
    best_results = []
    
    for method_name, method_key in enhancement_methods:
        # 1. 应用图像增强
        if method_key == "none":
            enhanced_image = image
        else:
            enhanced_image = apply_enhancement(image, method_key)

        # 2. 获取10-crop图片
        cropped_images = get_ten_crop_transforms(enhanced_image)
        
        all_probabilities = []
        
        # 3. 对10张图片分别进行推理
        for crop in cropped_images:
            img_array = np.array(crop)
            bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            mean = np.array([0.406, 0.456, 0.485])  # BGR: B, G, R
            std = np.array([0.225, 0.224, 0.229])   # BGR: B, G, R
            
            normalized_array = (bgr_array / 255.0 - mean) / std
            input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()
            
            with torch.no_grad():
                output = model(input_tensor)
            
            probabilities = torch.nn.functional.softmax(output[0], dim=0)
            all_probabilities.append(probabilities)

        # 4. 平均10次预测的概率
        mean_probabilities = torch.mean(torch.stack(all_probabilities), dim=0)
        max_confidence = mean_probabilities.max().item() * 100

        # 5. 如果是当前最佳结果，则保存
        if max_confidence > best_confidence:
            best_confidence = max_confidence
            best_method = method_name
            
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
            
            best_results = results if results else ["  - 无法识别 (所有结果置信度低于1%)"]

    # 只在最后打印最佳结果
    print(f"=== 最佳组合结果 (TTA 10-Crop) ===")
    print(f"最佳方法: {best_method} + BGR格式 + 置信度筛选")
    print(f"最高置信度: {best_confidence:.2f}%")
    print("识别结果:")
    for result in best_results:
        print(result)
    
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
    
    # 运行TTA版本识别
    run_tta_classification(
        classifier, original_image, bird_info, endemic_info, region_filter=12
    )
