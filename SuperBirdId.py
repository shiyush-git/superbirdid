"""
SuperBirdID - 高精度鸟类识别系统
"""

__version__ = "3.2.1"

import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from PIL.ExifTags import TAGS, GPSTAGS
import json
import cv2
import os
import sys

# ==================== 设备配置 ====================
# 分类模型使用 CPU（TorchScript + MPS 有兼容性问题）
# YOLO 会自动检测并使用 GPU（已验证工作正常）
CLASSIFIER_DEVICE = torch.device("cpu")
print(f"📱 分类模型设备: CPU (稳定模式)")
print(f"📱 YOLO 检测: 自动 GPU 加速")
# ================================================

# ExifTool支持（可选）
try:
    import exiftool
    EXIFTOOL_AVAILABLE = True

    # 配置exiftool二进制路径（支持打包环境）
    if getattr(sys, 'frozen', False):
        # 打包后的环境（PyInstaller）
        base_path = sys._MEIPASS
        EXIFTOOL_PATH = os.path.join(base_path, 'exiftool_bundle', 'exiftool')
        # 打包环境不需要设置权限，权限应该在打包时或安装时已设置好
    else:
        # 开发环境，使用项目内的完整 exiftool bundle
        base_path = os.path.dirname(os.path.abspath(__file__))
        EXIFTOOL_PATH = os.path.join(base_path, 'exiftool_bundle', 'exiftool')
        # 开发环境下设置可执行权限
        if os.path.exists(EXIFTOOL_PATH):
            try:
                os.chmod(EXIFTOOL_PATH, 0o755)
            except PermissionError:
                pass  # 如果没有权限，忽略（文件可能已经有正确权限）

except ImportError:
    EXIFTOOL_AVAILABLE = False
    EXIFTOOL_PATH = None
    print("⚠️ PyExifTool未安装，使用PIL读取EXIF（功能受限）")

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

# 尝试导入SQLite数据库管理器（可选功能）
try:
    from bird_database_manager import BirdDatabaseManager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    # SQLite数据库是可选功能，没有也不影响核心功能
    # print("ℹ️  使用JSON文件模式（SQLite数据库未启用）")

# --- 获取脚本所在目录 ---
# 支持 PyInstaller 打包环境
if getattr(sys, 'frozen', False):
    # 运行在 PyInstaller 打包的环境中
    script_dir = sys._MEIPASS
else:
    # 运行在普通 Python 环境中
    script_dir = os.path.dirname(os.path.abspath(__file__))

# --- 获取用户数据目录 ---
def get_user_data_dir():
    """获取用户数据目录，用于存储缓存等可写文件"""
    if sys.platform == 'darwin':  # macOS
        # 使用用户文档目录下的 SuperBirdID_File 文件夹
        user_data_dir = os.path.expanduser('~/Documents/SuperBirdID_File')
    elif sys.platform == 'win32':  # Windows
        user_data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'SuperBirdID_File')
    else:  # Linux
        user_data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'SuperBirdID_File')

    # 确保目录存在
    os.makedirs(user_data_dir, exist_ok=True)
    return user_data_dir

# --- YOLO鸟类检测器 ---
class YOLOBirdDetector:
    def __init__(self, model_path=None):
        if not YOLO_AVAILABLE:
            self.model = None
            return

        if model_path is None:
            model_path = os.path.join(script_dir, 'yolo_models/yolo11l.pt')

        try:
            self.model = YOLO(model_path)
            # YOLO会自动检测并使用最佳设备（MPS/CUDA/CPU）
            print(f"YOLO模型加载成功: {model_path} (自动GPU检测)")
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
            # Ultralytics YOLO会自动检测并使用最佳设备（MPS/CUDA/CPU）
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

# 全局变量 - 使用懒加载
classifier = None
db_manager = None
bird_info = None

def decrypt_model(encrypted_path: str, password: str) -> bytes:
    """解密模型文件并返回解密后的数据"""
    print("DEBUG: 开始导入加密库...")
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    print("DEBUG: 加密库导入完成")

    # 读取加密文件
    print(f"DEBUG: 读取加密文件: {encrypted_path}")
    with open(encrypted_path, 'rb') as f:
        encrypted_data = f.read()
    print(f"DEBUG: 读取到 {len(encrypted_data) / (1024*1024):.2f} MB 加密数据")

    # 提取 salt, iv, ciphertext
    salt = encrypted_data[:16]
    iv = encrypted_data[16:32]
    ciphertext = encrypted_data[32:]
    print(f"DEBUG: 解析加密数据结构完成")

    # 派生密钥
    print("DEBUG: 开始密钥派生（PBKDF2 100000次迭代，预计需要5-10秒）...")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())
    print("DEBUG: 密钥派生完成")

    # 解密
    print("DEBUG: 开始AES解密...")
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    plaintext_padded = decryptor.update(ciphertext) + decryptor.finalize()
    print("DEBUG: AES解密完成")

    # 移除填充
    padding_length = plaintext_padded[-1]
    plaintext = plaintext_padded[:-padding_length]
    print(f"DEBUG: 去除填充完成，最终数据大小 {len(plaintext) / (1024*1024):.2f} MB")

    return plaintext

def lazy_load_classifier():
    """懒加载 PyTorch 分类模型（支持加密模型）"""
    global classifier
    if classifier is None:
        print("正在加载AI模型...")
        print(f"DEBUG: script_dir = {script_dir}")
        print(f"DEBUG: sys.frozen = {getattr(sys, 'frozen', False)}")
        if getattr(sys, 'frozen', False):
            print(f"DEBUG: sys._MEIPASS = {sys._MEIPASS}")

        # 固定密码（与加密工具相同）
        SECRET_PASSWORD = "SuperBirdID_2024_AI_Model_Encryption_Key_v1"

        # 检查是否存在加密模型
        encrypted_model_path = PYTORCH_CLASSIFICATION_MODEL_PATH + '.enc'
        print(f"DEBUG: 基础模型路径 = {PYTORCH_CLASSIFICATION_MODEL_PATH}")
        print(f"DEBUG: 加密模型路径 = {encrypted_model_path}")
        print(f"DEBUG: 加密模型存在? {os.path.exists(encrypted_model_path)}")
        print(f"DEBUG: 未加密模型存在? {os.path.exists(PYTORCH_CLASSIFICATION_MODEL_PATH)}")

        if os.path.exists(encrypted_model_path):
            # 加载加密模型
            print("检测到加密模型，正在解密...")
            try:
                model_data = decrypt_model(encrypted_model_path, SECRET_PASSWORD)
                print(f"DEBUG: 解密后数据大小 = {len(model_data) / (1024*1024):.2f} MB")

                # 将解密的数据写入临时文件
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pt') as tmp_file:
                    tmp_file.write(model_data)
                    tmp_model_path = tmp_file.name

                print(f"DEBUG: 临时模型文件 = {tmp_model_path}")

                # 加载临时模型文件到 CPU
                classifier = torch.jit.load(tmp_model_path, map_location='cpu')
                classifier.eval()

                # 删除临时文件
                try:
                    os.unlink(tmp_model_path)
                except:
                    pass

                print(f"✓ 加密模型加载完成 (设备: cpu)")
            except Exception as e:
                print(f"❌ 加密模型加载失败: {e}")
                import traceback
                traceback.print_exc()
                # 回退到未加密模型
                if os.path.exists(PYTORCH_CLASSIFICATION_MODEL_PATH):
                    print("尝试加载未加密模型...")
                    classifier = torch.jit.load(PYTORCH_CLASSIFICATION_MODEL_PATH, map_location='cpu')
                    classifier.eval()
                    print(f"✓ 未加密模型加载完成 (设备: cpu)")
                else:
                    raise RuntimeError("无法加载模型：加密模型解密失败且未找到未加密模型")
        else:
            # 加载未加密模型
            print("未找到加密模型，尝试加载未加密模型...")
            if os.path.exists(PYTORCH_CLASSIFICATION_MODEL_PATH):
                classifier = torch.jit.load(PYTORCH_CLASSIFICATION_MODEL_PATH, map_location='cpu')
                classifier.eval()
                print(f"✓ 未加密模型加载完成 (设备: cpu)")
            else:
                raise RuntimeError(f"未找到模型文件: {PYTORCH_CLASSIFICATION_MODEL_PATH}")

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


# 验证关键文件是否存在
def verify_files():
    """快速验证关键文件"""
    required_files = [
        PYTORCH_CLASSIFICATION_MODEL_PATH,
        BIRD_INFO_PATH
    ]

    missing_files = []
    for file_path in required_files:
        # 对于模型文件，检查是否存在加密版本
        if file_path == PYTORCH_CLASSIFICATION_MODEL_PATH:
            if not os.path.exists(file_path) and not os.path.exists(file_path + '.enc'):
                missing_files.append(os.path.basename(file_path) + ' (或 .enc)')
        else:
            if not os.path.exists(file_path):
                missing_files.append(os.path.basename(file_path))

    if missing_files:
        print(f"✗ 缺少必要文件: {', '.join(missing_files)}")
        sys.exit(1)
    else:
        # 检查是否使用加密模型
        if os.path.exists(PYTORCH_CLASSIFICATION_MODEL_PATH + '.enc'):
            print("✓ 文件完整性检查通过 (使用加密模型)")
        else:
            print("✓ 文件完整性检查通过")

# 启动时只进行文件验证
verify_files()

def extract_gps_from_exif_exiftool(image_path):
    """
    使用ExifTool从图像EXIF数据中提取GPS坐标（更强大、更可靠）
    返回: (latitude, longitude, location_info) 或 (None, None, None)
    """
    import threading
    import queue

    result_queue = queue.Queue()
    exception_queue = queue.Queue()

    def _exiftool_worker():
        """ExifTool工作线程"""
        try:
            print(f"DEBUG: ExifTool路径: {EXIFTOOL_PATH}")
            print(f"DEBUG: ExifTool存在? {os.path.exists(EXIFTOOL_PATH)}")
            print(f"DEBUG: 开始创建ExifToolHelper...")
            with exiftool.ExifToolHelper(executable=EXIFTOOL_PATH) as et:
                print(f"DEBUG: ExifToolHelper创建成功，开始读取元数据...")
                metadata = et.get_metadata(image_path)
                print(f"DEBUG: 元数据读取完成")

                if not metadata or len(metadata) == 0:
                    result_queue.put((None, None, "无EXIF数据"))
                    return

                data = metadata[0]

                # ExifTool提供已计算好的GPS坐标
                lat = data.get('Composite:GPSLatitude')
                lon = data.get('Composite:GPSLongitude')

                if lat is not None and lon is not None:
                    location_info = f"GPS: {lat:.6f}, {lon:.6f} (ExifTool)"
                    result_queue.put((lat, lon, location_info))
                else:
                    result_queue.put((None, None, "无GPS数据"))

        except Exception as e:
            exception_queue.put(e)

    # 启动工作线程
    worker_thread = threading.Thread(target=_exiftool_worker, daemon=True)
    worker_thread.start()

    # 等待结果，最多5秒
    worker_thread.join(timeout=5.0)

    if worker_thread.is_alive():
        # 超时了，线程还在运行
        print("DEBUG: ExifTool超时（5秒），使用PIL fallback")
        return None, None, "ExifTool超时"

    # 检查是否有异常
    if not exception_queue.empty():
        e = exception_queue.get()
        print(f"DEBUG: ExifTool异常: {e}")
        return None, None, f"ExifTool GPS解析失败: {e}"

    # 检查是否有结果
    if not result_queue.empty():
        return result_queue.get()

    return None, None, "ExifTool无响应"

def extract_gps_from_exif_pil(image_path):
    """
    使用PIL从图像EXIF数据中提取GPS坐标（Fallback方案）
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
        return None, None, f"PIL GPS解析失败: {e}"

def extract_gps_from_exif(image_path):
    """
    从图像EXIF数据中提取GPS坐标（智能选择最佳方法）
    优先使用ExifTool，失败则fallback到PIL
    返回: (latitude, longitude, location_info) 或 (None, None, None)
    """
    # 优先使用ExifTool（如果可用）
    if EXIFTOOL_AVAILABLE:
        lat, lon, info = extract_gps_from_exif_exiftool(image_path)
        if lat is not None and lon is not None:
            # 成功读取到GPS数据
            return lat, lon, info
        elif info in ["无GPS数据", "无EXIF数据"]:
            # exiftool读取成功，但照片确实没有GPS数据，直接返回，不需要fallback
            print(f"DEBUG: ExifTool读取完成，{info}")
            return None, None, info
        else:
            # exiftool读取失败（超时、异常等），尝试PIL fallback
            print(f"DEBUG: ExifTool读取失败({info})，使用PIL fallback...")

    # 使用PIL fallback
    print("DEBUG: 使用PIL读取GPS...")
    return extract_gps_from_exif_pil(image_path)

def write_bird_name_to_exif(image_path, bird_name):
    """
    将鸟种名称写入图片EXIF的Title字段
    仅支持JPEG和RAW格式，跳过PNG等粘贴格式

    Args:
        image_path: 图片路径
        bird_name: 鸟种名称（中文或英文）

    Returns:
        (success: bool, message: str)
    """
    # 检查文件是否存在
    if not os.path.exists(image_path):
        return False, f"文件不存在: {image_path}"

    # 获取文件扩展名
    file_ext = os.path.splitext(image_path)[1].lower()

    # 支持的格式列表
    supported_formats = [
        '.jpg', '.jpeg', '.jpe', '.jfif',  # JPEG
        '.cr2', '.cr3',     # Canon RAW
        '.nef', '.nrw',     # Nikon RAW
        '.arw', '.srf',     # Sony RAW
        '.dng',             # Adobe RAW
        '.raf',             # Fujifilm RAW
        '.orf',             # Olympus RAW
        '.rw2',             # Panasonic RAW
        '.pef',             # Pentax RAW
        '.srw',             # Samsung RAW
        '.raw',             # 通用RAW
        '.rwl',             # Leica RAW
    ]

    # 跳过不支持的格式（如PNG）
    if file_ext not in supported_formats:
        return False, f"跳过格式 {file_ext}（仅支持JPEG和RAW格式）"

    # 必须使用ExifTool才能写入
    if not EXIFTOOL_AVAILABLE:
        return False, "ExifTool不可用，无法写入EXIF"

    try:
        with exiftool.ExifToolHelper(executable=EXIFTOOL_PATH) as et:
            # 写入Title字段（EXIF:ImageDescription）
            et.set_tags(
                image_path,
                tags={
                    "EXIF:ImageDescription": bird_name,
                    "XMP:Title": bird_name,
                },
                params=["-overwrite_original"]  # 不创建备份文件
            )

        return True, f"✓ 已写入EXIF Title: {bird_name}"

    except Exception as e:
        return False, f"写入EXIF失败: {e}"

def get_bird_description_from_db(bird_cn_name):
    """
    从数据库中读取鸟种的详细中文介绍

    Args:
        bird_cn_name: 鸟种中文名

    Returns:
        dict: {
            'cn_name': str,
            'en_name': str,
            'scientific_name': str,
            'short_description': str,
            'full_description': str,
            'ebird_code': str
        } 或 None（如果未找到）
    """
    import sqlite3

    try:
        # 连接数据库
        db_path = os.path.join(script_dir, 'bird_reference.sqlite')
        if not os.path.exists(db_path):
            return None

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 查询鸟种信息
        cursor.execute("""
            SELECT
                chinese_simplified,
                english_name,
                scientific_name,
                short_description_zh,
                full_description_zh,
                ebird_code
            FROM BirdCountInfo
            WHERE chinese_simplified = ?
            LIMIT 1
        """, (bird_cn_name,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'cn_name': row[0],
                'en_name': row[1],
                'scientific_name': row[2],
                'short_description': row[3] or '',
                'full_description': row[4] or '',
                'ebird_code': row[5] or ''
            }
        else:
            return None

    except Exception as e:
        print(f"读取鸟种信息失败: {e}")
        return None

def write_bird_caption_to_exif(image_path, caption_text):
    """
    将鸟种描述写入图片EXIF的Caption字段
    仅支持JPEG和RAW格式

    Args:
        image_path: 图片路径
        caption_text: 描述文本

    Returns:
        (success: bool, message: str)
    """
    # 检查文件是否存在
    if not os.path.exists(image_path):
        return False, f"文件不存在: {image_path}"

    # 获取文件扩展名
    file_ext = os.path.splitext(image_path)[1].lower()

    # 支持的格式列表
    supported_formats = [
        '.jpg', '.jpeg', '.jpe', '.jfif',  # JPEG
        '.cr2', '.cr3', '.nef', '.nrw', '.arw', '.srf', '.dng',
        '.raf', '.orf', '.rw2', '.pef', '.srw', '.raw', '.rwl',
    ]

    # 跳过不支持的格式
    if file_ext not in supported_formats:
        return False, f"跳过格式 {file_ext}（仅支持JPEG和RAW格式）"

    # 必须使用ExifTool才能写入
    if not EXIFTOOL_AVAILABLE:
        return False, "ExifTool不可用，无法写入EXIF"

    try:
        with exiftool.ExifToolHelper(executable=EXIFTOOL_PATH) as et:
            # 写入Caption字段
            et.set_tags(
                image_path,
                tags={
                    "EXIF:ImageDescription": caption_text,
                    "XMP:Description": caption_text,
                    "IPTC:Caption-Abstract": caption_text,
                },
                params=["-overwrite_original"]
            )

        return True, f"✓ 已写入EXIF Caption"

    except Exception as e:
        return False, f"写入EXIF Caption失败: {e}"

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
        print(f"🔍 检测到RAW格式: {file_ext.upper()}")
        print(f"📸 正在处理RAW文件...")

        # 策略1: 优先尝试使用ExifTool提取内嵌JPEG（适用于压缩RAW格式）
        if EXIFTOOL_AVAILABLE:
            try:
                import tempfile
                print("  方法1: 尝试从RAW中提取内嵌JPEG...")

                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    tmp_jpg_path = tmp_file.name

                # 尝试提取 JpgFromRaw（全分辨率JPEG）
                import subprocess
                result = subprocess.run(
                    [EXIFTOOL_PATH, '-b', '-JpgFromRaw', image_path],
                    capture_output=True,
                    timeout=10
                )

                if result.returncode == 0 and len(result.stdout) > 1000:
                    # 成功提取到JPEG数据
                    with open(tmp_jpg_path, 'wb') as f:
                        f.write(result.stdout)

                    try:
                        image = Image.open(tmp_jpg_path).convert("RGB")
                        os.unlink(tmp_jpg_path)  # 删除临时文件
                        print(f"✓ RAW图像加载成功，尺寸: {image.size}")
                        print(f"  使用方法: 内嵌JPEG提取 (全分辨率)")
                        return image
                    except Exception as e:
                        os.unlink(tmp_jpg_path)
                        print(f"  内嵌JPEG解析失败: {e}")
                else:
                    # 没有 JpgFromRaw，尝试提取 PreviewImage
                    result = subprocess.run(
                        [EXIFTOOL_PATH, '-b', '-PreviewImage', image_path],
                        capture_output=True,
                        timeout=10
                    )

                    if result.returncode == 0 and len(result.stdout) > 1000:
                        with open(tmp_jpg_path, 'wb') as f:
                            f.write(result.stdout)

                        try:
                            image = Image.open(tmp_jpg_path).convert("RGB")
                            os.unlink(tmp_jpg_path)
                            print(f"✓ RAW图像加载成功，尺寸: {image.size}")
                            print(f"  使用方法: 预览JPEG提取 (可能低分辨率)")
                            return image
                        except Exception as e:
                            os.unlink(tmp_jpg_path)
                            print(f"  预览JPEG解析失败: {e}")
                    else:
                        if os.path.exists(tmp_jpg_path):
                            os.unlink(tmp_jpg_path)
            except Exception as e:
                print(f"  ExifTool提取失败: {e}")

        # 策略2: 使用rawpy处理RAW文件（如果ExifTool失败或不可用）
        if RAW_SUPPORT:
            try:
                print("  方法2: 尝试使用rawpy解码RAW...")

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
                print(f"  使用方法: rawpy解码 (完整RAW处理)")

                return image

            except rawpy.LibRawError as e:
                print(f"  rawpy解码失败: {e}")
                # 继续尝试下一个方法
            except Exception as e:
                print(f"  rawpy处理失败: {e}")
        elif not EXIFTOOL_AVAILABLE:
            # 两种方法都不可用
            raise ImportError(
                f"检测到RAW格式 ({file_ext})，但处理库未安装。\n"
                f"请安装以下任一方案:\n"
                f"  1. pip install rawpy imageio (推荐，完整RAW处理)\n"
                f"  2. pip install pyexiftool (轻量，提取内嵌JPEG)"
            )

        # 如果所有RAW处理方法都失败
        raise Exception(
            f"RAW文件 ({file_ext}) 处理失败，已尝试所有可用方法:\n"
            f"  ✗ ExifTool内嵌JPEG提取: {'已尝试' if EXIFTOOL_AVAILABLE else '不可用'}\n"
            f"  ✗ rawpy RAW解码: {'已尝试' if RAW_SUPPORT else '不可用'}\n"
            f"建议: 使用相机自带软件将RAW转换为JPEG格式"
        )

    else:
        # 标准格式 (JPG, PNG, TIFF等)
        try:
            image = Image.open(image_path).convert("RGB")
            print(f"✓ 图像加载成功，尺寸: {image.size}")
            return image
        except Exception as e:
            raise Exception(f"图像加载失败: {e}")

# GPS 查询缓存（减少重复计算）
_gps_cache = {}

def get_region_from_gps(latitude, longitude):
    """
    根据GPS坐标确定地理区域和对应的eBird国家代码
    优先使用离线地理数据库，失败时回退到粗粒度判断
    返回: (region_name, country_code, region_info)
    """
    if latitude is None or longitude is None:
        return None, None, "无GPS坐标"

    # 检查缓存（四舍五入到小数点后2位，约1km精度）
    cache_key = (round(latitude, 2), round(longitude, 2))
    if cache_key in _gps_cache:
        return _gps_cache[cache_key]

    # 方法 1: 使用 reverse_geocoder 离线数据库（优先）
    try:
        import reverse_geocoder as rg
        results = rg.search((latitude, longitude), mode=1)  # mode=1: 单点查询
        if results and len(results) > 0:
            result = results[0]
            country_code = result.get('cc', '').upper()  # ISO 国家代码
            location_name = result.get('name', '')  # 地点名称

            if country_code:
                region_info = f"GPS定位: {location_name}, {country_code} ({latitude:.3f}, {longitude:.3f})"
                result_tuple = (location_name, country_code, region_info)
                _gps_cache[cache_key] = result_tuple
                return result_tuple
    except Exception as e:
        print(f"DEBUG: reverse_geocoder 失败: {e}")
        # 继续尝试 fallback 方法

    # 方法 2: 回退到粗粒度地理区域判断（保留作为 fallback）
    region_map = [
        # 澳洲和大洋洲
        {
            'name': 'Australia',
            'country': 'AU',
            'bounds': [(-50, 110), (-10, 180)],
            'description': '澳大利亚（粗略）'
        },
        # 亚洲
        {
            'name': 'Asia',
            'country': 'CN',
            'bounds': [(-10, 60), (80, 180)],
            'description': '亚洲（粗略）'
        },
        # 欧洲
        {
            'name': 'Europe',
            'country': 'DE',
            'bounds': [(35, -25), (80, 60)],
            'description': '欧洲（粗略）'
        },
        # 北美洲
        {
            'name': 'North_America',
            'country': 'US',
            'bounds': [(15, -170), (80, -50)],
            'description': '北美洲（粗略）'
        },
        # 南美洲
        {
            'name': 'South_America',
            'country': 'BR',
            'bounds': [(-60, -90), (15, -30)],
            'description': '南美洲（粗略）'
        },
        # 非洲
        {
            'name': 'Africa',
            'country': 'ZA',
            'bounds': [(-40, -20), (40, 55)],
            'description': '非洲（粗略）'
        }
    ]

    for region in region_map:
        (lat_min, lon_min), (lat_max, lon_max) = region['bounds']

        if (lat_min <= latitude <= lat_max and
            lon_min <= longitude <= lon_max):

            region_info = f"GPS定位: {region['description']} ({latitude:.3f}, {longitude:.3f})"
            result_tuple = (region['name'], region['country'], region_info)
            _gps_cache[cache_key] = result_tuple
            return result_tuple

    # 默认返回
    result_tuple = (None, None, f"未知区域 ({latitude:.3f}, {longitude:.3f})")
    _gps_cache[cache_key] = result_tuple
    return result_tuple

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

    # 推理（模型和输入都在 CPU 上）
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
                # 优先使用数据库查询
                bird_name_cn = None
                bird_name_en = None

                if db_manager:
                    bird_info = db_manager.get_bird_by_class_id(class_id)
                    if bird_info:
                        bird_name_cn = bird_info['chinese_simplified']
                        bird_name_en = bird_info['english_name']

                # 如果数据库查询失败，回退到 bird_data
                if not bird_name_cn and class_id < len(bird_data) and len(bird_data[class_id]) >= 2:
                    bird_name_cn = bird_data[class_id][0]
                    bird_name_en = bird_data[class_id][1]

                if bird_name_cn and bird_name_en:
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

        # 检查是否已有该位置的缓存
        if EBIRD_FILTER_AVAILABLE:
            EBIRD_API_KEY = os.environ.get('EBIRD_API_KEY', '60nan25sogpo')
            cache_dir = os.path.join(get_user_data_dir(), 'ebird_cache')
            temp_filter = eBirdCountryFilter(EBIRD_API_KEY, cache_dir=cache_dir, offline_dir=os.path.join(script_dir, "offline_ebird_data"))
            cache_file = temp_filter.get_location_cache_file_path(latitude, longitude, 25)
            has_cache = temp_filter.is_cache_valid(cache_file)

            if not has_cache:
                print(f"\n💡 提示: 检测到GPS位置数据，但本地暂无缓存")
                print(f"   可以获取该位置25km范围内的鸟类观察记录")
                print(f"   数据将缓存到: {cache_dir}/")
                print(f"   缓存有效期: 30天")
                fetch_choice = input("是否立即获取当地鸟类数据？(y/n，直接回车为是): ").strip().lower()

                if fetch_choice in ['', 'y', 'yes']:
                    print(f"\n正在从eBird获取 ({latitude:.3f}, {longitude:.3f}) 附近数据...")
                    species_list = temp_filter.get_location_species_list(latitude, longitude, 25)
                    if species_list:
                        # 获取缓存详情
                        cache_info = temp_filter.get_location_cache_info(latitude, longitude, 25)
                        if cache_info:
                            obs_count = cache_info.get('observation_count', len(species_list))
                            print(f"✓ 成功获取 {len(species_list)} 个物种（基于 {obs_count} 条观察记录）")
                        else:
                            print(f"✓ 成功获取并缓存 {len(species_list)} 个物种的数据")
                        print(f"   缓存文件: {cache_file}")
                    else:
                        print("⚠ 获取失败，将使用现有数据")
                else:
                    print("跳过获取，将使用现有数据")
            else:
                # 显示缓存详情
                cache_info = temp_filter.get_location_cache_info(latitude, longitude, 25)
                if cache_info:
                    species_count = cache_info.get('species_count', 0)
                    obs_count = cache_info.get('observation_count', species_count)
                    print(f"✓ 本地已有缓存: {species_count} 个物种（基于 {obs_count} 条观察记录）")
                else:
                    print(f"✓ 本地已有该位置的缓存数据")

        print("\n筛选选项: 1.GPS精确位置(25km) 2.国家级别 3.手动选择")
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

            # 检查离线数据可用性
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
                # 有离线数据，显示所有可用国家（与无GPS时的逻辑相同）
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
                # 没有离线数据，直接使用全球模式
                print("⚠ 未检测到离线eBird数据")
                print("💡 将使用全球模式（无地理过滤）")
                print("   提示：如需地理过滤，请下载离线eBird数据包")
                user_region = None
                country_code = None

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
            # 没有离线数据，且无GPS信息，直接使用全球模式
            print("⚠ 未检测到离线eBird数据，且无GPS信息")
            print("💡 将使用全球模式（无地理过滤）")
            print("   提示：如需地理过滤，请：")
            print("   1. 使用带GPS信息的照片，或")
            print("   2. 下载离线eBird数据包")
            user_region = None
            country_code = None

    # eBird国家物种过滤设置
    country_filter = None
    ebird_species_set = None

    if EBIRD_FILTER_AVAILABLE and (country_code or (use_precise_gps and latitude is not None and longitude is not None)):
        try:
            # eBird API密钥（优先使用环境变量，否则使用默认值）
            EBIRD_API_KEY = os.environ.get('EBIRD_API_KEY', '60nan25sogpo')
            cache_dir = os.path.join(get_user_data_dir(), 'ebird_cache')
            country_filter = eBirdCountryFilter(EBIRD_API_KEY, cache_dir=cache_dir, offline_dir=os.path.join(script_dir, "offline_ebird_data"))

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

