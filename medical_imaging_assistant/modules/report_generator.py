"""
诊断报告生成模块
"""
from datetime import datetime


class ReportGenerator:
    def __init__(self):
        pass

    def generate(self, record_id, patient_info, detection_result, analysis_result, image_filename):
        """生成结构化诊断报告"""
        now = datetime.now()

        report = {
            "report_id": f"RPT-{record_id}",
            "report_date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "patient_info": {
                "name": patient_info.get("name", ""),
                "age": patient_info.get("age", ""),
                "gender": patient_info.get("gender", ""),
            },
            "exam_info": {
                "type": patient_info.get("exam_type", ""),
                "clinical_info": patient_info.get("clinical_info", ""),
                "image_filename": image_filename,
            },
            "detection_summary": {
                "total_regions": len(detection_result.get("detections", [])),
                "detections": [
                    {
                        "class_name": d["class_name"],
                        "confidence": d["confidence"],
                        "bbox": d["bbox"],
                        "size_mm": d.get("attributes", {}).get("size_mm", 0),
                        "shape": d.get("attributes", {}).get("shape", ""),
                        "edge": d.get("attributes", {}).get("edge", ""),
                        "density": d.get("attributes", {}).get("density", ""),
                    }
                    for d in detection_result.get("detections", [])
                ],
            },
            "analysis_summary": {
                "overall_impression": analysis_result.get("overall_impression", ""),
                "risk_level": analysis_result.get("risk_level", ""),
                "risk_score": analysis_result.get("risk_score", 0),
                "findings": analysis_result.get("findings", []),
                "risk_factors": analysis_result.get("risk_factors", []),
                "differential_diagnosis": analysis_result.get("differential_diagnosis", []),
                "recommendations": analysis_result.get("recommendations", []),
                "follow_up": analysis_result.get("follow_up", ""),
            },
            "disclaimer": analysis_result.get(
                "disclaimer",
                "本报告由AI辅助诊断系统自动生成，仅供参考，不能替代专业医师的诊断和治疗建议。"
            ),
        }

        return report
