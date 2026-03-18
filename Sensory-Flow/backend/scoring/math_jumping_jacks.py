"""
math_jumping_jacks.py

Scoring utilities for the "Jumping Jacks" exercise (6 Years and 7 Years)
in the same style as your other exercise math_*.py modules.

Expected input keys (dict row/params):
    shoulder_abduction_angle_mean_deg
    hip_abduction_distance_mean_norm
    hip_upward_displacement_mean_norm
    arm_leg_open_sync_mean_s
    arm_leg_close_sync_mean_s

Outputs:
- Individual scores per parameter
- total_score + interpretation (age-specific bands)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

Number = float


def _isfinite(x: Any) -> bool:
    try:
        return x is not None and float(x) == float(x) and float(x) not in (float("inf"), float("-inf"))
    except Exception:
        return False


@dataclass(frozen=True)
class Bin:
    """Numeric bin for scoring: lo <= x < hi"""
    lo: Optional[Number] = None
    hi: Optional[Number] = None
    score: int = 0


def _score_from_bins(x: Any, bins: List[Bin], default: Optional[int] = None) -> Optional[int]:
    if not _isfinite(x):
        return default
    v = float(x)
    for b in bins:
        lo_ok = True if b.lo is None else (v >= b.lo)
        hi_ok = True if b.hi is None else (v < b.hi)
        if lo_ok and hi_ok:
            return int(b.score)
    return default


def _sum_scores(scores: Dict[str, Optional[int]], keys: List[str]) -> Optional[int]:
    vals = [scores.get(k) for k in keys]
    if any(v is None for v in vals):
        return None
    return int(sum(int(v) for v in vals))


# =========================================================
# 6 YEARS
# =========================================================

def score_shoulder_abduction_angle_6y(x: Any) -> Optional[int]:
    # Higher is better
    return _score_from_bins(x, [
        Bin(None, 101.09, 1),
        Bin(101.09, 117.99, 2),
        Bin(117.99, 134.89, 3),
        Bin(134.89, 151.79, 4),
        Bin(151.79, 168.69, 5),
        Bin(168.69, None, 6),
    ])


def score_hip_abduction_distance_6y(x: Any) -> Optional[int]:
    # Higher is better
    return _score_from_bins(x, [
        Bin(None, 2.15, 1),
        Bin(2.15, 2.62, 2),
        Bin(2.62, 3.09, 3),
        Bin(3.09, 3.56, 4),
        Bin(3.56, 4.03, 5),
        Bin(4.03, 4.50, 6),
        Bin(4.50, 4.97, 7),
        Bin(4.97, None, 8),
    ])


def score_jump_6y(x: Any) -> Optional[int]:
    # Higher is better
    return _score_from_bins(x, [
        Bin(None, 0.93, 1),
        Bin(0.93, 1.84, 2),
        Bin(1.84, 2.75, 3),
        Bin(2.75, 3.66, 4),
        Bin(3.66, 4.57, 5),
        Bin(4.57, None, 6),
    ])


def score_arm_leg_open_sync_6y(x: Any) -> Optional[int]:
    # Lower is better (seconds)
    return _score_from_bins(x, [
        Bin(None, 0.28, 8),
        Bin(0.28, 0.59, 7),
        Bin(0.59, 0.90, 6),
        Bin(0.90, 1.21, 5),
        Bin(1.21, 1.52, 4),
        Bin(1.52, 1.83, 3),
        Bin(1.83, 2.14, 2),
        Bin(2.14, None, 1),
    ])


def score_arm_leg_close_sync_6y(x: Any) -> Optional[int]:
    # Lower is better (seconds)
    return _score_from_bins(x, [
        Bin(None, 0.36, 7),
        Bin(0.36, 1.09, 6),
        Bin(1.09, 1.82, 5),
        Bin(1.82, 2.55, 4),
        Bin(2.55, 3.28, 3),
        Bin(3.28, 4.01, 2),
        Bin(4.01, None, 1),
    ])


def interpret_total_6y(total: Optional[int]) -> Optional[str]:
    if total is None:
        return None
    t = int(total)
    if 0 <= t < 15:
        return "Extremely Below Average"
    if 15 <= t < 17:
        return "Well-Below Average"
    if 17 <= t < 19:
        return "Below Average"
    if 19 <= t < 23:
        return "Average"
    if 23 <= t < 25:
        return "Above average"
    if 25 <= t < 27:
        return "Well-Above Average"
    if 27 <= t <= 35:
        return "Extremely Above Average"
    return "Out of expected range"


def score_row_6y(row: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    out["shoulder_abduction_angle_score"] = score_shoulder_abduction_angle_6y(
        row.get("shoulder_abduction_angle_mean_deg")
    )
    out["hip_abduction_distance_score"] = score_hip_abduction_distance_6y(
        row.get("hip_abduction_distance_mean_norm")
    )
    out["jump_score"] = score_jump_6y(row.get("hip_upward_displacement_mean_norm"))
    out["arm_leg_open_sync_score"] = score_arm_leg_open_sync_6y(row.get("arm_leg_open_sync_mean_s"))
    out["arm_leg_close_sync_score"] = score_arm_leg_close_sync_6y(row.get("arm_leg_close_sync_mean_s"))

    keys = [
        "shoulder_abduction_angle_score",
        "hip_abduction_distance_score",
        "jump_score",
        "arm_leg_open_sync_score",
        "arm_leg_close_sync_score",
    ]
    out["total_score"] = _sum_scores(out, keys)
    out["interpretation"] = interpret_total_6y(out["total_score"])
    out["max_total"] = 35
    return out


# =========================================================
# 7 YEARS
# =========================================================

def score_shoulder_abduction_angle_7y(x: Any) -> Optional[int]:
    # Higher is better. Boundary 3/4 set so ~140.7 maps to 3 (match original rubric).
    return _score_from_bins(x, [
        Bin(None, 114.88, 1),
        Bin(114.88, 127.20, 2),
        Bin(127.20, 142.0, 3),
        Bin(142.0, 151.84, 4),
        Bin(151.84, 164.16, 5),
        Bin(164.16, 176.48, 6),
        Bin(176.48, None, 7),
    ])


def score_hip_abduction_distance_7y(x: Any) -> Optional[int]:
    # Higher is better
    return _score_from_bins(x, [
        Bin(None, 1.71, 1),
        Bin(1.71, 2.35, 2),
        Bin(2.35, 2.99, 3),
        Bin(2.99, 3.63, 4),
        Bin(3.63, 4.27, 5),
        Bin(4.27, 4.91, 6),
        Bin(4.91, 5.55, 7),
        Bin(5.55, None, 8),
    ])


def score_jump_7y(x: Any) -> Optional[int]:
    # Higher is better
    return _score_from_bins(x, [
        Bin(None, 0.41, 1),
        Bin(0.41, 1.73, 2),
        Bin(1.73, 3.05, 3),
        Bin(3.05, 4.37, 4),
        Bin(4.37, 5.69, 5),
        Bin(5.69, None, 6),
    ])


def score_arm_leg_open_sync_7y(x: Any) -> Optional[int]:
    # Lower is better (seconds)
    return _score_from_bins(x, [
        Bin(None, 0.41, 8),
        Bin(0.41, 0.62, 7),
        Bin(0.62, 0.83, 6),
        Bin(0.83, 1.04, 5),
        Bin(1.04, 1.25, 4),
        Bin(1.25, 1.46, 3),
        Bin(1.46, 1.67, 2),
        Bin(1.67, None, 1),
    ])


def score_arm_leg_close_sync_7y(x: Any) -> Optional[int]:
    # Lower is better (seconds)
    return _score_from_bins(x, [
        Bin(None, 0.39, 7),
        Bin(0.39, 0.97, 6),
        Bin(0.97, 1.55, 5),
        Bin(1.55, 2.13, 4),
        Bin(2.13, 2.71, 3),
        Bin(2.71, 3.29, 2),
        Bin(3.29, None, 1),
    ])


def interpret_total_7y(total: Optional[int]) -> Optional[str]:
    if total is None:
        return None
    t = int(total)
    if 0 <= t < 14:
        return "Extremely Below Average"
    if 14 <= t < 16:
        return "Well-Below Average"
    if 16 <= t < 18:
        return "Below Average"
    if 18 <= t < 22:
        return "Average"
    if 22 <= t < 24:
        return "Above average"
    if 24 <= t < 26:
        return "Well-Above Average"
    if 26 <= t <= 36:
        return "Extremely Above Average"
    return "Out of expected range"


def score_row_7y(row: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    out["shoulder_abduction_angle_score"] = score_shoulder_abduction_angle_7y(
        row.get("shoulder_abduction_angle_mean_deg")
    )
    out["hip_abduction_distance_score"] = score_hip_abduction_distance_7y(
        row.get("hip_abduction_distance_mean_norm")
    )
    out["jump_score"] = score_jump_7y(row.get("hip_upward_displacement_mean_norm"))
    out["arm_leg_open_sync_score"] = score_arm_leg_open_sync_7y(row.get("arm_leg_open_sync_mean_s"))
    out["arm_leg_close_sync_score"] = score_arm_leg_close_sync_7y(row.get("arm_leg_close_sync_mean_s"))

    keys = [
        "shoulder_abduction_angle_score",
        "hip_abduction_distance_score",
        "jump_score",
        "arm_leg_open_sync_score",
        "arm_leg_close_sync_score",
    ]
    out["total_score"] = _sum_scores(out, keys)
    out["interpretation"] = interpret_total_7y(out["total_score"])
    out["max_total"] = 36
    return out


# =========================================================
# Convenience selector
# =========================================================

def score_row(row: Dict[str, Any], age_years: int) -> Dict[str, Any]:
    if int(age_years) == 6:
        return score_row_6y(row)
    if int(age_years) == 7:
        return score_row_7y(row)
    raise ValueError("age_years must be 6 or 7 for Jumping Jacks scoring.")
