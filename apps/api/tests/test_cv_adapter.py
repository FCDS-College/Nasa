from PIL import Image
import cv2
import numpy as np

from flame_api.worker import _adapt_result


def test_cv_result_adapter_preserves_measurement_semantics(tmp_path):
    from api_contract import assert_contract_component

    image_path = tmp_path / "source.png"
    mask_path = tmp_path / "mask.png"
    Image.new("RGB", (64, 64), (255, 100, 10)).save(image_path)
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[16:48, 20:44] = 255
    cv2.imwrite(str(mask_path), mask)
    input_data = {
        "width": 64,
        "height": 64,
        "calibration": {"state": "absent", "scale_px_per_mm": None, "scale_source": None},
    }
    legacy = {
        "pipelineVersion": "cv-opencv-v1.1.0",
        "preprocessing": {"version": "letterbox-lanczos-v1", "scale": 1.0, "padX": 0, "padY": 0, "originalWidth": 64, "originalHeight": 64, "contentWidth": 64, "contentHeight": 64, "targetSize": 64},
        "detection": {"status": "PRESENT", "confidence": 0.8, "boundingBox": {"xmin": 20, "ymin": 16, "xmax": 44, "ymax": 48}, "modelName": "otsu-contour-baseline", "modelVersion": "1.1.0"},
        "segmentation": {"maskUri": str(mask_path)},
        "measurements": {"geometry": {"pixelArea": 768, "centroid": {"x": 32, "y": 32}, "perimeter": 112, "circularity": 0.77}, "appearance": {}},
        "confidenceAndQualityFlags": {"qualityFlags": {"blur": False, "saturationClipping": True, "lowLight": False, "multipleFlames": False, "occlusion": False}, "qualityMetrics": {"significantComponents": 1}, "segmenterConfidence": 0.9},
        "provenance": {"inputUri": str(image_path)},
    }

    mapped = _adapt_result(legacy, input_data, tmp_path)
    result = mapped["result"]

    assert result["detection"]["status"] == "present"
    assert_contract_component(result, "FlameAnalysisResult")
    assert result["measurements"]["appearance"]["saturated_fraction"]["value"] == 1.0
    assert result["measurements"]["appearance"]["mean_r"]["value"] == 255.0
    assert result["measurements"]["geometry_px"]["area"]["classification"] == "measured"
    assert result["measurements"]["geometry_physical"] is None
    assert "temperature" not in str(result).lower()
    assert all(0 <= point["x"] <= 64 and 0 <= point["y"] <= 64 for contour in result["segmentation"]["contours"] for point in contour)
    assert {warning["code"] for warning in mapped["warnings"]} == {"TEMPERATURE_NOT_AVAILABLE", "SCALE_CALIBRATION_ABSENT", "LOW_DETECTION_CONFIDENCE"}