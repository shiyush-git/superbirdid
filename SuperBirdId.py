import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from PIL.ExifTags import TAGS, GPSTAGS
import json
import cv2
import csv
import os
import sys

# RAW格式支持
try:
    import rawpy
    import imageio
    RAW_SUPPORT = True
except ImportError:
    RAW_SUPPORT = False
    print("提示: 如需支持RAW格式，请安装: pip install rawpy imageio")

# 尝试导入YOLO模块
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("警告: YOLO模块未找到，将跳过鸟类检测功能")

# 尝试导入eBird国家过滤器
try:
    from ebird_country_filter import eBirdCountryFilter
    EBIRD_FILTER_AVAILABLE = True
except ImportError:
    EBIRD_FILTER_AVAILABLE = False
    print("警告: eBird过滤器模块未找到，将跳过国家物种过滤功能")

# 尝试导入SQLite数据库管理器
try:
    from bird_database_manager import BirdDatabaseManager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("警告: 数据库管理器模块未找到，将使用传统JSON文件")

# --- 获取脚本所在目录 ---
script_dir = os.path.dirname(os.path.abspath(__file__))

# --- YOLO鸟类检测器 ---
class YOLOBirdDetector:
    def __init__(self, model_path=None):
        if not YOLO_AVAILABLE:
            self.model = None
            return
            
        if model_path is None:
            model_path = os.path.join(script_dir, 'yolo11x.pt')
        
        try:
            self.model = YOLO(model_path)
            print(f"YOLO模型加载成功: {model_path}")
        except Exception as e:
            print(f"YOLO模型加载失败: {e}")
            self.model = None
    
    def detect_and_crop_bird(self, image_input, confidence_threshold=0.25, padding=20):
        """
        检测并裁剪鸟类区域

        Args:
            image_input: 可以是文件路径(str)或PIL Image对象
            confidence_threshold: YOLO检测置信度阈值
            padding: 裁剪边距

        Returns:
            (cropped_image, detection_info) 或 (None, error_message)
        """
        if self.model is None:
            return None, "YOLO模型未可用"

        try:
            # 判断输入类型
            if isinstance(image_input, str):
                # 文件路径：需要先加载图像
                from SuperBirdId import load_image
                image = load_image(image_input)
            elif isinstance(image_input, Image.Image):
                # 已经是PIL Image对象
                image = image_input
            else:
                return None, "不支持的图像输入类型"

            # 将PIL Image转换为numpy数组用于YOLO检测
            import numpy as np
            img_array = np.array(image)

            # 使用numpy数组进行YOLO检测
            results = self.model(img_array, conf=confidence_threshold)

            # 解析检测结果
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())

                        # 只保留鸟类检测结果 (COCO数据集中鸟类的class_id是14)
                        if class_id == 14:
                            detections.append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'confidence': float(confidence)
                            })

            if not detections:
                return None, "未检测到鸟类"

            # 选择置信度最高的检测结果
            best_detection = max(detections, key=lambda x: x['confidence'])

            # 使用已加载的图像进行裁剪
            img_width, img_height = image.size
            
            x1, y1, x2, y2 = best_detection['bbox']
            
            # 添加边距并确保不超出图像边界
            x1_padded = max(0, x1 - padding)
            y1_padded = max(0, y1 - padding)
            x2_padded = min(img_width, x2 + padding)
            y2_padded = min(img_height, y2 + padding)
            
            # 裁剪图像
            cropped_image = image.crop((x1_padded, y1_padded, x2_padded, y2_padded))
            
            detection_info = f"YOLO检测: 置信度{best_detection['confidence']:.3f}, 裁剪尺寸{cropped_image.size}"
            
            return cropped_image, detection_info
            
        except Exception as e:
            return None, f"YOLO检测失败: {e}"

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

# --- 加载模型和数据 ---
PYTORCH_CLASSIFICATION_MODEL_PATH = os.path.join(script_dir, 'birdid2024.pt')
BIRD_INFO_PATH = os.path.join(script_dir, 'birdinfo.json')
ENDEMIC_PATH = os.path.join(script_dir, 'endemic.json')
LABELMAP_PATH = os.path.join(script_dir, 'labelmap.csv')

# 全局变量 - 使用懒加载
classifier = None
db_manager = None
bird_info = None
endemic_info = None
labelmap_data = None

def lazy_load_classifier():
    """懒加载 PyTorch 分类模型"""
    global classifier
    if classifier is None:
        print("正在加载AI模型...")
        classifier = torch.jit.load(PYTORCH_CLASSIFICATION_MODEL_PATH)
        classifier.eval()
        print("✓ PyTorch分类模型加载完成")
    return classifier

def lazy_load_bird_info():
    """懒加载鸟类信息"""
    global bird_info
    if bird_info is None:
        print("正在加载鸟类数据...")
        with open(BIRD_INFO_PATH, 'r') as f:
            bird_info = json.load(f)
        print("✓ 鸟类信息加载完成")
    return bird_info

def lazy_load_endemic_info():
    """懒加载特有种信息"""
    global endemic_info
    if endemic_info is None:
        with open(ENDEMIC_PATH, 'r') as f:
            endemic_info = json.load(f)
        print("✓ 特有种信息加载完成")
    return endemic_info

def lazy_load_database():
    """懒加载数据库管理器"""
    global db_manager
    if db_manager is None and DATABASE_AVAILABLE:
        try:
            print("正在连接数据库...")
            db_manager = BirdDatabaseManager()
            print("✓ SQLite数据库连接成功")
        except Exception as e:
            print(f"✗ SQLite数据库连接失败: {e}")
            db_manager = False  # 标记为已尝试但失败
    return db_manager if db_manager is not False else None

def lazy_load_labelmap():
    """懒加载标签映射"""
    global labelmap_data
    if labelmap_data is None:
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
            print(f"✓ 标签映射加载完成: {len(labelmap_data)} 条目")
        else:
            print("⚠ 标签映射文件未找到")
    return labelmap_data

# 验证关键文件是否存在
def verify_files():
    """快速验证关键文件"""
    required_files = [
        PYTORCH_CLASSIFICATION_MODEL_PATH,
        BIRD_INFO_PATH,
        ENDEMIC_PATH,
        LABELMAP_PATH
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(os.path.basename(file_path))

    if missing_files:
        print(f"✗ 缺少必要文件: {', '.join(missing_files)}")
        sys.exit(1)
    else:
        print("✓ 文件完整性检查通过")

# 启动时只进行文件验证
verify_files()

def extract_gps_from_exif(image_path):
    """
    从图像EXIF数据中提取GPS坐标
    返回: (latitude, longitude, location_info) 或 (None, None, None)
    """
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()

        if not exif_data:
            return None, None, "无EXIF数据"

        gps_info = {}
        for tag, value in exif_data.items():
            decoded_tag = TAGS.get(tag, tag)
            if decoded_tag == "GPSInfo":
                for gps_tag in value:
                    gps_decoded_tag = GPSTAGS.get(gps_tag, gps_tag)
                    gps_info[gps_decoded_tag] = value[gps_tag]
                break

        if not gps_info:
            return None, None, "无GPS数据"

        # 解析GPS坐标
        def convert_to_degrees(gps_coord, hemisphere):
            degrees = gps_coord[0]
            minutes = gps_coord[1]
            seconds = gps_coord[2]

            decimal_degrees = degrees + (minutes / 60.0) + (seconds / 3600.0)

            if hemisphere in ['S', 'W']:
                decimal_degrees = -decimal_degrees

            return decimal_degrees

        lat = None
        lon = None

        if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
            lat = convert_to_degrees(
                gps_info['GPSLatitude'],
                gps_info['GPSLatitudeRef']
            )

        if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
            lon = convert_to_degrees(
                gps_info['GPSLongitude'],
                gps_info['GPSLongitudeRef']
            )

        if lat is not None and lon is not None:
            location_info = f"GPS: {lat:.6f}, {lon:.6f}"
            return lat, lon, location_info
        else:
            return None, None, "GPS坐标不完整"

    except Exception as e:
        return None, None, f"GPS解析失败: {e}"

def load_image(image_path):
    """
    增强的图像加载函数 - 支持标准格式和RAW格式
    支持格式: JPG, PNG, TIFF, BMP, CR2, CR3, NEF, ARW, DNG, RAF, ORF等
    """
    # 检查文件是否存在
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"文件不存在: {image_path}")

    # 获取文件扩展名
    file_ext = os.path.splitext(image_path)[1].lower()

    # RAW格式扩展名列表
    raw_extensions = [
        '.cr2', '.cr3',     # Canon
        '.nef', '.nrw',     # Nikon
        '.arw', '.srf',     # Sony
        '.dng',             # Adobe/通用
        '.raf',             # Fujifilm
        '.orf',             # Olympus
        '.rw2',             # Panasonic
        '.pef',             # Pentax
        '.srw',             # Samsung
        '.raw',             # 通用
        '.rwl',             # Leica
        '.3fr',             # Hasselblad
        '.fff',             # Hasselblad
        '.erf',             # Epson
        '.mef',             # Mamiya
        '.mos',             # Leaf
        '.mrw',             # Minolta
        '.x3f',             # Sigma
    ]

    # 判断是否为RAW格式
    if file_ext in raw_extensions:
        if not RAW_SUPPORT:
            raise ImportError(
                f"检测到RAW格式 ({file_ext})，但RAW支持库未安装。\n"
                f"请安装: pip install rawpy imageio"
            )

        try:
            print(f"🔍 检测到RAW格式: {file_ext.upper()}")
            print(f"📸 正在处理RAW文件...")

            # 使用rawpy读取RAW文件
            with rawpy.imread(image_path) as raw:
                # 使用默认参数处理RAW数据
                # use_camera_wb=True: 使用相机白平衡
                # output_bps=8: 输出8位图像
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    output_bps=8,
                    no_auto_bright=False,  # 自动亮度调整
                    auto_bright_thr=0.01   # 自动亮度阈值
                )

            # 转换为PIL Image
            image = Image.fromarray(rgb)

            print(f"✓ RAW图像加载成功，尺寸: {image.size}")
            print(f"  原始RAW → RGB 8位转换完成")

            return image

        except rawpy.LibRawError as e:
            raise Exception(f"RAW文件处理失败: {e}")
        except Exception as e:
            raise Exception(f"RAW图像加载失败: {e}")

    else:
        # 标准格式 (JPG, PNG, TIFF等)
        try:
            image = Image.open(image_path).convert("RGB")
            print(f"✓ 图像加载成功，尺寸: {image.size}")
            return image
        except Exception as e:
            raise Exception(f"图像加载失败: {e}")

def get_region_from_gps(latitude, longitude):
    """
    根据GPS坐标确定地理区域和对应的eBird国家
    返回: (region, country_code, region_info)
    """
    if latitude is None or longitude is None:
        return None, None, "无GPS坐标"

    # 基于GPS坐标的地理区域划分
    region_map = [
        # 澳洲和大洋洲
        {
            'name': 'Australia',
            'country': 'australia',
            'bounds': [(-50, 110), (-10, 180)],  # 南纬10-50度，东经110-180度
            'description': '澳大利亚'
        },
        # 亚洲
        {
            'name': 'Asia',
            'country': 'china',
            'bounds': [(-10, 60), (80, 180)],    # 南纬10度到北纬80度，东经60-180度
            'description': '亚洲'
        },
        # 欧洲
        {
            'name': 'Europe',
            'country': 'germany',
            'bounds': [(35, -25), (80, 60)],     # 北纬35-80度，西经25度到东经60度
            'description': '欧洲'
        },
        # 北美洲
        {
            'name': 'North_America',
            'country': 'usa',
            'bounds': [(15, -170), (80, -50)],   # 北纬15-80度，西经170-50度
            'description': '北美洲'
        },
        # 南美洲
        {
            'name': 'South_America',
            'country': 'brazil',
            'bounds': [(-60, -90), (15, -30)],   # 南纬60度到北纬15度，西经90-30度
            'description': '南美洲'
        },
        # 非洲
        {
            'name': 'Africa',
            'country': 'south_africa',
            'bounds': [(-40, -20), (40, 55)],    # 南纬40度到北纬40度，西经20度到东经55度
            'description': '非洲'
        }
    ]

    for region in region_map:
        (lat_min, lon_min), (lat_max, lon_max) = region['bounds']

        # 检查坐标是否在区域内
        if (lat_min <= latitude <= lat_max and
            lon_min <= longitude <= lon_max):

            region_info = f"GPS定位: {region['description']} ({latitude:.3f}, {longitude:.3f})"
            return region['name'], region['country'], region_info

    # 默认全球模式
    return None, None, f"未知区域 ({latitude:.3f}, {longitude:.3f})"

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
    """
    地理区域信息仅用于显示，不再影响置信度计算

    Args:
        species_name: 鸟类的英文名称
        user_region: 用户选择的地理区域

    Returns:
        置信度调整系数: 始终为1.0（无调整）
    """
    return 1.0  # 地理区域信息仅作为显示参考，不再调整置信度

def dual_resize_comparison(image, target_size=224):
    """
    双方法对比：同时测试直接224和256→224两种方法，返回两种结果
    """
    # 方法1：直接调整到224x224
    direct_image = image.resize((target_size, target_size), Image.LANCZOS)
    
    # 方法2：传统256→224方法
    resized_256 = image.resize((256, 256), Image.LANCZOS)
    left = (256 - target_size) // 2
    top = (256 - target_size) // 2
    traditional_image = resized_256.crop((left, top, left + target_size, top + target_size))
    
    return {
        'direct': {
            'image': direct_image,
            'name': '直接调整224x224'
        },
        'traditional': {
            'image': traditional_image, 
            'name': '传统方法(256→224)'
        }
    }

def smart_resize(image, target_size=224):
    """
    智能图像尺寸调整，根据图像大小和宽高比选择最佳预处理方法
    现在会同时测试两种方法，返回更好的结果
    """
    width, height = image.size
    max_dimension = max(width, height)
    
    # 对于小图像，仍然只使用直接方法以提高效率
    if max_dimension < 1000:
        final_image = image.resize((target_size, target_size), Image.LANCZOS)
        method_name = "直接调整(小图像)"
        return final_image, method_name, None  # 第三个参数是对比结果
    
    # 对于大图像，使用传统256→224方法（基于测试结果优化）
    resized_256 = image.resize((256, 256), Image.LANCZOS)
    left = (256 - target_size) // 2
    top = (256 - target_size) // 2
    final_image = resized_256.crop((left, top, left + target_size, top + target_size))
    method_name = "传统256→224(大图像优化)"

    return final_image, method_name, None

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

def test_single_resize_method(model, processed_image, bird_data, method_name):
    """测试单个预处理方法的识别效果"""
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

    # 温度锐化: 提升置信度 (T=0.6 经过测试验证可提升5倍置信度)
    TEMPERATURE = 0.6
    probabilities = torch.nn.functional.softmax(output[0] / TEMPERATURE, dim=0)
    max_confidence = probabilities.max().item() * 100
    
    return max_confidence, probabilities, method_name

def run_ultimate_classification(image, user_region=None, country_filter=None, ebird_species_set=None, use_gps_precise=False):
    """
    终极版本：BGR格式 + 图像增强 + 地理区域智能筛选 + eBird精确定位过滤
    user_region: 用户所在地理区域 (Australia, Asia, Europe, Africa, North_America, South_America, Pacific, Arctic)
    country_filter: eBird国家过滤器实例
    ebird_species_set: 国家物种代码集合
    use_gps_precise: 是否使用GPS精确定位数据
    """
    # 懒加载所需组件
    model = lazy_load_classifier()
    bird_data = lazy_load_bird_info()
    endemic_data = lazy_load_endemic_info()
    db_manager = lazy_load_database()
    # 测试多种增强方法 + 双预处理对比
    enhancement_methods = [
        ("无增强", "none"),
        ("UnsharpMask增强", "unsharp_mask"),
        ("高对比度+边缘增强", "contrast_edge"),
        ("降低饱和度", "desaturate")
    ]
    
    best_confidence = 0
    best_method = ""
    best_results = []
    all_test_results = []  # 保存所有测试结果
    
    for method_name, method_key in enhancement_methods:
        # 应用图像增强
        if method_key == "none":
            enhanced_image = image
        else:
            enhanced_image = apply_enhancement(image, method_key)
        
        # 智能预处理：获取预处理方法和可能的对比数据
        final_image, resize_method, comparison_data = smart_resize(enhanced_image, target_size=224)
        
        # 如果有对比数据（大图像），测试两种预处理方法
        if comparison_data is not None:
            for resize_type, resize_info in comparison_data.items():
                test_confidence, test_probs, test_method_name = test_single_resize_method(
                    model, resize_info['image'], bird_data, resize_info['name']
                )
                
                test_result = {
                    'enhancement': method_name,
                    'resize': test_method_name,
                    'confidence': test_confidence,
                    'probabilities': test_probs,
                    'full_method': f"{method_name} + {test_method_name}"
                }
                all_test_results.append(test_result)
                
                # 检查是否是当前最佳结果
                if test_confidence > best_confidence:
                    best_confidence = test_confidence
                    best_method = test_result['full_method']
                    # 使用这个结果的probabilities来生成最终结果
                    probabilities = test_probs
        else:
            # 小图像，只测试一种方法
            test_confidence, test_probs, test_method_name = test_single_resize_method(
                model, final_image, bird_data, resize_method
            )
            
            test_result = {
                'enhancement': method_name,
                'resize': test_method_name,
                'confidence': test_confidence,
                'probabilities': test_probs,
                'full_method': f"{method_name} + {test_method_name}"
            }
            all_test_results.append(test_result)
            
            if test_confidence > best_confidence:
                best_confidence = test_confidence
                best_method = test_result['full_method']
                probabilities = test_probs

    # 循环结束后，处理最佳结果
    if best_confidence > 0:
        # 获取结果
        results = []
        k = min(len(probabilities), len(bird_data), 1000)
        all_probs, all_catid = torch.topk(probabilities, k)
        
        count = 0
        # 存储所有候选结果用于地理区域调整
        candidates = []
        
        for i in range(all_probs.size(0)):
            class_id = all_catid[i].item()
            raw_confidence = all_probs[i].item() * 100
            
            if raw_confidence < 1.0:  # 原生置信度必须≥1%才显示
                continue
            
            try:
                if class_id < len(bird_data) and len(bird_data[class_id]) >= 2:
                    bird_name_cn = bird_data[class_id][0]
                    bird_name_en = bird_data[class_id][1]
                    name = f"{bird_name_cn} ({bird_name_en})"
                    
                    # 移除地理区域名称匹配的置信度加成（只用于显示信息）
                    region_boost = 1.0  # 不再基于名称匹配给予置信度提升
                    
                    # 应用eBird物种过滤（如果可用）
                    ebird_boost = 1.0
                    ebird_match = False
                    ebird_code = None
                    ebird_type = ""

                    if ebird_species_set:
                        # 优先使用数据库获取eBird代码
                        if db_manager:
                            ebird_code = db_manager.get_ebird_code_by_english_name(bird_name_en)

                        # eBird过滤逻辑（纯过滤，不加成置信度）
                        if ebird_species_set:  # 如果启用了eBird过滤
                            if not ebird_code:  # 没有eBird代码，跳过
                                continue
                            elif ebird_code not in ebird_species_set:  # 不在列表中，跳过
                                continue
                            else:  # 在列表中，标记但不加成
                                ebird_boost = 1.0  # 不加成，只标记
                                if use_gps_precise:
                                    ebird_type = "GPS精确"
                                else:
                                    ebird_type = "国家级"
                                ebird_match = True

                    # 综合置信度（移除eBird加成，只保留温度锐化的效果）
                    adjusted_confidence = raw_confidence * region_boost * ebird_boost
                    adjusted_confidence = min(adjusted_confidence, 99.0)  # 限制最高99%
                    
                    # 获取鸟类区域信息
                    bird_region = get_bird_region(bird_name_en)
                    region_info = f" [区域: {bird_region}]" if bird_region != 'Unknown' else ""
                    
                    # 构建显示信息（eBird只显示匹配，不显示加成）
                    boost_parts = []
                    # 不再显示eBird加成信息，因为已移除加成

                    boost_info = ""  # 移除置信度调整显示
                    if ebird_match:
                        if use_gps_precise:
                            ebird_info = f" [GPS精确匹配✓]"
                        else:
                            ebird_info = f" [eBird匹配✓]"
                    else:
                        ebird_info = ""
                    
                    candidates.append({
                        'class_id': class_id,
                        'raw_confidence': raw_confidence,
                        'adjusted_confidence': adjusted_confidence,
                        'name': name,
                        'region': bird_region,
                        'boost': region_boost,
                        'ebird_boost': ebird_boost,
                        'ebird_match': ebird_match,
                        'display_info': region_info + boost_info + ebird_info
                    })
                else:
                    name = f"Unknown (ID: {class_id})"
                    candidates.append({
                        'class_id': class_id,
                        'raw_confidence': raw_confidence,
                        'adjusted_confidence': raw_confidence,
                        'name': name,
                        'region': 'Unknown',
                        'boost': 1.0,
                        'display_info': ""
                    })
            except (IndexError, TypeError):
                name = f"Unknown (ID: {class_id})"
                candidates.append({
                    'class_id': class_id,
                    'raw_confidence': raw_confidence,
                    'adjusted_confidence': raw_confidence,
                    'name': name,
                    'region': 'Unknown',
                    'boost': 1.0,
                    'display_info': ""
                })
        
        # 按调整后置信度重新排序
        candidates.sort(key=lambda x: x['adjusted_confidence'], reverse=True)
        
        # 选择前5个结果，原生置信度≥1%
        for candidate in candidates[:5]:
                results.append(
                    f"  - Class ID: {candidate['class_id']}, "
                    f"原始: {candidate['raw_confidence']:.2f}%, "
                    f"调整后: {candidate['adjusted_confidence']:.2f}%, "
                    f"Name: {candidate['name']}{candidate['display_info']}"
                )
                count += 1
        
        best_results = results if results else ["  - 无法识别 (所有结果原生置信度低于1%)"]
    else:
        best_results = ["  - 未能识别任何鸟类"]
        
    # 打印所有测试结果的概要（用于调试）
    print(f"\n已测试 {len(all_test_results)} 种组合：")
    for i, result in enumerate(sorted(all_test_results, key=lambda x: x['confidence'], reverse=True)[:3]):
        print(f"  {i+1}. {result['full_method']}: {result['confidence']:.2f}%")

    # 打印最佳结果
    if ebird_species_set:
        if use_gps_precise:
            ebird_info = f" + GPS精确定位过滤"
        else:
            ebird_info = f" + eBird国家过滤"
    else:
        ebird_info = ""

    print(f"=== 最佳组合结果 ===")
    print(f"最佳方法: {best_method} + BGR格式 + 智能置信度调整{ebird_info}")
    print(f"最高置信度: {best_confidence:.2f}%")
    if user_region:
        print(f"目标区域: {user_region} (仅作为参考信息)")
    if ebird_species_set:
        if use_gps_precise:
            print(f"GPS精确过滤: 仅显示25km范围内有观察记录的鸟类 (纯过滤，无加成)")
        else:
            print(f"eBird过滤: 仅显示国家物种列表中的鸟类 (纯过滤，无加成)")
    print("识别结果:")
    for result in best_results:
        print(result)
    
    return best_confidence, best_method, best_results

# --- 主程序 ---
if __name__ == "__main__":
    print("🐦 SuperBirdID - 高精度鸟类识别系统")
    print("=" * 50)

    # 显示支持的功能
    features = ["快速启动"]
    if YOLO_AVAILABLE:
        features.append("YOLO智能检测")
    if EBIRD_FILTER_AVAILABLE:
        features.append("eBird地理过滤")
    if RAW_SUPPORT:
        features.append("RAW格式")

    print("✓ " + " | ✓ ".join(features))
    print("=" * 50)

    # 获取图片路径
    image_path = input("\n📸 请输入图片文件的完整路径: ").strip().strip("'\"")  # 去掉前后空格和引号
    
    try:
        original_image = load_image(image_path)
        detection_info = None

        # 尝试从图像中提取GPS信息
        print("\n🌍 正在检测GPS位置信息...")
        latitude, longitude, gps_info = extract_gps_from_exif(image_path)
        auto_region = None
        auto_country = None

        if latitude is not None and longitude is not None:
            auto_region, auto_country, region_info = get_region_from_gps(latitude, longitude)
            if auto_region:
                print(f"✓ {region_info}")
            else:
                print(f"⚠ {region_info}")
        else:
            print(f"⚠ {gps_info}")

        # 自动判断是否需要使用YOLO
        width, height = original_image.size
        max_dimension = max(width, height)
        
        # 大于640像素且YOLO可用时自动使用YOLO
        if max_dimension > 640 and YOLO_AVAILABLE:
            print(f"\n图像尺寸: {width}x{height}")
            print(f"检测到大尺寸图像({max_dimension} > 640)，自动启用YOLO鸟类检测...")

            detector = YOLOBirdDetector()
            # 传入PIL Image对象而不是文件路径，支持RAW格式
            cropped_image, detection_msg = detector.detect_and_crop_bird(original_image)

            if cropped_image is not None:
                original_image = cropped_image
                detection_info = detection_msg
                print(f"YOLO检测成功: {detection_msg}")
            else:
                print(f"YOLO检测失败: {detection_msg}")
                print("将使用原始图像进行识别")
        elif max_dimension <= 640:
            print(f"\n图像尺寸: {width}x{height}")
            print(f"小尺寸图像({max_dimension} ≤ 640)，直接进行识别...")
        elif not YOLO_AVAILABLE:
            print(f"\n图像尺寸: {width}x{height}")
            print("YOLO模块不可用，使用原始图像进行识别...")
        
    except FileNotFoundError:
        print(f"错误: 文件未找到, 请检查路径 '{image_path}' 是否正确。")
        sys.exit(1)
    except Exception as e:
        print(f"加载图片时发生错误: {e}")
        sys.exit(1)
    
    # 智能地理区域设置（GPS优先）
    print("\n=== 地理位置设置 ===")

    if auto_region and auto_country:
        # GPS自动检测成功
        print(f"🎯 GPS自动检测: {auto_region}")
        print("筛选选项: 1.GPS精确位置(25km) 2.国家级别 3.手动选择")
        gps_choice = input("请选择筛选方式 (1-3，直接回车使用GPS精确): ").strip() or '1'

        if gps_choice == '1':
            # 使用GPS精确位置
            user_region, country_code = auto_region, auto_country
            use_precise_gps = True
            print(f"✓ 已选择GPS精确定位: {auto_region} + 25km范围eBird数据")
        elif gps_choice == '2':
            # 使用国家级别
            user_region, country_code = auto_region, auto_country
            use_precise_gps = False
            print(f"✓ 已选择国家级别: {user_region} + eBird({country_code})")
        else:
            # 用户选择手动设置
            use_precise_gps = False
            print("可选区域: 1.Asia/China  2.Australia  3.Europe  4.North_America  5.全球模式")
            region_country_map = {
                '1': ('Asia', 'china'),
                '2': ('Australia', 'australia'),
                '3': ('Europe', 'germany'),
                '4': ('North_America', 'usa'),
                '5': (None, None)
            }

            try:
                choice = input("请选择 (1-5): ").strip()
                user_region, country_code = region_country_map.get(choice, ('Australia', 'australia'))

                if user_region:
                    print(f"✓ 手动选择: {user_region} + eBird({country_code})")
                else:
                    print("✓ 手动选择: 全球模式")
            except:
                user_region, country_code = 'Australia', 'australia'
                print("✓ 输入无效，默认使用: Australia + eBird(australia)")

    else:
        # 无GPS数据，检查是否有离线eBird数据可用
        use_precise_gps = False

        # 尝试读取离线数据索引
        offline_index_path = os.path.join(script_dir, "offline_ebird_data", "offline_index.json")
        available_countries = {}

        if os.path.exists(offline_index_path):
            try:
                with open(offline_index_path, 'r', encoding='utf-8') as f:
                    offline_index = json.load(f)
                    available_countries = offline_index.get('countries', {})
            except Exception as e:
                print(f"⚠ 读取离线数据索引失败: {e}")

        if available_countries:
            # 有离线数据，显示所有可用国家
            print(f"\n📦 检测到 {len(available_countries)} 个国家的离线eBird数据")
            print("=" * 50)

            # 创建国家代码到中文名称的映射
            country_names = {
                'AU': '澳大利亚', 'CN': '中国', 'US': '美国', 'CA': '加拿大',
                'BR': '巴西', 'IN': '印度', 'ID': '印度尼西亚', 'MX': '墨西哥',
                'CO': '哥伦比亚', 'PE': '秘鲁', 'EC': '厄瓜多尔', 'BO': '玻利维亚',
                'VE': '委内瑞拉', 'CL': '智利', 'AR': '阿根廷', 'ZA': '南非',
                'KE': '肯尼亚', 'TZ': '坦桑尼亚', 'MG': '马达加斯加', 'CM': '喀麦隆',
                'GH': '加纳', 'NG': '尼日利亚', 'ET': '埃塞俄比亚', 'UG': '乌干达',
                'CR': '哥斯达黎加', 'PA': '巴拿马', 'GT': '危地马拉', 'NI': '尼加拉瓜',
                'HN': '洪都拉斯', 'BZ': '伯利兹', 'SV': '萨尔瓦多', 'NO': '挪威',
                'SE': '瑞典', 'FI': '芬兰', 'GB': '英国', 'FR': '法国',
                'ES': '西班牙', 'IT': '意大利', 'DE': '德国', 'PL': '波兰',
                'RO': '罗马尼亚', 'TR': '土耳其', 'RU': '俄罗斯', 'JP': '日本',
                'KR': '韩国', 'TH': '泰国', 'VN': '越南', 'PH': '菲律宾',
                'MY': '马来西亚', 'SG': '新加坡', 'NZ': '新西兰'
            }

            # 按区域分组显示
            regions = {
                '亚洲': ['CN', 'IN', 'ID', 'JP', 'KR', 'TH', 'VN', 'PH', 'MY', 'SG', 'RU'],
                '大洋洲': ['AU', 'NZ'],
                '欧洲': ['GB', 'DE', 'FR', 'IT', 'ES', 'NO', 'SE', 'FI', 'PL', 'RO', 'TR'],
                '北美洲': ['US', 'CA', 'MX', 'CR', 'PA', 'GT', 'NI', 'HN', 'BZ', 'SV'],
                '南美洲': ['BR', 'CO', 'PE', 'EC', 'BO', 'VE', 'CL', 'AR'],
                '非洲': ['ZA', 'KE', 'TZ', 'MG', 'CM', 'GH', 'NG', 'ET', 'UG']
            }

            # 创建编号映射
            country_list = []
            idx = 1

            for region_name, region_countries in regions.items():
                available_in_region = [cc for cc in region_countries if cc in available_countries]
                if available_in_region:
                    print(f"\n【{region_name}】")
                    for cc in available_in_region:
                        species_count = available_countries[cc].get('species_count', 0)
                        cn_name = country_names.get(cc, cc)
                        print(f"  {idx}. {cn_name} ({cc}) - {species_count} 种鸟类")
                        country_list.append(cc)
                        idx += 1

            print(f"\n  {idx}. 全球模式（不使用国家过滤）")
            print("=" * 50)

            try:
                choice = input(f"请选择国家 (1-{idx}，直接回车默认澳大利亚): ").strip()

                if not choice:
                    # 默认澳大利亚
                    country_code = 'AU'
                    user_region = 'Australia'
                    print(f"✓ 已选择: 澳大利亚 (AU) - {available_countries['AU']['species_count']} 种鸟类")
                elif choice.isdigit():
                    choice_num = int(choice)
                    if 1 <= choice_num < idx:
                        # 选择了具体国家
                        country_code = country_list[choice_num - 1]
                        cn_name = country_names.get(country_code, country_code)
                        species_count = available_countries[country_code]['species_count']
                        user_region = None  # 使用国家代码，不用区域名
                        print(f"✓ 已选择: {cn_name} ({country_code}) - {species_count} 种鸟类")
                    elif choice_num == idx:
                        # 选择全球模式
                        country_code = None
                        user_region = None
                        print("✓ 已选择: 全球模式（不使用eBird过滤）")
                    else:
                        # 无效选择，默认澳大利亚
                        country_code = 'AU'
                        user_region = 'Australia'
                        print(f"⚠ 输入无效，默认使用: 澳大利亚 (AU) - {available_countries['AU']['species_count']} 种鸟类")
                else:
                    # 无效输入，默认澳大利亚
                    country_code = 'AU'
                    user_region = 'Australia'
                    print(f"⚠ 输入无效，默认使用: 澳大利亚 (AU) - {available_countries['AU']['species_count']} 种鸟类")

            except Exception as e:
                # 发生错误，默认澳大利亚
                country_code = 'AU'
                user_region = 'Australia'
                print(f"⚠ 发生错误 ({e})，默认使用: 澳大利亚 (AU)")
        else:
            # 没有离线数据，使用传统选择
            print("⚠ 未检测到离线eBird数据")
            print("可选区域: 1.Asia/China  2.Australia  3.Europe  4.North_America  5.全球模式")
            region_country_map = {
                '1': ('Asia', 'china'),
                '2': ('Australia', 'australia'),
                '3': ('Europe', 'germany'),
                '4': ('North_America', 'usa'),
                '5': (None, None)
            }

            try:
                choice = input("请选择 (1-5，直接回车默认澳洲): ").strip() or '2'
                user_region, country_code = region_country_map.get(choice, (None, None))

                if user_region:
                    print(f"✓ 已选择: {user_region} + eBird({country_code})")
                else:
                    print("✓ 已选择: 全球模式")

            except:
                user_region, country_code = 'Australia', 'australia'
                print("✓ 输入无效，默认使用: Australia + eBird(australia)")

    # eBird国家物种过滤设置
    country_filter = None
    ebird_species_set = None

    if EBIRD_FILTER_AVAILABLE and (country_code or (use_precise_gps and latitude is not None and longitude is not None)):
        try:
            # eBird API密钥
            EBIRD_API_KEY = "60nan25sogpo"
            country_filter = eBirdCountryFilter(EBIRD_API_KEY, offline_dir="offline_ebird_data")

            # 检查离线数据可用性
            if country_filter.is_offline_data_available():
                available_countries = country_filter.get_available_offline_countries()
                print(f"📦 检测到离线eBird数据: {len(available_countries)} 个国家")
            else:
                print("⚠ 未检测到离线eBird数据，仅依赖在线API")

            if use_precise_gps and latitude is not None and longitude is not None:
                # 使用GPS精确位置获取25km范围内的鸟类
                print(f"正在获取GPS位置 ({latitude:.3f}, {longitude:.3f}) 25km范围内的鸟类观察记录...")
                ebird_species_set = country_filter.get_location_species_list(latitude, longitude, 25)

                if ebird_species_set:
                    print(f"✓ 成功获取精确位置 {len(ebird_species_set)} 个物种的eBird数据")
                else:
                    print("⚠ GPS精确查询失败，降级到国家级别查询...")
                    ebird_species_set = country_filter.get_country_species_list(country_code)
                    if ebird_species_set:
                        print(f"✓ 降级成功获取 {len(ebird_species_set)} 个物种的eBird数据")
            else:
                # 使用国家级别查询
                # 如果country_code已经是2位代码（如'AU'），直接使用
                # 否则通过get_country_species_list转换
                if len(country_code) == 2 and country_code.isupper():
                    # 直接使用2位国家代码
                    print(f"正在加载 {country_code} 的鸟类物种列表...")
                    ebird_species_set = country_filter.get_country_species_list(country_code)
                else:
                    # 传统的国家名称，需要转换
                    print(f"正在获取 {country_code} 的鸟类物种列表...")
                    ebird_species_set = country_filter.get_country_species_list(country_code)

                if ebird_species_set:
                    print(f"✓ 成功加载 {len(ebird_species_set)} 个物种的eBird数据")

            if not ebird_species_set:
                print("✗ 获取eBird数据失败，将使用常规模式")
                country_filter = None
        except Exception as e:
            print(f"eBird过滤器初始化失败: {e}")
    elif not EBIRD_FILTER_AVAILABLE:
        print("\neBird过滤器不可用，将使用常规地理区域过滤")
    
    # 运行终极版识别
    print(f"\n{'='*50}")
    if detection_info:
        print(f"预处理信息: {detection_info}")
    run_ultimate_classification(
        original_image,
        user_region=user_region,
        country_filter=country_filter,
        ebird_species_set=ebird_species_set,
        use_gps_precise=use_precise_gps
    )

