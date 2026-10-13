import numpy as np
from typing import Tuple

def compute_mask_iou(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float:
    """
    حساب Intersection over Union (IoU) لأقنعة تقسيم اللهب/السخام (Flame segmentation masks).
    """
    pred_bool = pred_mask.astype(bool)
    gt_bool = gt_mask.astype(bool)

    intersection = np.logical_and(pred_bool, gt_bool).sum()
    union = np.logical_or(pred_bool, gt_bool).sum()

    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    return float(intersection / union)

def compute_dice_coefficient(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float:
    """
    حساب معمل Dice (F1-score مكافئ) لتحديد دقة حدود اللهب.
    """
    pred_bool = pred_mask.astype(bool)
    gt_bool = gt_mask.astype(bool)

    intersection = np.logical_and(pred_bool, gt_bool).sum()
    total_area = pred_bool.sum() + gt_bool.sum()

    if total_area == 0:
        return 1.0
    return float((2.0 * intersection) / total_area)

def compute_precision_recall_masks(pred_mask: np.ndarray, gt_mask: np.ndarray) -> Tuple[float, float]:
    """
    حساب الدقة والاستدعاء على مستوى البكسل (Pixel-level Precision & Recall).
    """
    pred_bool = pred_mask.astype(bool)
    gt_bool = gt_mask.astype(bool)

    intersection = np.logical_and(pred_bool, gt_bool).sum()
    pred_sum = pred_bool.sum()
    gt_sum = gt_bool.sum()

    precision = float(intersection / pred_sum) if pred_sum > 0 else 0.0
    recall = float(intersection / gt_sum) if gt_sum > 0 else 0.0

    return precision, recall
