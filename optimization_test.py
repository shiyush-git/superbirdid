#!/usr/bin/env python3
"""
鸟类识别优化测试工具
对比各种优化方案的识别效果，量化改进效果
"""
import os
import sys
import time
import json
import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
from pathlib import Path

# 导入原始模块
try:
    from SuperBirdId import lazy_load_classifier, lazy_load_bird_info, YOLOBirdDetector
    from ebird_country_filter import eBirdCountryFilter
    from bird_database_manager import BirdDatabaseManager
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

class BirdIDOptimizationTester:
    def __init__(self, test_images_dir: str = None):
        """
        初始化优化测试器

        Args:
            test_images_dir: 测试图像目录路径
        """
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_images_dir = test_images_dir or self.script_dir

        # 懒加载组件
        self.model = None
        self.bird_info = None
        self.yolo_detector = None
        self.db_manager = None

        # 测试结果存储
        self.test_results = []

        # 测试配置
        self.test_configs = {
            'preprocessing': {
                'original': '原始方法',
                'direct_224': '直接224x224',
                'traditional_256_224': '传统256→224',
                'smart_adaptive': '智能自适应'
            },
            'confidence_thresholds': {
                'strict': 5.0,     # 严格阈值 5%
                'normal': 1.0,     # 正常阈值 1%
                'loose': 0.1,      # 宽松阈值 0.1%
                'dynamic': 'auto'  # 动态阈值
            },
            'yolo_confidence': {
                'conservative': 0.5,  # 保守 50%
                'normal': 0.25,       # 正常 25%
                'aggressive': 0.1     # 激进 10%
            },
            'enhancement_methods': {
                'none': '无增强',
                'unsharp_mask': 'UnsharpMask增强',
                'contrast_edge': '对比度+边缘增强',
                'desaturate': '降饱和度'
            }
        }

        print(f"🔬 鸟类识别优化测试器初始化完成")
        print(f"测试目录: {self.test_images_dir}")

    def _lazy_load_components(self):
        """懒加载所需组件"""
        if self.model is None:
            print("加载AI模型...")
            self.model = lazy_load_classifier()

        if self.bird_info is None:
            print("加载鸟类数据...")
            self.bird_info = lazy_load_bird_info()

        if self.yolo_detector is None:
            print("初始化YOLO检测器...")
            self.yolo_detector = YOLOBirdDetector()

        try:
            if self.db_manager is None:
                self.db_manager = BirdDatabaseManager()
        except:
            print("⚠ 数据库管理器加载失败，将使用JSON数据")

    def preprocess_image_original(self, image: Image.Image) -> Tuple[np.ndarray, str]:
        """原始预处理方法"""
        # 直接使用smart_resize的逻辑
        width, height = image.size
        max_dimension = max(width, height)

        if max_dimension < 1000:
            final_image = image.resize((224, 224), Image.LANCZOS)
            method_name = "原始-直接调整(小图像)"
        else:
            # 传统256→224方法
            resized_256 = image.resize((256, 256), Image.LANCZOS)
            left = (256 - 224) // 2
            top = (256 - 224) // 2
            final_image = resized_256.crop((left, top, left + 224, top + 224))
            method_name = "原始-传统方法(大图像)"

        return self._image_to_tensor(final_image), method_name

    def preprocess_image_direct_224(self, image: Image.Image) -> Tuple[np.ndarray, str]:
        """直接224x224预处理"""
        final_image = image.resize((224, 224), Image.LANCZOS)
        return self._image_to_tensor(final_image), "直接224x224"

    def preprocess_image_traditional(self, image: Image.Image) -> Tuple[np.ndarray, str]:
        """传统256→224预处理"""
        resized_256 = image.resize((256, 256), Image.LANCZOS)
        left = (256 - 224) // 2
        top = (256 - 224) // 2
        final_image = resized_256.crop((left, top, left + 224, top + 224))
        return self._image_to_tensor(final_image), "传统256→224"

    def preprocess_image_smart_adaptive(self, image: Image.Image) -> Tuple[np.ndarray, str]:
        """智能自适应预处理"""
        width, height = image.size
        aspect_ratio = width / height

        # 根据宽高比选择最佳预处理策略
        if 0.8 <= aspect_ratio <= 1.2:  # 接近正方形
            final_image = image.resize((224, 224), Image.LANCZOS)
            method_name = "智能-直接调整(正方形)"
        elif aspect_ratio > 1.2:  # 宽图
            # 先调整到合适高度，然后裁剪
            new_width = int(224 * aspect_ratio)
            resized = image.resize((new_width, 224), Image.LANCZOS)
            left = (new_width - 224) // 2
            final_image = resized.crop((left, 0, left + 224, 224))
            method_name = "智能-宽图裁剪"
        else:  # 高图
            # 先调整到合适宽度，然后裁剪
            new_height = int(224 / aspect_ratio)
            resized = image.resize((224, new_height), Image.LANCZOS)
            top = (new_height - 224) // 2
            final_image = resized.crop((0, top, 224, top + 224))
            method_name = "智能-高图裁剪"

        return self._image_to_tensor(final_image), method_name

    def _image_to_tensor(self, image: Image.Image) -> np.ndarray:
        """将PIL图像转换为模型输入张量"""
        img_array = np.array(image)

        # 转换为BGR通道顺序（保持与原代码一致）
        bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # ImageNet标准化 (BGR格式)
        mean = np.array([0.406, 0.456, 0.485])  # BGR: B, G, R
        std = np.array([0.225, 0.224, 0.229])   # BGR: B, G, R

        normalized_array = (bgr_array / 255.0 - mean) / std
        input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()

        return input_tensor

    def apply_enhancement(self, image: Image.Image, method: str) -> Image.Image:
        """应用图像增强"""
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

    def run_inference(self, input_tensor: torch.Tensor) -> Tuple[torch.Tensor, float]:
        """运行模型推理"""
        self._lazy_load_components()

        start_time = time.time()
        with torch.no_grad():
            output = self.model(input_tensor)
        inference_time = time.time() - start_time

        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        return probabilities, inference_time

    def extract_results(self, probabilities: torch.Tensor, confidence_threshold: float = 1.0,
                       top_k: int = 5) -> List[Dict]:
        """提取识别结果"""
        self._lazy_load_components()

        results = []
        k = min(len(probabilities), len(self.bird_info), 1000)
        all_probs, all_catid = torch.topk(probabilities, k)

        # 动态阈值计算
        if confidence_threshold == 'auto':
            # 计算概率分布的统计信息
            probs_array = probabilities.cpu().numpy()
            mean_prob = np.mean(probs_array)
            std_prob = np.std(probs_array)
            confidence_threshold = max(0.1, (mean_prob + std_prob) * 100)  # 动态阈值

        count = 0
        for i in range(all_probs.size(0)):
            if count >= top_k:
                break

            class_id = all_catid[i].item()
            confidence = all_probs[i].item() * 100

            if confidence < confidence_threshold:
                continue

            try:
                if class_id < len(self.bird_info) and len(self.bird_info[class_id]) >= 2:
                    bird_name_cn = self.bird_info[class_id][0]
                    bird_name_en = self.bird_info[class_id][1]

                    # 尝试获取eBird代码
                    ebird_code = None
                    if self.db_manager:
                        ebird_code = self.db_manager.get_ebird_code_by_english_name(bird_name_en)

                    results.append({
                        'class_id': class_id,
                        'confidence': confidence,
                        'chinese_name': bird_name_cn,
                        'english_name': bird_name_en,
                        'ebird_code': ebird_code,
                        'rank': count + 1
                    })
                    count += 1
            except (IndexError, TypeError):
                continue

        return results

    def test_single_image_comprehensive(self, image_path: str) -> Dict:
        """对单张图像进行全面测试"""
        print(f"\n🔍 测试图像: {os.path.basename(image_path)}")

        try:
            original_image = Image.open(image_path).convert('RGB')
            image_size = original_image.size
            print(f"图像尺寸: {image_size}")
        except Exception as e:
            print(f"❌ 图像加载失败: {e}")
            return {}

        test_result = {
            'image_path': image_path,
            'image_size': image_size,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'tests': {}
        }

        # 预处理方法测试
        preprocessing_methods = {
            'original': self.preprocess_image_original,
            'direct_224': self.preprocess_image_direct_224,
            'traditional_256_224': self.preprocess_image_traditional,
            'smart_adaptive': self.preprocess_image_smart_adaptive
        }

        # YOLO检测测试（仅对大图像）
        yolo_results = {}
        if max(image_size) > 640 and self.yolo_detector and self.yolo_detector.model:
            print("  🎯 测试YOLO检测参数...")
            for conf_name, conf_value in self.test_configs['yolo_confidence'].items():
                try:
                    cropped_image, detection_msg = self.yolo_detector.detect_and_crop_bird(
                        image_path, confidence_threshold=conf_value
                    )
                    yolo_results[conf_name] = {
                        'success': cropped_image is not None,
                        'message': detection_msg,
                        'cropped_size': cropped_image.size if cropped_image else None
                    }
                except Exception as e:
                    yolo_results[conf_name] = {
                        'success': False,
                        'message': f"YOLO检测失败: {e}",
                        'cropped_size': None
                    }

        # 对每种图像增强方法进行测试
        for enhancement_name, enhancement_desc in self.test_configs['enhancement_methods'].items():
            print(f"  🎨 测试增强方法: {enhancement_desc}")

            # 应用增强
            if enhancement_name == 'none':
                enhanced_image = original_image
            else:
                enhanced_image = self.apply_enhancement(original_image, enhancement_name)

            # 测试每种预处理方法
            for prep_name, prep_func in preprocessing_methods.items():
                print(f"    🔧 预处理: {self.test_configs['preprocessing'][prep_name]}")

                try:
                    # 预处理
                    input_tensor, method_desc = prep_func(enhanced_image)

                    # 推理
                    probabilities, inference_time = self.run_inference(input_tensor)

                    # 测试不同置信度阈值
                    threshold_results = {}
                    for threshold_name, threshold_value in self.test_configs['confidence_thresholds'].items():
                        results = self.extract_results(probabilities, threshold_value, top_k=5)

                        threshold_results[threshold_name] = {
                            'threshold_value': threshold_value,
                            'results_count': len(results),
                            'results': results,
                            'top_confidence': results[0]['confidence'] if results else 0,
                            'top_result': results[0] if results else None
                        }

                    test_key = f"{enhancement_name}_{prep_name}"
                    test_result['tests'][test_key] = {
                        'enhancement': enhancement_desc,
                        'preprocessing': method_desc,
                        'inference_time': inference_time,
                        'max_confidence': probabilities.max().item() * 100,
                        'confidence_thresholds': threshold_results
                    }

                except Exception as e:
                    print(f"    ❌ 测试失败: {e}")
                    test_key = f"{enhancement_name}_{prep_name}"
                    test_result['tests'][test_key] = {
                        'error': str(e),
                        'enhancement': enhancement_desc,
                        'preprocessing': self.test_configs['preprocessing'][prep_name]
                    }

        test_result['yolo_detection'] = yolo_results
        print(f"✅ 图像测试完成: {len(test_result['tests'])} 个组合")

        return test_result

    def run_batch_test(self, image_patterns: List[str] = None) -> List[Dict]:
        """批量测试多张图像"""
        if image_patterns is None:
            # 默认搜索测试图像
            image_patterns = [
                "*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff"
            ]

        test_images = []
        for pattern in image_patterns:
            test_images.extend(Path(self.test_images_dir).glob(pattern))

        # 获取用户指定的测试图像数量
        test_images = list(test_images)

        if len(test_images) > 10:
            print(f"发现 {len(test_images)} 张图像")
            max_count = input(f"请输入要测试的图像数量 (直接回车测试前100张): ").strip()
            try:
                max_count = int(max_count) if max_count else 100
                max_count = min(max_count, len(test_images))
                test_images = test_images[:max_count]
            except ValueError:
                test_images = test_images[:100]

        if not test_images:
            print(f"❌ 在 {self.test_images_dir} 中未找到测试图像")
            return []

        print(f"🚀 开始批量测试 {len(test_images)} 张图像...")

        all_results = []
        for i, image_path in enumerate(test_images, 1):
            print(f"\n{'='*60}")
            print(f"测试进度: {i}/{len(test_images)}")

            result = self.test_single_image_comprehensive(str(image_path))
            if result:
                all_results.append(result)

        self.test_results = all_results
        return all_results

    def analyze_results(self) -> Dict:
        """分析测试结果"""
        if not self.test_results:
            print("❌ 没有测试结果可分析")
            return {}

        print(f"\n📊 分析 {len(self.test_results)} 张图像的测试结果...")

        analysis = {
            'summary': {
                'total_images': len(self.test_results),
                'total_tests': 0,
                'successful_tests': 0
            },
            'best_combinations': {},
            'method_performance': {
                'enhancement': {},
                'preprocessing': {},
                'confidence_threshold': {}
            },
            'recommendations': []
        }

        # 收集所有测试数据
        all_test_data = []

        for result in self.test_results:
            for test_key, test_data in result.get('tests', {}).items():
                if 'error' in test_data:
                    continue

                analysis['summary']['total_tests'] += 1

                enhancement, preprocessing = test_key.split('_', 1)

                for threshold_name, threshold_data in test_data.get('confidence_thresholds', {}).items():
                    if threshold_data['results_count'] > 0:
                        analysis['summary']['successful_tests'] += 1

                        test_record = {
                            'image': os.path.basename(result['image_path']),
                            'enhancement': enhancement,
                            'preprocessing': preprocessing,
                            'threshold': threshold_name,
                            'top_confidence': threshold_data['top_confidence'],
                            'results_count': threshold_data['results_count'],
                            'inference_time': test_data['inference_time'],
                            'max_confidence': test_data['max_confidence']
                        }
                        all_test_data.append(test_record)

        if not all_test_data:
            print("❌ 没有成功的测试数据")
            return analysis

        # 转换为DataFrame进行分析
        df = pd.DataFrame(all_test_data)

        # 分析最佳组合
        best_by_confidence = df.loc[df['top_confidence'].idxmax()]
        best_by_speed = df.loc[df['inference_time'].idxmin()]

        # 稳定性分析（仅在多张图像时有效）
        most_stable = None
        if len(self.test_results) > 1:
            best_by_stability = df.groupby(['enhancement', 'preprocessing', 'threshold'])['top_confidence'].agg(['mean', 'std']).reset_index()
            best_by_stability['stability_score'] = best_by_stability['mean'] / (best_by_stability['std'] + 0.1)
            if not best_by_stability['stability_score'].isna().all():
                most_stable = best_by_stability.loc[best_by_stability['stability_score'].idxmax()]

        analysis['best_combinations'] = {
            'highest_confidence': {
                'combination': f"{best_by_confidence['enhancement']}_{best_by_confidence['preprocessing']}_{best_by_confidence['threshold']}",
                'confidence': best_by_confidence['top_confidence'],
                'details': best_by_confidence.to_dict()
            },
            'fastest': {
                'combination': f"{best_by_speed['enhancement']}_{best_by_speed['preprocessing']}_{best_by_speed['threshold']}",
                'time': best_by_speed['inference_time'],
                'details': best_by_speed.to_dict()
            }
        }

        # 添加稳定性分析（仅在多张图像时）
        if most_stable is not None:
            analysis['best_combinations']['most_stable'] = {
                'combination': f"{most_stable['enhancement']}_{most_stable['preprocessing']}_{most_stable['threshold']}",
                'stability_score': most_stable['stability_score'],
                'mean_confidence': most_stable['mean'],
                'confidence_std': most_stable['std']
            }

        # 方法性能统计
        analysis['method_performance']['enhancement'] = df.groupby('enhancement')['top_confidence'].agg(['mean', 'std', 'count']).to_dict('index')
        analysis['method_performance']['preprocessing'] = df.groupby('preprocessing')['top_confidence'].agg(['mean', 'std', 'count']).to_dict('index')
        analysis['method_performance']['confidence_threshold'] = df.groupby('threshold')['top_confidence'].agg(['mean', 'std', 'count']).to_dict('index')

        # 生成建议
        best_enhancement = df.groupby('enhancement')['top_confidence'].mean().idxmax()
        best_preprocessing = df.groupby('preprocessing')['top_confidence'].mean().idxmax()
        best_threshold = df.groupby('threshold')['top_confidence'].mean().idxmax()

        analysis['recommendations'] = [
            f"最佳图像增强方法: {self.test_configs['enhancement_methods'].get(best_enhancement, best_enhancement)}",
            f"最佳预处理方法: {self.test_configs['preprocessing'].get(best_preprocessing, best_preprocessing)}",
            f"最佳置信度阈值: {best_threshold}",
            f"平均置信度提升: {df['top_confidence'].mean():.2f}%",
            f"推理时间范围: {df['inference_time'].min():.3f}s - {df['inference_time'].max():.3f}s"
        ]

        return analysis

    def save_results(self, output_file: str = None):
        """保存测试结果"""
        if output_file is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            output_file = f"optimization_test_results_{timestamp}.json"

        output_path = os.path.join(self.script_dir, output_file)

        results_data = {
            'test_config': self.test_configs,
            'test_results': self.test_results,
            'analysis': self.analyze_results(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2, default=str)
            print(f"✅ 测试结果已保存到: {output_path}")
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")

    def generate_report(self):
        """生成测试报告"""
        analysis = self.analyze_results()

        if not analysis:
            return

        print(f"\n{'='*80}")
        print("🎯 鸟类识别优化测试报告")
        print(f"{'='*80}")

        # 摘要
        summary = analysis['summary']
        print(f"\n📋 测试摘要:")
        print(f"  测试图像数量: {summary['total_images']}")
        print(f"  总测试次数: {summary['total_tests']}")
        print(f"  成功测试次数: {summary['successful_tests']}")
        print(f"  成功率: {summary['successful_tests']/summary['total_tests']*100:.1f}%")

        # 最佳组合
        best = analysis['best_combinations']
        print(f"\n🏆 最佳组合:")
        print(f"  最高置信度组合: {best['highest_confidence']['combination']}")
        print(f"    置信度: {best['highest_confidence']['confidence']:.2f}%")
        print(f"  最快组合: {best['fastest']['combination']}")
        print(f"    推理时间: {best['fastest']['time']:.3f}s")

        if 'most_stable' in best:
            print(f"  最稳定组合: {best['most_stable']['combination']}")
            print(f"    稳定性得分: {best['most_stable']['stability_score']:.2f}")
        else:
            print(f"  最稳定组合: 需要多张图像测试才能计算")

        # 建议
        print(f"\n💡 优化建议:")
        for i, recommendation in enumerate(analysis['recommendations'], 1):
            print(f"  {i}. {recommendation}")

        print(f"\n{'='*80}")


def main():
    """主函数"""
    print("🐦 SuperBirdID 优化测试工具")
    print("="*50)

    # 获取测试目录
    test_dir = input("请输入测试图像目录路径 (直接回车使用当前目录): ").strip() or "."

    if not os.path.exists(test_dir):
        print(f"❌ 目录不存在: {test_dir}")
        return

    # 初始化测试器
    tester = BirdIDOptimizationTester(test_dir)

    print("\n选择测试模式:")
    print("1. 单张图像测试")
    print("2. 批量图像测试")

    choice = input("请选择 (1-2): ").strip()

    if choice == '1':
        # 单张图像测试
        image_path = input("请输入图像文件路径: ").strip().strip("'\"")
        if not os.path.exists(image_path):
            print(f"❌ 图像文件不存在: {image_path}")
            return

        result = tester.test_single_image_comprehensive(image_path)
        if result:
            tester.test_results = [result]

    elif choice == '2':
        # 批量测试
        tester.run_batch_test()

    else:
        print("❌ 无效选择")
        return

    # 生成分析报告
    tester.generate_report()

    # 保存结果
    save_choice = input("\n是否保存详细结果到JSON文件? (y/n): ").strip().lower()
    if save_choice == 'y':
        tester.save_results()


if __name__ == "__main__":
    main()