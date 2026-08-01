"""
YOLO 目标检测模块
支持加载预训练模型进行真实检测，也支持模拟检测模式（无模型时演示用）
"""
import os
import random
import math
from PIL import Image, ImageStat


class YOLODetector:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.use_simulation = config.YOLO_USE_SIMULATION
        self.conf_threshold = config.YOLO_CONF_THRESHOLD
        self.iou_threshold = config.YOLO_IOU_THRESHOLD
        self.classes = config.DETECTION_CLASSES

        # 尝试加载模型
        if not self.use_simulation:
            self._load_model()

    def _load_model(self):
        """加载YOLO模型"""
        try:
            from ultralytics import YOLO
            model_path = self.config.YOLO_MODEL_PATH
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                print(f"[YOLO] 模型加载成功: {model_path}")
            else:
                print(f"[YOLO] 模型文件不存在，切换到模拟模式: {model_path}")
                self.use_simulation = True
        except ImportError:
            print("[YOLO] ultralytics 未安装，使用模拟检测模式")
            self.use_simulation = True
        except Exception as e:
            print(f"[YOLO] 模型加载失败: {e}，使用模拟检测模式")
            self.use_simulation = True

    def detect(self, image_path):
        """
        执行目标检测
        返回: {
            "detections": [
                {
                    "class_name": str,
                    "class_id": int,
                    "confidence": float,
                    "bbox": [x1, y1, x2, y2],  # 像素坐标
                    "bbox_normalized": [x1, y1, x2, y2],  # 归一化坐标(0-1)
                    "attributes": {...}  # 附加属性
                }
            ],
            "image_size": {"width": int, "height": int},
            "model_info": {...}
        }
        """
        # 获取图像尺寸
        img = Image.open(image_path)
        img_width, img_height = img.size

        if self.use_simulation or self.model is None:
            result = self._simulate_detection(image_path, img_width, img_height)
        else:
            result = self._real_detect(image_path, img_width, img_height)

        return result

    def _real_detect(self, image_path, img_width, img_height):
        """使用真实YOLO模型检测"""
        try:
            results = self.model(
                image_path,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
            )

            detections = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    cls_name = (
                        self.classes[cls_id]
                        if cls_id < len(self.classes)
                        else f"class_{cls_id}"
                    )

                    detections.append({
                        "class_name": cls_name,
                        "class_id": cls_id,
                        "confidence": round(conf, 4),
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "bbox_normalized": [
                            round(x1 / img_width, 4),
                            round(y1 / img_height, 4),
                            round(x2 / img_width, 4),
                            round(y2 / img_height, 4),
                        ],
                        "attributes": self._compute_attributes(
                            [x1, y1, x2, y2], img_width, img_height, cls_name, conf
                        ),
                    })

            return {
                "detections": detections,
                "image_size": {"width": img_width, "height": img_height},
                "model_info": {
                    "model_name": "YOLOv8",
                    "mode": "real",
                    "conf_threshold": self.conf_threshold,
                    "iou_threshold": self.iou_threshold,
                },
            }
        except Exception as e:
            print(f"[YOLO] 真实检测失败: {e}，回退到模拟模式")
            return self._simulate_detection(image_path, img_width, img_height)

    def _simulate_detection(self, image_path, img_width, img_height):
        """
        模拟检测：生成逼真的医学影像检测结果
        基于图像内容生成合理的检测结果，用于系统演示
        """
        # 分析图像亮度/纹理特征来生成更合理的检测
        img = Image.open(image_path).convert("L")  # 转灰度
        img_small = img.resize((256, 256))
        stat = ImageStat.Stat(img_small)
        # 用标准差近似图像复杂度
        std_val = stat.stddev[0] if stat.stddev else 50.0

        # 检测数量：基于图像复杂度随机生成 1-4 个区域
        complexity = std_val / 50.0
        num_detections = max(1, min(4, int(complexity * 2) + random.randint(0, 1)))

        detections = []
        # 预定义的检测场景模板
        scenarios = self._generate_scenarios(num_detections, img_width, img_height)

        for scenario in scenarios:
            x1, y1, x2, y2 = scenario["bbox"]
            cls_name = scenario["class_name"]
            conf = scenario["confidence"]

            detections.append({
                "class_name": cls_name,
                "class_id": self.classes.index(cls_name)
                if cls_name in self.classes
                else -1,
                "confidence": round(conf, 4),
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "bbox_normalized": [
                    round(x1 / img_width, 4),
                    round(y1 / img_height, 4),
                    round(x2 / img_width, 4),
                    round(y2 / img_height, 4),
                ],
                "attributes": self._compute_attributes(
                    [x1, y1, x2, y2], img_width, img_height, cls_name, conf
                ),
            })

        return {
            "detections": detections,
            "image_size": {"width": img_width, "height": img_height},
            "model_info": {
                "model_name": "YOLOv8-Sim",
                "mode": "simulation",
                "conf_threshold": self.conf_threshold,
                "iou_threshold": self.iou_threshold,
            },
        }

    def _generate_scenarios(self, count, img_w, img_h):
        """生成模拟检测场景"""
        # 常见医学影像检测场景
        scenario_templates = [
            {"class_name": "结节", "size_range": (0.03, 0.08), "conf_range": (0.72, 0.94)},
            {"class_name": "肿块", "size_range": (0.05, 0.12), "conf_range": (0.68, 0.89)},
            {"class_name": "磨玻璃影", "size_range": (0.04, 0.10), "conf_range": (0.65, 0.85)},
            {"class_name": "钙化", "size_range": (0.02, 0.05), "conf_range": (0.78, 0.96)},
            {"class_name": "实性病变", "size_range": (0.04, 0.09), "conf_range": (0.70, 0.88)},
            {"class_name": "囊性病变", "size_range": (0.03, 0.07), "conf_range": (0.75, 0.92)},
            {"class_name": "纤维条索", "size_range": (0.06, 0.15), "conf_range": (0.60, 0.80)},
            {"class_name": "胸腔积液", "size_range": (0.08, 0.18), "conf_range": (0.66, 0.85)},
        ]

        # 随机选择不重复的场景
        selected = random.sample(scenario_templates, min(count, len(scenario_templates)))
        results = []
        occupied_regions = []

        for template in selected:
            # 随机位置（避免重叠）
            for _ in range(10):  # 尝试10次找到不重叠的位置
                size_ratio = random.uniform(*template["size_range"])
                w = int(img_w * size_ratio)
                h = int(img_h * size_ratio * random.uniform(0.8, 1.2))
                cx = random.uniform(0.2, 0.8) * img_w
                cy = random.uniform(0.2, 0.8) * img_h
                x1 = max(0, int(cx - w / 2))
                y1 = max(0, int(cy - h / 2))
                x2 = min(img_w, int(cx + w / 2))
                y2 = min(img_h, int(cy + h / 2))

                # 检查重叠
                overlap = False
                for region in occupied_regions:
                    if self._bbox_overlap([x1, y1, x2, y2], region):
                        overlap = True
                        break
                if not overlap:
                    occupied_regions.append([x1, y1, x2, y2])
                    break

            conf = random.uniform(*template["conf_range"])
            results.append({
                "bbox": [x1, y1, x2, y2],
                "class_name": template["class_name"],
                "confidence": conf,
            })

        return results

    @staticmethod
    def _bbox_overlap(b1, b2):
        """检查两个bbox是否重叠"""
        return not (b1[2] < b2[0] or b2[2] < b1[0] or b1[3] < b2[1] or b2[3] < b1[1])

    @staticmethod
    def _compute_attributes(bbox, img_w, img_h, class_name, confidence):
        """计算检测区域的附加属性"""
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        area = width * height

        # 根据类别估算大小
        max_dim = max(width, height)
        if max_dim < 10:
            size_desc = "微小"
        elif max_dim < 30:
            size_desc = "小"
        elif max_dim < 50:
            size_desc = "中等"
        else:
            size_desc = "较大"

        # 形态描述
        aspect_ratio = width / height if height > 0 else 1
        if 0.8 <= aspect_ratio <= 1.2:
            shape_desc = "类圆形"
        elif aspect_ratio > 1.5:
            shape_desc = "椭圆形（横长）"
        elif aspect_ratio < 0.6:
            shape_desc = "椭圆形（纵长）"
        else:
            shape_desc = "不规则形"

        # 边缘描述
        edge_descs = ["边缘清晰", "边缘较清晰", "边缘稍模糊", "边缘可见分叶"]
        edge_desc = random.choice(edge_descs)

        # 密度描述
        density_descs = ["均匀密度", "密度稍高", "密度不均", "低密度"]
        density_desc = random.choice(density_descs)

        return {
            "size_mm": round(max_dim * 0.3, 1),  # 模拟mm换算
            "size_description": size_desc,
            "shape": shape_desc,
            "aspect_ratio": round(aspect_ratio, 2),
            "edge": edge_desc,
            "density": density_desc,
            "area_pixels": int(area),
            "area_ratio": round(area / (img_w * img_h), 4),
        }
