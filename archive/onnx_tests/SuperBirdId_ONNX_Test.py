import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import json
import cv2
import csv
import os
import time

# 检查并安装onnxruntime
try:
    import onnxruntime as ort
    print("✅ ONNX Runtime available")
except ImportError:
    print("❌ ONNX Runtime not found. Please install it:")
    print("pip install onnxruntime")
    exit()

# --- 获取脚本所在目录 ---
script_dir = os.path.dirname(os.path.abspath(__file__))

# --- 地理区域识别配置 ---
GEOGRAPHIC_REGIONS = {
    'Australia': ['australian', 'australasian', 'new zealand'],
    'Africa': ['african', 'south african'],
    'Europe': ['european', 'eurasian', 'scandinavian', 'caucasian'],
    'Asia': ['asian', 'indian', 'siberian', 'himalayan', 'chinese', 'ryukyu', 'oriental'],
    'North_America': ['american', 'canadian', 'north american'],
    'South_America': ['brazilian', 'patagonian', 'south american', 'west indian'],
    'Pacific': ['pacific'],
    'Arctic': ['arctic']
}

# --- 模型路径 ---
ONNX_MODEL_PATH = os.path.join(script_dir, 'classify_bird_11144.onnx')
PYTORCH_MODEL_PATH = os.path.join(script_dir, 'birdid2024.pt')
BIRD_INFO_PATH = os.path.join(script_dir, 'birdinfo.json')
ENDEMIC_PATH = os.path.join(script_dir, 'endemic.json')
LABELMAP_PATH = os.path.join(script_dir, 'labelmap.csv')

try:
    # 加载ONNX模型
    if os.path.exists(ONNX_MODEL_PATH):
        onnx_session = ort.InferenceSession(ONNX_MODEL_PATH)
        
        # 获取所有输入输出信息
        inputs = onnx_session.get_inputs()
        outputs = onnx_session.get_outputs()
        
        print(f"✅ ONNX model loaded successfully")
        print(f"📊 模型架构详情:")
        
        for i, input_info in enumerate(inputs):
            print(f"   输入{i}: name='{input_info.name}', shape={input_info.shape}, type={input_info.type}")
        
        for i, output_info in enumerate(outputs):
            print(f"   输出{i}: name='{output_info.name}', shape={output_info.shape}, type={output_info.type}")
        
        input_name = inputs[0].name
        output_name = outputs[0].name
        input_shape = inputs[0].shape
        
    else:
        print(f"❌ ONNX model not found at {ONNX_MODEL_PATH}")
        exit()

    # 加载PyTorch模型（用于对比）
    try:
        import torch
        if os.path.exists(PYTORCH_MODEL_PATH):
            pytorch_model = torch.jit.load(PYTORCH_MODEL_PATH)
            pytorch_model.eval()
            print("✅ PyTorch model loaded for comparison")
        else:
            pytorch_model = None
            print("⚠️ PyTorch model not found, comparison disabled")
    except ImportError:
        pytorch_model = None
        print("⚠️ PyTorch not available, comparison disabled")

    # 加载其他数据文件
    with open(BIRD_INFO_PATH, 'r') as f:
        bird_info = json.load(f)
    print("✅ Bird info loaded")

    with open(ENDEMIC_PATH, 'r') as f:
        endemic_info = json.load(f)
    print("✅ Endemic info loaded")
    
    # 加载labelmap.csv
    labelmap_data = {}
    if os.path.exists(LABELMAP_PATH):
        with open(LABELMAP_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if len(row) >= 2:
                    try:
                        class_id = int(row[0])
                        name = row[1]
                        labelmap_data[class_id] = name
                    except ValueError:
                        continue
        print(f"✅ Label map loaded: {len(labelmap_data)} entries")

except Exception as e:
    print(f"❌ Error loading files: {e}")
    exit()

def get_bird_region(species_name):
    """根据鸟类名称推断地理区域"""
    if not species_name:
        return 'Unknown'
    
    species_lower = species_name.lower()
    
    for region, keywords in GEOGRAPHIC_REGIONS.items():
        for keyword in keywords:
            if keyword in species_lower:
                return region
    
    return 'Unknown'

def calculate_regional_confidence_boost(species_name, user_region=None):
    """计算地理区域置信度调整系数"""
    if not user_region or not species_name:
        return 1.0
    
    bird_region = get_bird_region(species_name)
    
    if bird_region == user_region:
        return 1.5  # 本区域物种置信度提升50%
    elif bird_region != 'Unknown':
        return 0.8  # 其他区域物种置信度降低20%
    else:
        return 1.0  # 未知区域物种不调整

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
        return enhancer.enhance(0.5)
    else:
        return image

def preprocess_image_rgb(image, target_size=300):
    """RGB格式预处理（可能适用于ONNX模型）"""
    # 应用最佳增强
    enhanced_image = apply_enhancement(image, "unsharp_mask")
    
    # 调整尺寸
    resize_size = max(320, target_size + 20)
    resized_image = enhanced_image.resize((resize_size, resize_size), Image.LANCZOS)
    
    left = (resize_size - target_size) // 2
    top = (resize_size - target_size) // 2
    final_image = resized_image.crop((left, top, left + target_size, top + target_size))
    
    # 转换为numpy数组 (保持RGB格式)
    img_array = np.array(final_image)
    
    # ImageNet标准化 (RGB格式)
    mean = np.array([0.485, 0.456, 0.406])  # RGB: R, G, B
    std = np.array([0.229, 0.224, 0.225])   # RGB: R, G, B
    
    normalized_array = (img_array / 255.0 - mean) / std
    
    return normalized_array

def preprocess_image_simple(image, target_size=300):
    """简单预处理（只做resize和归一化）"""
    # 简单resize
    resized_image = image.resize((target_size, target_size), Image.LANCZOS)
    
    # 转换为numpy数组
    img_array = np.array(resized_image)
    
    # 简单归一化到[0,1]
    normalized_array = img_array / 255.0
    
    return normalized_array

def preprocess_image(image, target_size=300, for_pytorch=False, method="bgr"):
    """预处理图像 - 支持多种方法"""
    if for_pytorch:
        # PyTorch使用BGR方法
        target_size = 224
        resize_size = 256
        
        enhanced_image = apply_enhancement(image, "unsharp_mask")
        resized_image = enhanced_image.resize((resize_size, resize_size), Image.LANCZOS)
        
        left = (resize_size - target_size) // 2
        top = (resize_size - target_size) // 2
        final_image = resized_image.crop((left, top, left + target_size, top + target_size))
        
        img_array = np.array(final_image)
        bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        mean = np.array([0.406, 0.456, 0.485])  # BGR
        std = np.array([0.225, 0.224, 0.229])   # BGR
        
        normalized_array = (bgr_array / 255.0 - mean) / std
        return normalized_array
    else:
        # ONNX模型尝试不同方法
        if method == "rgb":
            return preprocess_image_rgb(image, target_size)
        elif method == "simple":
            return preprocess_image_simple(image, target_size)
        else:  # "bgr"
            enhanced_image = apply_enhancement(image, "unsharp_mask")
            resize_size = max(320, target_size + 20)
            resized_image = enhanced_image.resize((resize_size, resize_size), Image.LANCZOS)
            
            left = (resize_size - target_size) // 2
            top = (resize_size - target_size) // 2
            final_image = resized_image.crop((left, top, left + target_size, top + target_size))
            
            img_array = np.array(final_image)
            bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            mean = np.array([0.406, 0.456, 0.485])  # BGR
            std = np.array([0.225, 0.224, 0.229])   # BGR
            
            normalized_array = (bgr_array / 255.0 - mean) / std
            return normalized_array

def run_onnx_inference(session, input_name, preprocessed_image):
    """运行ONNX推理"""
    # 添加batch维度并转换为float32
    input_tensor = np.expand_dims(preprocessed_image.transpose(2, 0, 1), axis=0).astype(np.float32)
    
    start_time = time.time()
    outputs = session.run(None, {input_name: input_tensor})
    inference_time = time.time() - start_time
    
    # 检查输出形状
    print(f"🔍 ONNX模型输出形状: {outputs[0].shape}")
    
    return outputs[0], inference_time

def run_pytorch_inference(model, preprocessed_image):
    """运行PyTorch推理"""
    if model is None:
        return None, 0
    
    import torch
    input_tensor = torch.from_numpy(preprocessed_image).permute(2, 0, 1).unsqueeze(0).float()
    
    start_time = time.time()
    with torch.no_grad():
        output = model(input_tensor)
    inference_time = time.time() - start_time
    
    return output[0].numpy(), inference_time

def softmax(x):
    """计算softmax"""
    exp_x = np.exp(x - np.max(x))
    return exp_x / np.sum(exp_x)

def process_results(logits, bird_data, user_region=None, model_name="Model"):
    """处理识别结果"""
    # 确保logits是1维数组
    if len(logits.shape) > 1:
        logits = logits.flatten()
    
    probabilities = softmax(logits)
    print(f"🔍 {model_name} 输出类别数: {len(probabilities)}, bird_data长度: {len(bird_data)}")
    
    # 调试信息：检查输出值范围
    max_prob = np.max(probabilities) * 100
    min_prob = np.min(probabilities) * 100
    mean_prob = np.mean(probabilities) * 100
    print(f"🔍 {model_name} 置信度范围: 最大={max_prob:.4f}%, 最小={min_prob:.4f}%, 平均={mean_prob:.4f}%")
    
    # 显示前5个最高置信度
    top_5_indices = np.argsort(probabilities)[::-1][:5]
    print(f"🔍 {model_name} Top5置信度:")
    for i, idx in enumerate(top_5_indices):
        print(f"   {i+1}. 类别{idx}: {probabilities[idx]*100:.4f}%")
    
    # 获取top结果，但要确保不超出bird_data范围
    max_classes = min(len(probabilities), len(bird_data))
    top_indices = np.argsort(probabilities[:max_classes])[::-1][:1000]  # 只取有效范围内的类别
    
    candidates = []
    
    for idx in top_indices:
        raw_confidence = probabilities[idx] * 100
        
        if raw_confidence < 0.5:
            continue
        
        try:
            # 双重检查索引有效性
            if idx < len(bird_data) and idx < len(probabilities) and len(bird_data[idx]) >= 2:
                bird_name_cn = bird_data[idx][0]
                bird_name_en = bird_data[idx][1]
                name = f"{bird_name_cn} ({bird_name_en})"
                
                # 应用地理区域置信度调整
                region_boost = calculate_regional_confidence_boost(bird_name_en, user_region)
                adjusted_confidence = raw_confidence * region_boost
                
                # 获取鸟类区域信息
                bird_region = get_bird_region(bird_name_en)
                region_info = f" [区域: {bird_region}]" if bird_region != 'Unknown' else ""
                boost_info = f" [调整: {region_boost:.1f}x]" if region_boost != 1.0 else ""
                
                candidates.append({
                    'class_id': idx,
                    'raw_confidence': raw_confidence,
                    'adjusted_confidence': adjusted_confidence,
                    'name': name,
                    'region': bird_region,
                    'boost': region_boost,
                    'display_info': region_info + boost_info
                })
            else:
                # 如果索引超出范围，跳过
                if idx >= len(bird_data):
                    print(f"⚠️ 跳过超出范围的类别索引: {idx} (最大: {len(bird_data)-1})")
        except (IndexError, TypeError) as e:
            print(f"⚠️ 处理类别 {idx} 时出错: {e}")
            pass
    
    # 按调整后置信度排序
    candidates.sort(key=lambda x: x['adjusted_confidence'], reverse=True)
    
    results = []
    for candidate in candidates[:5]:
        if candidate['adjusted_confidence'] >= 1.0:
            results.append(
                f"  🔹 {candidate['adjusted_confidence']:.2f}% | {candidate['name']}{candidate['display_info']}"
            )
    
    return results, candidates

def run_model_comparison(image_path, user_region=None):
    """运行模型对比测试"""
    try:
        # 加载图像
        original_image = Image.open(image_path).convert("RGB")
        print(f"📷 加载图像: {image_path}")
        
        # 为不同模型预处理图像
        pytorch_preprocessed = preprocess_image(original_image, for_pytorch=True)  # 224x224
        
        # 尝试ONNX的多种预处理方法
        preprocessing_methods = [
            ("BGR+ImageNet标准化", "bgr"),
            ("RGB+ImageNet标准化", "rgb"), 
            ("简单归一化", "simple")
        ]
        
        print("\n" + "="*80)
        print("🚀 ONNX vs PyTorch 模型对比测试")
        print("="*80)
        
        if user_region:
            print(f"📍 目标区域: {user_region}")
            print(f"📋 调整规则: {user_region}地区物种 +50%, 其他地区物种 -20%")
        
        # ONNX推理 - 测试多种预处理方法
        best_onnx_results = []
        best_onnx_candidates = []
        best_method_name = ""
        best_confidence = 0
        
        for method_name, method_key in preprocessing_methods:
            print(f"\n🔥 ONNX模型推理中... (300x300, {method_name})")
            
            onnx_preprocessed = preprocess_image(original_image, target_size=300, for_pytorch=False, method=method_key)
            onnx_logits, onnx_time = run_onnx_inference(onnx_session, input_name, onnx_preprocessed)
            onnx_results, onnx_candidates = process_results(onnx_logits, bird_info, user_region, f"ONNX-{method_name}")
            
            # 检查是否有有效结果
            if onnx_candidates and onnx_candidates[0]['adjusted_confidence'] > best_confidence:
                best_confidence = onnx_candidates[0]['adjusted_confidence']
                best_onnx_results = onnx_results
                best_onnx_candidates = onnx_candidates
                best_method_name = method_name
            
            print(f"   结果数量: {len(onnx_results)}")
            if onnx_candidates:
                print(f"   最高置信度: {onnx_candidates[0]['adjusted_confidence']:.2f}%")
        
        # 使用最佳ONNX结果进行最终对比
        onnx_results = best_onnx_results
        onnx_candidates = best_onnx_candidates
        
        # PyTorch推理
        pytorch_results = []
        pytorch_candidates = []
        pytorch_time = 0
        
        if pytorch_model is not None:
            print(f"🔥 PyTorch模型推理中... (224x224)")
            pytorch_logits, pytorch_time = run_pytorch_inference(pytorch_model, pytorch_preprocessed)
            pytorch_results, pytorch_candidates = process_results(pytorch_logits, bird_info, user_region, "PyTorch")
        
        # 显示结果
        print(f"\n📊 ONNX模型最佳结果 (方法: {best_method_name}):")
        if onnx_results:
            for result in onnx_results:
                print(result)
        else:
            print("  - 所有预处理方法都无法获得满足条件的识别结果")
        
        if pytorch_model is not None:
            print(f"\n📊 PyTorch模型结果 (推理时间: {pytorch_time:.3f}s):")
            if pytorch_results:
                for result in pytorch_results:
                    print(result)
            else:
                print("  - 无满足条件的识别结果")
            
            # 性能对比
            print(f"\n⚡ 性能对比:")
            print(f"  ONNX推理时间:    {onnx_time:.3f}s")
            print(f"  PyTorch推理时间: {pytorch_time:.3f}s")
            if pytorch_time > 0:
                speedup = pytorch_time / onnx_time
                print(f"  ONNX加速比:      {speedup:.2f}x")
            
            # 结果一致性检查
            if onnx_candidates and pytorch_candidates:
                onnx_top = onnx_candidates[0]['name']
                pytorch_top = pytorch_candidates[0]['name']
                if onnx_top == pytorch_top:
                    print(f"  ✅ 两模型识别结果一致: {onnx_top}")
                else:
                    print(f"  ⚠️ 两模型识别结果不同:")
                    print(f"    ONNX:    {onnx_top}")
                    print(f"    PyTorch: {pytorch_top}")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

# --- 主程序 ---
if __name__ == "__main__":
    # 获取图片路径
    image_path = input("请输入图片文件的完整路径: ")
    if not os.path.exists(image_path):
        print(f"❌ 文件不存在: {image_path}")
        exit()
    
    # 获取用户所在地理区域
    print("\n可选地理区域:")
    regions = list(GEOGRAPHIC_REGIONS.keys()) + ['None']
    for i, region in enumerate(regions, 1):
        print(f"{i}. {region}")
    
    try:
        region_choice = input("\n请选择您所在的地理区域 (输入数字，或直接回车跳过): ").strip()
        if region_choice and region_choice.isdigit():
            choice_idx = int(region_choice) - 1
            if 0 <= choice_idx < len(regions) - 1:  # 排除 'None'
                user_region = regions[choice_idx]
                print(f"已选择区域: {user_region}")
            else:
                user_region = None
                print("未选择特定区域，将进行全球模式测试")
        else:
            user_region = None
            print("未选择特定区域，将进行全球模式测试")
    except:
        user_region = None
        print("输入无效，将进行全球模式测试")
    
    # 运行对比测试
    run_model_comparison(image_path, user_region)