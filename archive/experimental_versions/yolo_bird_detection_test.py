import torch
import cv2
import numpy as np
from PIL import Image
import os
from ultralytics import YOLO

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))

class YOLOBirdDetector:
    def __init__(self, model_path=None):
        """
        初始化YOLO鸟类检测器
        model_path: YOLO模型路径，默认使用项目中的yolo11x.pt
        """
        if model_path is None:
            model_path = os.path.join(script_dir, 'yolo11x.pt')
        
        try:
            self.model = YOLO(model_path)
            print(f"YOLO模型加载成功: {model_path}")
        except Exception as e:
            print(f"YOLO模型加载失败: {e}")
            raise
    
    def detect_birds(self, image_path, confidence_threshold=0.25):
        """
        检测图像中的鸟类
        image_path: 输入图像路径
        confidence_threshold: 置信度阈值
        返回: 检测结果列表
        """
        try:
            # 使用YOLO进行检测
            results = self.model(image_path, conf=confidence_threshold)
            
            # 解析检测结果
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for i, box in enumerate(boxes):
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        # 获取类别名称
                        class_name = self.model.names[class_id]
                        
                        # 只保留鸟类检测结果 (COCO数据集中鸟类的class_id是14)
                        if class_id == 14:  # 'bird' in COCO dataset
                            detections.append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'confidence': float(confidence),
                                'class_id': class_id,
                                'class_name': class_name
                            })
            
            # 按置信度排序
            detections.sort(key=lambda x: x['confidence'], reverse=True)
            return detections
            
        except Exception as e:
            print(f"鸟类检测失败: {e}")
            return []
    
    def get_highest_confidence_bird(self, image_path, confidence_threshold=0.25):
        """
        获取置信度最高的鸟类检测结果
        """
        detections = self.detect_birds(image_path, confidence_threshold)
        
        if detections:
            return detections[0]  # 返回置信度最高的检测结果
        else:
            return None
    
    def crop_bird_from_detection(self, image_path, detection_result, padding=20):
        """
        根据检测结果裁剪鸟类区域
        image_path: 原始图像路径
        detection_result: 检测结果字典
        padding: 裁剪时的边距
        返回: PIL Image对象
        """
        try:
            # 加载原始图像
            image = Image.open(image_path).convert('RGB')
            img_width, img_height = image.size
            
            # 获取检测框坐标
            x1, y1, x2, y2 = detection_result['bbox']
            
            # 添加边距并确保不超出图像边界
            x1_padded = max(0, x1 - padding)
            y1_padded = max(0, y1 - padding)
            x2_padded = min(img_width, x2 + padding)
            y2_padded = min(img_height, y2 + padding)
            
            # 裁剪图像
            cropped_image = image.crop((x1_padded, y1_padded, x2_padded, y2_padded))
            
            return cropped_image
            
        except Exception as e:
            print(f"图像裁剪失败: {e}")
            return None
    
    def visualize_detection(self, image_path, detections, save_path=None):
        """
        可视化检测结果
        image_path: 原始图像路径
        detections: 检测结果列表
        save_path: 保存路径（可选）
        """
        try:
            # 加载图像
            image = cv2.imread(image_path)
            
            # 绘制检测框
            for detection in detections:
                x1, y1, x2, y2 = detection['bbox']
                confidence = detection['confidence']
                
                # 绘制边界框
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # 添加标签
                label = f"Bird: {confidence:.2f}"
                cv2.putText(image, label, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            if save_path:
                cv2.imwrite(save_path, image)
                print(f"检测结果已保存到: {save_path}")
            
            return image
            
        except Exception as e:
            print(f"可视化失败: {e}")
            return None

def test_yolo_bird_detection(image_path=None):
    """
    测试YOLO鸟类检测功能
    """
    print("=== YOLO鸟类检测测试 ===")
    
    # 初始化检测器
    try:
        detector = YOLOBirdDetector()
    except Exception as e:
        print(f"无法初始化YOLO检测器: {e}")
        return
    
    # 获取测试图像路径
    if image_path is None:
        image_path = os.path.join(script_dir, 'test_bird_image.jpg')
    
    if not os.path.exists(image_path):
        print(f"图像文件不存在: {image_path}")
        print("请确保有测试图像文件存在")
        return
    
    print(f"正在检测图像: {image_path}")
    
    # 执行检测
    detections = detector.detect_birds(image_path)
    
    if not detections:
        print("未检测到任何鸟类")
        return
    
    print(f"\n检测到 {len(detections)} 只鸟:")
    for i, detection in enumerate(detections):
        print(f"  {i+1}. 置信度: {detection['confidence']:.3f}, "
              f"边界框: {detection['bbox']}")
    
    # 获取置信度最高的鸟类
    best_bird = detector.get_highest_confidence_bird(image_path)
    if best_bird:
        print(f"\n置信度最高的鸟类:")
        print(f"  置信度: {best_bird['confidence']:.3f}")
        print(f"  边界框: {best_bird['bbox']}")
        
        # 裁剪鸟类区域
        cropped_bird = detector.crop_bird_from_detection(image_path, best_bird)
        if cropped_bird:
            # 保存裁剪后的图像
            crop_save_path = os.path.join(script_dir, 'cropped_bird.jpg')
            cropped_bird.save(crop_save_path)
            print(f"  裁剪图像已保存到: {crop_save_path}")
            
            # 显示裁剪图像信息
            print(f"  裁剪图像尺寸: {cropped_bird.size}")
    
    # 可视化检测结果
    visualization_path = os.path.join(script_dir, 'detection_result.jpg')
    detector.visualize_detection(image_path, detections, visualization_path)

if __name__ == "__main__":
    test_yolo_bird_detection()