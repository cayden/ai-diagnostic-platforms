"""YOLO 缺陷检测引擎

支持两种模式:
  1. simulation — 基于图像特征分析生成模拟检测结果，开箱即用
  2. model     — 加载预训练 YOLO 权重进行真实推理 (需 ultralytics 库)
"""

import os
import random
from PIL import Image, ImageStat

from config import Config


class YoloDetector:
    def __init__(self, config: Config):
        self.config = config
        self.mode = config.DETECTION_MODE
        self.model = None
        self.conf_threshold = config.YOLO_CONF_THRESHOLD
        self.iou_threshold = config.YOLO_IOU_THRESHOLD
        self.classes = config.DEFECT_CLASSES

        # 缺陷类型映射: class_id -> (code, name, severity, color)
        self.class_map = {}
        for cid, code, name, sev, color in self.classes:
            self.class_map[cid] = {
                "class_id": cid,
                "code": code,
                "name": name,
                "severity": sev,
                "color": color,
            }

        if self.mode == "model":
            self._load_model()

    def _load_model(self):
        """加载 YOLO 预训练模型"""
        try:
            from ultralytics import YOLO
            model_path = self.config.YOLO_MODEL_PATH
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                print(f"[YOLO] 模型已加载: {model_path}")
            else:
                print(f"[YOLO] 模型文件不存在: {model_path}，降级为模拟模式")
                self.mode = "simulation"
        except ImportError:
            print("[YOLO] ultralytics 未安装，降级为模拟模式")
            self.mode = "simulation"

    def detect(self, image_path: str) -> dict:
        """执行检测"""
        if self.mode == "model" and self.model:
            return self._detect_with_model(image_path)
        return self._simulate_detection(image_path)

    def _detect_with_model(self, image_path: str) -> dict:
        """使用真实 YOLO 模型推理"""
        img = Image.open(image_path)
        results = self.model(
            image_path,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
        )

        detections = []
        for r in results:
            boxes = r.boxes
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i])
                conf = float(boxes.conf[i])
                xyxy = boxes.xyxy[i].tolist()
                cls_info = self.class_map.get(cls_id, {})
                detections.append({
                    "class_id": cls_id,
                    "class_name": cls_info.get("name", f"unknown_{cls_id}"),
                    "code": cls_info.get("code", f"cls_{cls_id}"),
                    "confidence": round(conf, 4),
                    "severity": cls_info.get("severity", "minor"),
                    "color": cls_info.get("color", "#999999"),
                    "bbox": {
                        "x1": round(xyxy[0]),
                        "y1": round(xyxy[1]),
                        "x2": round(xyxy[2]),
                        "y2": round(xyxy[3]),
                    },
                    "bbox_norm": {
                        "x1": round(xyxy[0] / img.width, 4),
                        "y1": round(xyxy[1] / img.height, 4),
                        "x2": round(xyxy[2] / img.width, 4),
                        "y2": round(xyxy[3] / img.height, 4),
                    },
                })

        return self._build_result(image_path, detections, img)

    def _simulate_detection(self, image_path: str) -> dict:
        """基于图像特征分析生成模拟检测结果"""
        img = Image.open(image_path).convert("RGB")
        w, h = img.size

        # 分析图像特征
        stat = ImageStat.Stat(img)
        brightness = sum(stat.mean) / len(stat.mean)   # 亮度 0-255
        contrast = max(stat.stddev) if stat.stddev else 0
        complexity = min(contrast / 80.0, 1.0)

        # 基于复杂度和随机数决定缺陷数量
        # 复杂度越高越可能检出缺陷
        base_count = int(complexity * 3)
        rng = random.Random(hash(os.path.basename(image_path)) % 10000)
        num_defects = rng.randint(max(0, base_count - 1), base_count + 1)

        # 有概率不检出缺陷 (合格品)
        if rng.random() < 0.3:
            num_defects = 0

        detections = []
        for _ in range(num_defects):
            cls = rng.choice(self.classes)
            cid, code, name, severity, color = cls

            # 生成检测框 — 随机分布在图像中
            box_w = rng.randint(max(20, int(w * 0.05)), max(40, int(w * 0.15)))
            box_h = rng.randint(max(20, int(h * 0.05)), max(40, int(h * 0.15)))
            x1 = rng.randint(0, max(1, w - box_w))
            y1 = rng.randint(0, max(1, h - box_h))
            x2 = x1 + box_w
            y2 = y1 + box_h

            conf = rng.uniform(self.conf_threshold, 0.98)

            detections.append({
                "class_id": cid,
                "class_name": name,
                "code": code,
                "confidence": round(conf, 4),
                "severity": severity,
                "color": color,
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "bbox_norm": {
                    "x1": round(x1 / w, 4),
                    "y1": round(y1 / h, 4),
                    "x2": round(x2 / w, 4),
                    "y2": round(y2 / h, 4),
                },
                # 模拟属性
                "attributes": self._gen_attributes(code, conf),
            })

        return self._build_result(image_path, detections, img)

    def _gen_attributes(self, code, conf):
        """根据缺陷类型生成模拟属性"""
        rng = random.Random()
        attrs = {
            "area_px2": rng.randint(50, 5000),
        }

        if code == "scratch":
            attrs["length_px"] = rng.randint(30, 200)
            attrs["orientation"] = rng.choice(["水平", "垂直", "斜向"])
            attrs["depth"] = "浅表"
        elif code == "dent":
            attrs["depth_mm"] = round(rng.uniform(0.1, 2.0), 2)
            attrs["area_mm2"] = round(rng.uniform(0.5, 10.0), 2)
        elif code == "crack":
            attrs["length_mm"] = round(rng.uniform(2.0, 15.0), 2)
            attrs["direction"] = rng.choice(["纵向", "横向", "不规则"])
            attrs["width_mm"] = round(rng.uniform(0.05, 0.5), 3)
        elif code == "stain":
            attrs["area_mm2"] = round(rng.uniform(1.0, 20.0), 2)
            attrs["type"] = rng.choice(["油污", "水渍", "灰尘", "指纹"])
        elif code == "deformation":
            attrs["deviation_mm"] = round(rng.uniform(0.5, 3.0), 2)
            attrs["direction"] = rng.choice(["弯曲", "扭曲", "胀大"])
        elif code == "missing_part":
            attrs["missing_item"] = rng.choice(["螺丝", "卡扣", "标签", "密封圈", "垫片"])
        elif code == "misalign":
            attrs["offset_mm"] = round(rng.uniform(0.5, 5.0), 2)
            attrs["direction"] = rng.choice(["左偏", "右偏", "上偏", "下偏"])
        elif code == "color_diff":
            attrs["delta_e"] = round(rng.uniform(1.5, 5.0), 2)
            attrs["direction"] = rng.choice(["偏亮", "偏暗", "偏色"])
        elif code == "burrs":
            attrs["location"] = rng.choice(["边缘", "孔位", "接缝"])
            attrs["size_mm"] = round(rng.uniform(0.1, 1.0), 2)
        elif code == "oxidation":
            attrs["area_mm2"] = round(rng.uniform(2.0, 30.0), 2)
            attrs["color"] = rng.choice(["黑色", "白色", "铜绿色"])

        return attrs

    def _build_result(self, image_path: str, detections: list, img: Image.Image) -> dict:
        """组装检测结果"""
        # 按严重度统计
        severity_counts = {"critical": 0, "major": 0, "minor": 0}
        for d in detections:
            sev = d.get("severity", "minor")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # 按类型统计
        type_counts = {}
        for d in detections:
            code = d.get("code", "unknown")
            type_counts[code] = type_counts.get(code, 0) + 1

        # 平均置信度
        avg_conf = sum(d["confidence"] for d in detections) / len(detections) if detections else 0

        return {
            "mode": self.mode,
            "image_size": {"width": img.width, "height": img.height},
            "total_detections": len(detections),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
            "avg_confidence": round(avg_conf, 4),
            "detections": detections,
            "conf_threshold": self.conf_threshold,
        }
