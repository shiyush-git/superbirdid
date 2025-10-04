#!/usr/bin/env python3
"""
置信度提升工具
针对低置信度问题的多策略解决方案
"""
import torch
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2
from typing import List, Tuple, Dict, Optional
import time

# 导入原始模块
from SuperBirdId import lazy_load_classifier, lazy_load_bird_info, lazy_load_database

# ============================================
# 策略1: 测试时增强 (Test-Time Augmentation)
# ============================================
class TTABooster:
    """测试时增强 - 通过多次推理平均提高置信度"""

    def __init__(self):
        self.augmentations = [
            ('原始', self.no_aug),
            ('水平翻转', self.horizontal_flip),
            ('轻微旋转+5度', lambda img: self.rotate(img, 5)),
            ('轻微旋转-5度', lambda img: self.rotate(img, -5)),
            ('亮度增强', self.brightness_up),
            ('对比度增强', self.contrast_up),
            ('锐化', self.sharpen),
            ('中心裁剪', self.center_crop),
        ]

    def no_aug(self, img):
        return img

    def horizontal_flip(self, img):
        return img.transpose(Image.FLIP_LEFT_RIGHT)

    def rotate(self, img, degrees):
        return img.rotate(degrees, resample=Image.BICUBIC, expand=False)

    def brightness_up(self, img):
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(1.15)  # 提高15%亮度

    def contrast_up(self, img):
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(1.2)  # 提高20%对比度

    def sharpen(self, img):
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(1.5)  # 提高50%锐度

    def center_crop(self, img):
        """中心裁剪90% - 去除边缘干扰"""
        w, h = img.size
        crop_w, crop_h = int(w * 0.9), int(h * 0.9)
        left = (w - crop_w) // 2
        top = (h - crop_h) // 2
        return img.crop((left, top, left + crop_w, top + crop_h))

    def predict_with_tta(self, image: Image.Image, model, preprocess_func,
                         top_k: int = 5) -> Dict:
        """
        使用TTA进行预测

        Args:
            image: PIL图像
            model: PyTorch模型
            preprocess_func: 预处理函数
            top_k: 返回前k个结果

        Returns:
            增强后的预测结果
        """
        all_predictions = []

        print(f"🔄 开始TTA (测试时增强): {len(self.augmentations)}种变换...")

        for aug_name, aug_func in self.augmentations:
            # 应用增强
            aug_image = aug_func(image)

            # 预处理
            processed = preprocess_func(aug_image)

            # 推理
            with torch.no_grad():
                output = model(processed)

            probs = torch.nn.functional.softmax(output[0], dim=0)
            all_predictions.append(probs.numpy())

        # 平均所有预测
        avg_probs = np.mean(all_predictions, axis=0)
        std_probs = np.std(all_predictions, axis=0)

        # 获取top-k结果
        top_indices = np.argsort(avg_probs)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            results.append({
                'class_id': int(idx),
                'avg_confidence': float(avg_probs[idx] * 100),
                'std': float(std_probs[idx] * 100),
                'min': float((avg_probs[idx] - std_probs[idx]) * 100),
                'max': float((avg_probs[idx] + std_probs[idx]) * 100),
            })

        print(f"✓ TTA完成，平均置信度提升: "
              f"{results[0]['avg_confidence']:.2f}% (±{results[0]['std']:.2f}%)")

        return {
            'method': 'TTA-8种增强',
            'results': results,
            'all_predictions': all_predictions
        }


# ============================================
# 策略2: 多尺度融合
# ============================================
class MultiScaleBooster:
    """多尺度预测融合"""

    def __init__(self):
        self.scales = [
            (224, '标准224'),
            (256, '大尺寸256'),
            (192, '小尺寸192'),
            (288, '超大尺寸288'),
        ]

    def predict_multiscale(self, image: Image.Image, model, top_k: int = 5) -> Dict:
        """多尺度预测"""
        all_predictions = []

        print(f"📐 开始多尺度预测: {len(self.scales)}种尺寸...")

        for size, name in self.scales:
            # 调整尺寸
            resized = image.resize((size, size), Image.LANCZOS)

            # 标准化
            img_array = np.array(resized)
            bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            mean = np.array([0.406, 0.456, 0.485])
            std = np.array([0.225, 0.224, 0.229])

            normalized = (bgr_array / 255.0 - mean) / std
            tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

            # 推理
            with torch.no_grad():
                output = model(tensor)

            probs = torch.nn.functional.softmax(output[0], dim=0).numpy()
            all_predictions.append(probs)

        # 加权平均 (大尺寸权重更高)
        weights = np.array([1.0, 1.2, 0.8, 1.3])
        weights = weights / weights.sum()

        weighted_avg = np.average(all_predictions, axis=0, weights=weights)

        # 获取top-k
        top_indices = np.argsort(weighted_avg)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            results.append({
                'class_id': int(idx),
                'confidence': float(weighted_avg[idx] * 100)
            })

        print(f"✓ 多尺度完成，最高置信度: {results[0]['confidence']:.2f}%")

        return {
            'method': '多尺度融合',
            'results': results
        }


# ============================================
# 策略3: 智能YOLO裁剪优化
# ============================================
class SmartCropBooster:
    """智能裁剪策略"""

    def __init__(self, yolo_model_path='yolo11x.pt'):
        try:
            from ultralytics import YOLO
            self.yolo = YOLO(yolo_model_path)
            self.available = True
        except:
            self.available = False
            print("⚠ YOLO不可用，跳过智能裁剪")

    def get_best_crop(self, image_path: str) -> Optional[Image.Image]:
        """获取最佳裁剪区域"""
        if not self.available:
            return None

        results = self.yolo(image_path, conf=0.15)  # 降低阈值捕获更多候选

        bird_detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0].cpu().numpy())
                    if class_id == 14:  # 鸟类
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        area = (x2 - x1) * (y2 - y1)

                        bird_detections.append({
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': float(confidence),
                            'area': float(area)
                        })

        if not bird_detections:
            return None

        # 选择最大且置信度最高的检测
        best = max(bird_detections,
                   key=lambda x: x['confidence'] * (x['area'] ** 0.5))

        image = Image.open(image_path).convert('RGB')
        x1, y1, x2, y2 = best['bbox']

        # 智能边距：面积越小，边距越大
        area_ratio = best['area'] / (image.width * image.height)
        padding = int(max(50, 200 * (1 - area_ratio)))

        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(image.width, x2 + padding)
        y2 = min(image.height, y2 + padding)

        cropped = image.crop((x1, y1, x2, y2))

        print(f"✂️  智能裁剪: {cropped.size}, 边距={padding}px, "
              f"YOLO置信度={best['confidence']:.2f}")

        return cropped


# ============================================
# 策略4: 温度缩放校准
# ============================================
class TemperatureScaling:
    """温度缩放 - 校准模型输出概率"""

    def __init__(self, temperature: float = 1.5):
        """
        Args:
            temperature: 温度参数
                - T > 1: 软化分布，提高低概率类的相对置信度
                - T < 1: 锐化分布，强化高概率类
                - T = 1: 不变
        """
        self.temperature = temperature

    def apply(self, logits: torch.Tensor) -> torch.Tensor:
        """应用温度缩放"""
        scaled_logits = logits / self.temperature
        return torch.nn.functional.softmax(scaled_logits, dim=0)

    def calibrate(self, model, image_tensor: torch.Tensor,
                  temperatures: List[float] = [0.8, 1.0, 1.2, 1.5, 2.0]) -> Dict:
        """测试不同温度"""
        with torch.no_grad():
            logits = model(image_tensor)[0]

        results = {}
        for T in temperatures:
            scaled_probs = self.apply(logits * 1.0, T)  # 克隆避免修改
            max_prob = scaled_probs.max().item()
            max_idx = scaled_probs.argmax().item()

            results[T] = {
                'max_confidence': max_prob * 100,
                'class_id': max_idx,
                'probabilities': scaled_probs
            }

        return results


# ============================================
# 主函数：综合提升策略
# ============================================
def boost_confidence(image_path: str,
                     strategy: str = 'all',
                     ebird_filter_set: Optional[set] = None) -> Dict:
    """
    综合置信度提升

    Args:
        image_path: 图像路径
        strategy: 'tta' | 'multiscale' | 'crop' | 'all'
        ebird_filter_set: eBird过滤物种集合

    Returns:
        提升后的识别结果
    """
    print(f"\n{'='*60}")
    print(f"🚀 置信度提升工具")
    print(f"{'='*60}")
    print(f"图像: {image_path}")
    print(f"策略: {strategy}")

    # 加载模型和数据
    model = lazy_load_classifier()
    bird_info = lazy_load_bird_info()
    db_manager = lazy_load_database()

    # 加载图像
    original_image = Image.open(image_path).convert('RGB')

    # 策略1: 智能裁剪 (如果需要)
    if strategy in ['crop', 'all']:
        crop_booster = SmartCropBooster()
        cropped = crop_booster.get_best_crop(image_path)
        if cropped:
            original_image = cropped

    # 预处理函数
    def preprocess(img):
        # 使用传统256→224方法
        resized = img.resize((256, 256), Image.LANCZOS)
        cropped = resized.crop((16, 16, 240, 240))

        img_array = np.array(cropped)
        bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        mean = np.array([0.406, 0.456, 0.485])
        std = np.array([0.225, 0.224, 0.229])

        normalized = (bgr_array / 255.0 - mean) / std
        return torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

    all_results = {}

    # 策略2: TTA
    if strategy in ['tta', 'all']:
        tta_booster = TTABooster()
        tta_result = tta_booster.predict_with_tta(original_image, model, preprocess)
        all_results['tta'] = tta_result

    # 策略3: 多尺度
    if strategy in ['multiscale', 'all']:
        ms_booster = MultiScaleBooster()
        ms_result = ms_booster.predict_multiscale(original_image, model)
        all_results['multiscale'] = ms_result

    # 融合所有结果
    final_results = merge_results(all_results, bird_info, db_manager, ebird_filter_set)

    # 打印最终结果
    print(f"\n{'='*60}")
    print(f"📊 最终识别结果 (提升后)")
    print(f"{'='*60}")

    for i, result in enumerate(final_results[:5], 1):
        ebird_tag = "🌍" if result.get('ebird_match') else ""
        print(f"{i}. {result['name']}")
        print(f"   置信度: {result['confidence']:.2f}% {ebird_tag}")
        if 'confidence_range' in result:
            print(f"   范围: {result['confidence_range']}")

    return final_results


def merge_results(all_results: Dict, bird_info: List, db_manager,
                  ebird_filter: Optional[set] = None) -> List[Dict]:
    """融合多种策略的结果"""

    # 收集所有候选
    class_scores = {}

    # TTA结果 (权重: 1.5)
    if 'tta' in all_results:
        for res in all_results['tta']['results']:
            cid = res['class_id']
            class_scores[cid] = class_scores.get(cid, 0) + res['avg_confidence'] * 1.5

    # 多尺度结果 (权重: 1.2)
    if 'multiscale' in all_results:
        for res in all_results['multiscale']['results']:
            cid = res['class_id']
            class_scores[cid] = class_scores.get(cid, 0) + res['confidence'] * 1.2

    # 排序
    sorted_classes = sorted(class_scores.items(), key=lambda x: x[1], reverse=True)

    # 构建最终结果
    final = []
    for class_id, score in sorted_classes[:10]:
        if class_id < len(bird_info) and len(bird_info[class_id]) >= 2:
            cn_name = bird_info[class_id][0]
            en_name = bird_info[class_id][1]

            result = {
                'class_id': class_id,
                'confidence': score,
                'chinese_name': cn_name,
                'english_name': en_name,
                'name': f"{cn_name} ({en_name})"
            }

            # eBird匹配检查
            if db_manager and ebird_filter:
                ebird_code = db_manager.get_ebird_code_by_english_name(en_name)
                if ebird_code and ebird_code in ebird_filter:
                    result['ebird_match'] = True
                    result['confidence'] *= 1.3  # 额外30%提升

            final.append(result)

    # 重新排序
    final.sort(key=lambda x: x['confidence'], reverse=True)

    return final


# ============================================
# 测试入口
# ============================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python confidence_booster.py <图片路径> [策略]")
        print("策略选项: tta, multiscale, crop, all (默认)")
        sys.exit(1)

    image_path = sys.argv[1]
    strategy = sys.argv[2] if len(sys.argv) > 2 else 'all'

    results = boost_confidence(image_path, strategy)
