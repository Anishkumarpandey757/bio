"""Prone Extension scoring (6y & 7y)

Inputs expected from your CV/preprocess pipeline (per clip):
- neck_mean_deg   (neck extension angle)
- trunk_mean_deg  (trunk extension angle)
- hip_mean_deg    (hip extension angle)
- knee_mean_deg   (knee flexion angle while holding prone extension)
- hold_duration_s (seconds)

Doc sources used:
- Corrected Prone Extension FS (6 Years).docx
- Corrected Prone Extension FS (7 Years).docx
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Bin:
    lo: float
    hi: Optional[float]  # None => +inf
    score: int

    def contains(self, x: float) -> bool:
        if self.hi is None:
            return x >= self.lo
        return self.lo <= x < self.hi


def _score_from_bins(x: Optional[float], bins: Sequence[Bin]) -> Optional[int]:
    if x is None:
        return None
    try:
        xf = float(x)
    except Exception:
        return None
    if xf != xf:  # NaN
        return None

    for b in bins:
        if b.contains(xf):
            return int(b.score)

    # safety fallback
    if bins:
        if xf < bins[0].lo:
            return int(bins[0].score)
        return int(bins[-1].score)
    return None


def _interpret_total(total: Optional[int], ranges: Sequence[Tuple[int, int, str]]) -> Optional[str]:
    if total is None:
        return None
    for lo, hi, label in ranges:
        if lo <= total < hi:
            return label
    if ranges and total >= ranges[-1][0]:
        return ranges[-1][2]
    return None


# ---------------------------
# Prone Extension — 6 Years
# ---------------------------

# Neck extension angle (deg)
# NOTE: 6y sheet starts at "Below -2" (no -3 bin listed). We implement exactly the provided raw ranges.
_PRO6_NECK = [
    Bin(0.00, 7.50, 1),
    Bin(7.50, 17.95, 2),
    Bin(17.95, 28.40, 3),
    Bin(28.40, 38.85, 4),
    Bin(38.85, None, 5),
]

# Trunk extension angle (deg)
_PRO6_TRUNK = [
    Bin(0.00, 3.52, 1),
    Bin(3.52, 5.65, 2),
    Bin(5.65, 7.78, 3),
    Bin(7.78, 9.91, 4),
    Bin(9.91, 12.04, 5),
    Bin(12.04, 14.17, 6),
    Bin(14.17, 16.30, 7),
    Bin(16.30, None, 8),
]

# Hip extension angle (deg)
_PRO6_HIP = [
    Bin(0.00, 11.45, 1),
    Bin(11.45, 13.67, 2),
    Bin(13.67, 15.89, 3),
    Bin(15.89, 18.10, 4),
    Bin(18.10, 20.00, 5),
    Bin(20.00, None, 6),
]

# Knee flexion angle (deg) — reverse scoring: larger knee flexion gets LOWER points.
_PRO6_KNEE = [
    Bin(0.00, 4.74, 8),
    Bin(4.74, 6.75, 7),
    Bin(6.75, 8.76, 6),
    Bin(8.76, 10.78, 5),
    Bin(10.78, 12.79, 4),
    Bin(12.79, 14.81, 3),
    Bin(14.81, 16.82, 2),
    Bin(16.82, None, 1),
]

# Hold duration (s)
_PRO6_HOLD = [
    Bin(0.00, 8.56, 1),
    Bin(8.56, 23.10, 2),
    Bin(23.10, 37.64, 3),
    Bin(37.64, 52.18, 4),
    Bin(52.18, 66.71, 5),
    Bin(66.71, 81.25, 6),
    Bin(81.25, 95.79, 7),
    Bin(95.79, None, 8),
]

_PRO6_TOTAL_RANGES = [
    (0, 13, "Extremely Below Average"),
    (13, 16, "Well-Below Average"),
    (16, 19, "Below Average"),
    (19, 25, "Average"),
    (25, 28, "Above average"),
    (28, 31, "Well-Above Average"),
    (31, 37, "Extremely Above Average"),
]


def score_neck_ext_6y(neck_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(neck_mean_deg, _PRO6_NECK)


def score_trunk_ext_6y(trunk_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(trunk_mean_deg, _PRO6_TRUNK)


def score_hip_ext_6y(hip_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(hip_mean_deg, _PRO6_HIP)


def score_knee_flex_6y(knee_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(knee_mean_deg, _PRO6_KNEE)


def score_hold_6y(hold_duration_s: Optional[float]) -> Optional[int]:
    return _score_from_bins(hold_duration_s, _PRO6_HOLD)


def score_row_prone_6y(row: Dict[str, float]) -> Dict[str, Optional[object]]:
    neck = score_neck_ext_6y(row.get("neck_mean_deg"))
    trunk = score_trunk_ext_6y(row.get("trunk_mean_deg"))
    hip = score_hip_ext_6y(row.get("hip_mean_deg"))
    knee = score_knee_flex_6y(row.get("knee_mean_deg"))
    hold = score_hold_6y(row.get("hold_duration_s"))

    parts = [neck, trunk, hip, knee, hold]
    total = int(sum(p for p in parts if isinstance(p, int))) if all(isinstance(p, int) for p in parts) else None

    return {
        "neck_ext_score": neck,
        "trunk_ext_score": trunk,
        "hip_ext_score": hip,
        "knee_flex_score": knee,
        "hold_duration_score": hold,
        "total_score": total,
        "interpretation": _interpret_total(total, _PRO6_TOTAL_RANGES),
        "max_score": 36,
    }


# ---------------------------
# Prone Extension — 7 Years
# ---------------------------

_PRO7_NECK = [
    Bin(0.00, 6.33, 1),
    Bin(6.33, 15.51, 2),
    Bin(15.51, 24.68, 3),
    Bin(24.68, 33.86, 4),
    Bin(33.86, 43.04, 5),
    Bin(43.04, None, 6),
]

_PRO7_TRUNK = [
    Bin(0.00, 4.33, 1),
    Bin(4.33, 6.47, 2),
    Bin(6.47, 8.62, 3),
    Bin(8.62, 10.76, 4),
    Bin(10.76, 12.91, 5),
    Bin(12.91, 15.05, 6),
    Bin(15.05, 17.19, 7),
    Bin(17.19, None, 8),
]

_PRO7_HIP = [
    Bin(0.00, 8.82, 1),
    Bin(8.82, 11.85, 2),
    Bin(11.85, 14.88, 3),
    Bin(14.88, 17.92, 4),
    Bin(17.92, 20.00, 5),
    Bin(20.00, None, 6),
]

# Knee flexion angle (deg) — reverse scoring (points 1..7 in the sheet)
_PRO7_KNEE = [
    Bin(0.00, 3.34, 7),
    Bin(3.34, 7.60, 6),
    Bin(7.60, 11.86, 5),
    Bin(11.86, 16.12, 4),
    Bin(16.12, 20.38, 3),
    Bin(20.38, 24.64, 2),
    Bin(24.64, None, 1),
]

_PRO7_HOLD = [
    Bin(0.00, 9.78, 1),
    Bin(9.78, 27.01, 2),
    Bin(27.01, 44.23, 3),
    Bin(44.23, 61.46, 4),
    Bin(61.46, 78.69, 5),
    Bin(78.69, 95.92, 6),
    Bin(95.92, 113.15, 7),
    Bin(113.15, None, 8),
]

_PRO7_TOTAL_RANGES = [
    (0, 14, "Extremely Below Average"),
    (14, 17, "Well-Below Average"),
    (17, 20, "Below Average"),
    (20, 26, "Average"),
    (26, 29, "Above average"),
    (29, 32, "Well-Above Average"),
    (32, 36, "Extremely Above Average"),
]


def score_neck_ext_7y(neck_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(neck_mean_deg, _PRO7_NECK)


def score_trunk_ext_7y(trunk_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(trunk_mean_deg, _PRO7_TRUNK)


def score_hip_ext_7y(hip_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(hip_mean_deg, _PRO7_HIP)


def score_knee_flex_7y(knee_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(knee_mean_deg, _PRO7_KNEE)


def score_hold_7y(hold_duration_s: Optional[float]) -> Optional[int]:
    return _score_from_bins(hold_duration_s, _PRO7_HOLD)


def score_row_prone_7y(row: Dict[str, float]) -> Dict[str, Optional[object]]:
    neck = score_neck_ext_7y(row.get("neck_mean_deg"))
    trunk = score_trunk_ext_7y(row.get("trunk_mean_deg"))
    hip = score_hip_ext_7y(row.get("hip_mean_deg"))
    knee = score_knee_flex_7y(row.get("knee_mean_deg"))
    hold = score_hold_7y(row.get("hold_duration_s"))

    parts = [neck, trunk, hip, knee, hold]
    total = int(sum(p for p in parts if isinstance(p, int))) if all(isinstance(p, int) for p in parts) else None

    return {
        "neck_ext_score": neck,
        "trunk_ext_score": trunk,
        "hip_ext_score": hip,
        "knee_flex_score": knee,
        "hold_duration_score": hold,
        "total_score": total,
        "interpretation": _interpret_total(total, _PRO7_TOTAL_RANGES),
        "max_score": 35,
    }


def score_row_prone(row: Dict[str, float], age_years: int) -> Dict[str, Optional[object]]:
    if age_years == 6:
        return score_row_prone_6y(row)
    if age_years == 7:
        return score_row_prone_7y(row)
    raise ValueError("age_years must be 6 or 7")
