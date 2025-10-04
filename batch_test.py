#!/usr/bin/env python3
"""
大批量鸟类识别优化测试工具
专注于关键配置的快速批量测试，支持100+张图像
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
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue

# 导入原始模块
try:
    from SuperBirdId import lazy_load_classifier, lazy_load_bird_info, YOLOBirdDetector
    from ebird_country_filter import eBirdCountryFilter
    from bird_database_manager import BirdDatabaseManager
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    sys.exit(1)

class BatchOptimizationTester:
    def __init__(self, test_images_dir: str = None):
        """
        初始化批量优化测试器

        Args:
            test_images_dir: 测试图像目录路径
        """
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_images_dir = test_images_dir or self.script_dir

        # 懒加载组件（全局共享）
        self.model = None
        self.bird_info = None
        self.db_manager = None
        self._lock = threading.Lock()

        # 测试结果存储
        self.test_results = []

        # 关键测试配置（精简版）
        self.key_configs = [
            {
                'name': '原始基准',
                'enhancement': 'none',
                'preprocessing': 'original',
                'confidence_threshold': 1.0,
                'description': '当前系统的基准配置'
            },
            {
                'name': '最佳理论',
                'enhancement': 'none',  # 根据测试结果，无增强更好
                'preprocessing': 'traditional_256_224',
                'confidence_threshold': 5.0,  # 严格阈值
                'description': '基于上次测试的最佳配置'
            },
            {
                'name': '智能自适应',
                'enhancement': 'none',
                'preprocessing': 'smart_adaptive',
                'confidence_threshold': 1.0,
                'description': '智能预处理方法'
            },
            {
                'name': '速度优先',
                'enhancement': 'none',
                'preprocessing': 'direct_224',
                'confidence_threshold': 1.0,
                'description': '最快速度配置'
            },
            {
                'name': '降饱和度+传统',
                'enhancement': 'desaturate',
                'preprocessing': 'traditional_256_224',
                'confidence_threshold': 5.0,
                'description': '上次测试中最高置信度配置'
            }
        ]

        print(f"🚀 大批量鸟类识别优化测试器初始化完成")
        print(f"测试目录: {self.test_images_dir}")
        print(f"测试配置数量: {len(self.key_configs)}")

    def _lazy_load_components(self):
        """线程安全的懒加载组件"""
        with self._lock:
            if self.model is None:
                print("加载AI模型...")
                self.model = lazy_load_classifier()
                print("✓ 模型加载完成")

            if self.bird_info is None:
                print("加载鸟类数据...")
                self.bird_info = lazy_load_bird_info()
                print("✓ 鸟类数据加载完成")

            try:
                if self.db_manager is None:
                    self.db_manager = BirdDatabaseManager()
                    print("✓ 数据库加载完成")
            except:
                self.db_manager = False
                print("⚠ 数据库管理器加载失败")

    def preprocess_image(self, image: Image.Image, method: str) -> Tuple[torch.Tensor, str]:
        """图像预处理"""
        width, height = image.size

        if method == 'original':
            # 原始方法
            max_dimension = max(width, height)
            if max_dimension < 1000:
                final_image = image.resize((224, 224), Image.LANCZOS)
                method_name = "原始-直接224"
            else:
                resized_256 = image.resize((256, 256), Image.LANCZOS)
                left = top = 16
                final_image = resized_256.crop((left, top, left + 224, top + 224))
                method_name = "原始-256→224"

        elif method == 'direct_224':
            # 直接224x224
            final_image = image.resize((224, 224), Image.LANCZOS)
            method_name = "直接224"

        elif method == 'traditional_256_224':
            # 传统256→224
            resized_256 = image.resize((256, 256), Image.LANCZOS)
            left = top = 16
            final_image = resized_256.crop((left, top, left + 224, top + 224))
            method_name = "传统256→224"

        elif method == 'smart_adaptive':
            # 智能自适应
            aspect_ratio = width / height
            if 0.8 <= aspect_ratio <= 1.2:
                final_image = image.resize((224, 224), Image.LANCZOS)
                method_name = "智能-直接"
            elif aspect_ratio > 1.2:
                new_width = int(224 * aspect_ratio)
                resized = image.resize((new_width, 224), Image.LANCZOS)
                left = (new_width - 224) // 2
                final_image = resized.crop((left, 0, left + 224, 224))
                method_name = "智能-宽图裁剪"
            else:
                new_height = int(224 / aspect_ratio)
                resized = image.resize((224, new_height), Image.LANCZOS)
                top = (new_height - 224) // 2
                final_image = resized.crop((0, top, 224, top + 224))
                method_name = "智能-高图裁剪"
        else:
            # 默认直接调整
            final_image = image.resize((224, 224), Image.LANCZOS)
            method_name = "默认直接"

        return self._image_to_tensor(final_image), method_name

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

    def _image_to_tensor(self, image: Image.Image) -> torch.Tensor:
        """将PIL图像转换为模型输入张量"""
        img_array = np.array(image)
        bgr_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # ImageNet标准化 (BGR格式)
        mean = np.array([0.406, 0.456, 0.485])
        std = np.array([0.225, 0.224, 0.229])

        normalized_array = (bgr_array / 255.0 - mean) / std
        input_tensor = torch.from_numpy(normalized_array).permute(2, 0, 1).unsqueeze(0).float()

        return input_tensor

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
                       top_k: int = 3) -> List[Dict]:
        """提取识别结果"""
        self._lazy_load_components()

        results = []
        k = min(len(probabilities), len(self.bird_info), 100)
        all_probs, all_catid = torch.topk(probabilities, k)

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
                    if self.db_manager and self.db_manager is not False:
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

    def test_single_image(self, image_path: str) -> Dict:
        """测试单张图像的所有关键配置"""
        image_name = os.path.basename(image_path)

        try:
            original_image = Image.open(image_path).convert('RGB')
            image_size = original_image.size
        except Exception as e:
            return {
                'image_path': image_path,
                'image_name': image_name,
                'error': f"图像加载失败: {e}",
                'tests': {}
            }

        test_result = {
            'image_path': image_path,
            'image_name': image_name,
            'image_size': image_size,
            'tests': {}
        }

        # 测试每个关键配置
        for config in self.key_configs:
            config_name = config['name']

            try:
                # 应用增强
                enhanced_image = self.apply_enhancement(original_image, config['enhancement'])

                # 预处理
                input_tensor, method_desc = self.preprocess_image(enhanced_image, config['preprocessing'])

                # 推理
                probabilities, inference_time = self.run_inference(input_tensor)

                # 提取结果
                results = self.extract_results(probabilities, config['confidence_threshold'], top_k=3)
                max_confidence = probabilities.max().item() * 100

                test_result['tests'][config_name] = {
                    'config': config,
                    'method_desc': method_desc,
                    'inference_time': inference_time,
                    'max_confidence': max_confidence,
                    'results_count': len(results),
                    'results': results,
                    'top_confidence': results[0]['confidence'] if results else 0,
                    'top_result': results[0] if results else None
                }

            except Exception as e:
                test_result['tests'][config_name] = {
                    'config': config,
                    'error': str(e)
                }

        return test_result

    def run_batch_test(self, max_images: int = 100, num_threads: int = 4) -> List[Dict]:
        """批量测试多张图像"""
        # 搜索测试图像
        image_patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff", "*.JPG", "*.JPEG"]
        test_images = []

        for pattern in image_patterns:
            test_images.extend(Path(self.test_images_dir).glob(pattern))
            test_images.extend(Path(self.test_images_dir).glob(f"**/{pattern}"))

        test_images = list(set(test_images))  # 去重

        if not test_images:
            print(f"❌ 在 {self.test_images_dir} 中未找到测试图像")
            return []

        # 限制图像数量
        if len(test_images) > max_images:
            test_images = test_images[:max_images]

        print(f"🎯 开始批量测试 {len(test_images)} 张图像...")
        print(f"📋 测试配置: {len(self.key_configs)} 个")
        print(f"🔧 预计总测试次数: {len(test_images) * len(self.key_configs)}")
        print(f"🚀 使用 {num_threads} 个线程并行处理")

        # 预加载模型（避免线程竞争）
        self._lazy_load_components()

        start_time = time.time()
        completed_tests = []

        # 使用进度队列
        progress_queue = Queue()

        def update_progress():
            completed = 0
            while completed < len(test_images):
                try:
                    progress_queue.get(timeout=1)
                    completed += 1
                    if completed % 10 == 0 or completed == len(test_images):
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (len(test_images) - completed) / rate if rate > 0 else 0
                        print(f"进度: {completed}/{len(test_images)} ({completed/len(test_images)*100:.1f}%) "
                              f"速度: {rate:.1f} 图/秒 预计剩余: {eta:.1f}秒")
                except:
                    continue

        # 启动进度监控线程
        import threading
        progress_thread = threading.Thread(target=update_progress)
        progress_thread.daemon = True
        progress_thread.start()

        # 并行处理图像
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_image = {
                executor.submit(self.test_single_image, str(image_path)): image_path
                for image_path in test_images
            }

            for future in as_completed(future_to_image):
                image_path = future_to_image[future]
                try:
                    result = future.result()
                    completed_tests.append(result)
                    progress_queue.put(1)
                except Exception as e:
                    print(f"❌ 处理 {image_path} 时出错: {e}")
                    progress_queue.put(1)

        total_time = time.time() - start_time
        print(f"\n✅ 批量测试完成!")
        print(f"总时间: {total_time:.2f}秒")
        print(f"平均速度: {len(test_images)/total_time:.2f} 图/秒")

        self.test_results = completed_tests
        return completed_tests

    def analyze_results(self) -> Dict:
        """分析批量测试结果"""
        if not self.test_results:
            return {}

        print(f"\n📊 分析 {len(self.test_results)} 张图像的测试结果...")

        # 收集所有成功的测试数据
        all_test_data = []
        failed_tests = 0

        for result in self.test_results:
            image_name = result['image_name']

            for config_name, test_data in result.get('tests', {}).items():
                if 'error' in test_data:
                    failed_tests += 1
                    continue

                if test_data.get('results_count', 0) > 0:
                    all_test_data.append({
                        'image': image_name,
                        'config': config_name,
                        'top_confidence': test_data['top_confidence'],
                        'max_confidence': test_data['max_confidence'],
                        'inference_time': test_data['inference_time'],
                        'results_count': test_data['results_count'],
                        'top_result': test_data.get('top_result', {}).get('chinese_name', 'Unknown')
                    })

        if not all_test_data:
            print("❌ 没有成功的测试数据")
            return {}

        # 转换为DataFrame进行分析
        df = pd.DataFrame(all_test_data)

        # 按配置分组分析 - 使用简化的统计方法
        config_stats = {}
        for config_name in df['config'].unique():
            config_data = df[df['config'] == config_name]
            config_stats[config_name] = {
                'avg_confidence': config_data['top_confidence'].mean(),
                'std_confidence': config_data['top_confidence'].std(),
                'min_confidence': config_data['top_confidence'].min(),
                'max_confidence': config_data['top_confidence'].max(),
                'count': len(config_data),
                'avg_time': config_data['inference_time'].mean(),
                'std_time': config_data['inference_time'].std(),
                'min_time': config_data['inference_time'].min(),
                'max_time': config_data['inference_time'].max()
            }

        # 找出最佳配置
        best_avg_confidence = df.groupby('config')['top_confidence'].mean().idxmax()
        best_max_confidence = df.loc[df['top_confidence'].idxmax()]
        fastest_config = df.groupby('config')['inference_time'].mean().idxmin()

        analysis = {
            'summary': {
                'total_images': len(self.test_results),
                'successful_tests': len(all_test_data),
                'failed_tests': failed_tests,
                'success_rate': len(all_test_data) / (len(all_test_data) + failed_tests) * 100 if (len(all_test_data) + failed_tests) > 0 else 0
            },
            'config_performance': config_stats,
            'best_configs': {
                'best_avg_confidence': {
                    'config': best_avg_confidence,
                    'avg_confidence': df.groupby('config')['top_confidence'].mean()[best_avg_confidence]
                },
                'best_max_confidence': {
                    'config': best_max_confidence['config'],
                    'confidence': best_max_confidence['top_confidence'],
                    'image': best_max_confidence['image']
                },
                'fastest': {
                    'config': fastest_config,
                    'avg_time': df.groupby('config')['inference_time'].mean()[fastest_config]
                }
            }
        }

        return analysis

    def generate_report(self):
        """生成详细的分析报告"""
        analysis = self.analyze_results()

        if not analysis:
            print("❌ 无法生成报告，没有有效数据")
            return

        print(f"\n{'='*80}")
        print("🎯 大批量鸟类识别优化测试报告")
        print(f"{'='*80}")

        # 测试摘要
        summary = analysis['summary']
        print(f"\n📋 测试摘要:")
        print(f"  测试图像总数: {summary['total_images']}")
        print(f"  成功测试次数: {summary['successful_tests']}")
        print(f"  失败测试次数: {summary['failed_tests']}")
        print(f"  成功率: {summary['success_rate']:.1f}%")

        # 配置性能对比
        print(f"\n🏆 配置性能排行:")
        best = analysis['best_configs']

        print(f"  1️⃣ 平均置信度最高: {best['best_avg_confidence']['config']}")
        print(f"     平均置信度: {best['best_avg_confidence']['avg_confidence']:.2f}%")

        print(f"  2️⃣ 单次最高置信度: {best['best_max_confidence']['config']}")
        print(f"     最高置信度: {best['best_max_confidence']['confidence']:.2f}%")
        print(f"     图像: {best['best_max_confidence']['image']}")

        print(f"  3️⃣ 速度最快: {best['fastest']['config']}")
        print(f"     平均推理时间: {best['fastest']['avg_time']:.4f}s")

        # 详细统计 - 重新收集数据
        print(f"\n📊 详细配置统计:")

        # 重新计算每个配置的统计数据
        for config in self.key_configs:
            config_name = config['name']

            # 收集该配置的所有数据
            config_results = []
            for result in self.test_results:
                if config_name in result.get('tests', {}):
                    test_data = result['tests'][config_name]
                    if 'error' not in test_data and test_data.get('results_count', 0) > 0:
                        config_results.append({
                            'confidence': test_data['top_confidence'],
                            'time': test_data['inference_time']
                        })

            if config_results:
                confidences = [r['confidence'] for r in config_results]
                times = [r['time'] for r in config_results]

                avg_conf = np.mean(confidences)
                std_conf = np.std(confidences)
                avg_time = np.mean(times)
                test_count = len(config_results)

                print(f"  {config_name}:")
                print(f"    平均置信度: {avg_conf:.2f}% (±{std_conf:.2f})")
                print(f"    平均推理时间: {avg_time:.4f}s")
                print(f"    成功测试数: {test_count}")
            else:
                print(f"  {config_name}: 无有效数据")

        print(f"\n💡 优化建议:")

        # 根据结果给出建议
        best_config_name = best['best_avg_confidence']['config']
        best_config = next(c for c in self.key_configs if c['name'] == best_config_name)

        print(f"  1. 推荐使用配置: {best_config_name}")
        print(f"     - 图像增强: {best_config['enhancement']}")
        print(f"     - 预处理方法: {best_config['preprocessing']}")
        print(f"     - 置信度阈值: {best_config['confidence_threshold']}")

        if best['fastest']['config'] != best_config_name:
            print(f"  2. 如需更快速度，可考虑: {best['fastest']['config']}")

        # 计算速度差异
        fastest_time = best['fastest']['avg_time']

        # 找到最佳配置的平均时间
        best_time = None
        for config in self.key_configs:
            if config['name'] == best_config_name:
                config_results = []
                for result in self.test_results:
                    if best_config_name in result.get('tests', {}):
                        test_data = result['tests'][best_config_name]
                        if 'error' not in test_data:
                            config_results.append(test_data['inference_time'])
                if config_results:
                    best_time = np.mean(config_results)
                break

        if best_time and best_time > fastest_time * 1.5:
            print(f"  3. 速度vs准确性权衡: 最佳配置比最快配置慢 {best_time/fastest_time:.1f}x")

        print(f"\n{'='*80}")

    def save_results(self, output_file: str = None):
        """保存测试结果"""
        if output_file is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            output_file = f"batch_test_results_{timestamp}.json"

        output_path = os.path.join(self.script_dir, output_file)

        results_data = {
            'test_config': {
                'key_configs': self.key_configs,
                'test_images_count': len(self.test_results)
            },
            'test_results': self.test_results,
            'analysis': self.analyze_results(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2, default=str)
            print(f"✅ 测试结果已保存到: {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")
            return None


def main():
    """主函数"""
    print("🚀 SuperBirdID 大批量优化测试工具")
    print("="*50)

    # 获取测试目录
    test_dir = input("请输入测试图像目录路径 (直接回车使用当前目录): ").strip() or "."

    if not os.path.exists(test_dir):
        print(f"❌ 目录不存在: {test_dir}")
        return

    # 初始化测试器
    tester = BatchOptimizationTester(test_dir)

    # 获取测试参数
    try:
        max_images = input("请输入要测试的图像数量 (直接回车默认100): ").strip()
        max_images = int(max_images) if max_images else 100

        num_threads = input("请输入并行线程数 (直接回车默认4): ").strip()
        num_threads = int(num_threads) if num_threads else 4
        num_threads = max(1, min(num_threads, 8))  # 限制在1-8之间

    except ValueError:
        max_images = 100
        num_threads = 4
        print("使用默认参数: 100张图像, 4个线程")

    # 运行批量测试
    print(f"\n开始测试最多 {max_images} 张图像，使用 {num_threads} 个线程...")

    results = tester.run_batch_test(max_images=max_images, num_threads=num_threads)

    if not results:
        print("❌ 没有测试结果")
        return

    # 生成分析报告
    tester.generate_report()

    # 保存结果
    save_choice = input("\n是否保存详细结果到JSON文件? (y/n): ").strip().lower()
    if save_choice == 'y':
        tester.save_results()

    print(f"\n🎉 批量测试完成! 共处理 {len(results)} 张图像")


if __name__ == "__main__":
    main()