import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import json
import cv2
import os

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 加载模型和数据
PYTORCH_CLASSIFICATION_MODEL_PATH = os.path.join(script_dir, 'birdid2024.pt')
BIRD_INFO_PATH = os.path.join(script_dir, 'birdinfo.json')

try:
    classifier = torch.jit.load(PYTORCH_CLASSIFICATION_MODEL_PATH)
    classifier.eval()
    
    with open(BIRD_INFO_PATH, 'r') as f:
        bird_info = json.load(f)
    print("模型和数据加载成功")
except Exception as e:
    print(f"加载失败: {e}")
    exit()

def preprocess_traditional(image):
    """传统方法: 256x256 → 中心裁剪224x224"""
    input_size = 224
    # 步骤1: 拉伸到256x256
    resized_image = image.resize((256, 256), Image.LANCZOS)
    
    # 步骤2: 中心裁剪到224x224
    left = (256 - input_size) // 2
    top = (256 - input_size) // 2
    final_image = resized_image.crop((left, top, left + input_size, top + input_size))
    
    return final_image

def preprocess_direct(image):
    """直接方法: 直接拉伸到224x224"""
    input_size = 224
    # 一步到位: 直接拉伸到224x224
    final_image = image.resize((input_size, input_size), Image.LANCZOS)
    
    return final_image

def preprocess_direct_pad(image):
    """直接填充方法: 保持比例填充到224x224"""
    input_size = 224
    
    # 计算原图的宽高比
    width, height = image.size
    max_side = max(width, height)
    
    # 创建正方形画布
    square_image = Image.new('RGB', (max_side, max_side), (255, 255, 255))
    
    # 计算居中位置
    x_offset = (max_side - width) // 2
    y_offset = (max_side - height) // 2
    
    # 将原图粘贴到正方形画布中心
    square_image.paste(image, (x_offset, y_offset))
    
    # 直接调整到224x224
    final_image = square_image.resize((input_size, input_size), Image.LANCZOS)
    
    return final_image

def run_classification_with_method(model, image, bird_data, method):
    """使用指定方法进行分类"""
    
    # 选择预处理方法
    if method == "traditional":
        processed_image = preprocess_traditional(image)
        method_name = "传统方法 (256→224)"
    elif method == "direct":
        processed_image = preprocess_direct(image)
        method_name = "直接方法 (直接224)"
    elif method == "direct_pad":
        processed_image = preprocess_direct_pad(image)
        method_name = "直接填充 (保比例224)"
    
    # 转换为numpy数组
    img_array = np.array(processed_image)
    
    # 转换为BGR通道顺序
    bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # ImageNet标准化 (BGR格式)
    mean = np.array([0.406, 0.456, 0.485])
    std = np.array([0.225, 0.224, 0.229])
    
    normalized_array = (bgr_array / 255.0 - mean) / std
    input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()
    
    # 推理
    with torch.no_grad():
        output = model(input_tensor)
    
    probabilities = torch.nn.functional.softmax(output[0], dim=0)
    max_confidence = probabilities.max().item() * 100
    
    # 获取前3个结果
    results = []
    k = min(len(probabilities), len(bird_data), 3)
    all_probs, all_catid = torch.topk(probabilities, k)
    
    for i in range(all_probs.size(0)):
        class_id = all_catid[i].item()
        confidence = all_probs[i].item() * 100
        
        if confidence < 0.5:
            continue
            
        try:
            if class_id < len(bird_data) and len(bird_data[class_id]) >= 2:
                bird_name_cn = bird_data[class_id][0]
                bird_name_en = bird_data[class_id][1]
                name = f"{bird_name_cn} ({bird_name_en})"
            else:
                name = f"Unknown (ID: {class_id})"
            
            results.append({
                'class_id': class_id,
                'confidence': confidence,
                'name': name
            })
        except:
            pass
    
    return method_name, max_confidence, results

def compare_resize_methods(image_path):
    """比较不同调整尺寸方法的效果"""
    try:
        original_image = Image.open(image_path).convert("RGB")
        print(f"原图尺寸: {original_image.size}")
    except Exception as e:
        print(f"加载图片失败: {e}")
        return
    
    print(f"\n=== 图像尺寸调整方法对比 ===")
    print(f"测试图像: {image_path}")
    
    methods = ["traditional", "direct", "direct_pad"]
    
    for method in methods:
        print(f"\n--- {method.upper()} ---")
        method_name, max_confidence, results = run_classification_with_method(
            classifier, original_image, bird_info, method
        )
        
        print(f"方法: {method_name}")
        print(f"最高置信度: {max_confidence:.2f}%")
        print("识别结果:")
        
        if results:
            for i, result in enumerate(results):
                print(f"  {i+1}. {result['name']} - {result['confidence']:.2f}%")
        else:
            print("  无有效识别结果")

if __name__ == "__main__":
    image_path = input("请输入图片路径: ")
    compare_resize_methods(image_path)