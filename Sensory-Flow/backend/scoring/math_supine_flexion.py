"""Supine Flexion scoring (6y & 7y)

This file mirrors the style of your existing per-test math.py files:
- small, pure functions
- deterministic scoring based on the FS (Form Sheet) ranges

Inputs expected from your CV/preprocess pipeline (per clip):
- neck_mean_deg   (neck flexion angle)
- trunk_mean_deg  (trunk flexion angle)
- hip_mean_deg    (hip flexion angle)
- knee_mean_deg   (knee flexion angle)
- hold_duration_s (seconds)

Doc sources used:
- Supine Flexion FS (6 years).docx
- Supine Flexion FS (7 Years).docx
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Number = float


@dataclass(frozen=True)
class Bin:
    """Closed-open interval bin: [lo, hi) except last bin may be open-ended."""

    lo: float
    hi: Optional[float]  # None => +inf
    score: int

    def contains(self, x: float) -> bool:
        if self.hi is None:
            return x >= self.lo
        return self.lo <= x < self.hi


def _score_from_bins(x: Optional[float], bins: Sequence[Bin]) -> Optional[int]:
    """Return score for x using bins; None if x is None/NaN or not matched."""
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

    # If it's below the first bin, return the first bin score (conservative).
    # This avoids None when minor rounding pushes slightly out-of-range.
    if bins:
        if xf < bins[0].lo:
            return int(bins[0].score)
        # If above all finite bins, return last bin score.
        return int(bins[-1].score)
    return None


def _interpret_total(total: Optional[int], ranges: Sequence[Tuple[int, int, str]]) -> Optional[str]:
    """ranges are [lo, hi) with label."""
    if total is None:
        return None
    for lo, hi, label in ranges:
        if lo <= total < hi:
            return label
    # if equals top boundary
    if ranges and total >= ranges[-1][0]:
        return ranges[-1][2]
    return None


# ---------------------------
# Supine Flexion — 6 Years
# ---------------------------

# Neck flexion angle (deg)
_SUP6_NECK = [
    Bin(0.00, 35.94, 1),
    Bin(35.94, 38.14, 2),
    Bin(38.14, 40.33, 3),
    Bin(40.33, 42.53, 4),
    Bin(42.53, 44.72, 5),
    Bin(44.72, None, 6),
]

# Trunk flexion angle (deg)
_SUP6_TRUNK = [
    Bin(0.00, 21.76, 1),
    Bin(21.76, 30.23, 2),
    Bin(30.23, 38.70, 3),
    Bin(38.70, 47.17, 4),
    Bin(47.17, 55.65, 5),
    Bin(55.65, 64.12, 6),
    Bin(64.12, 72.59, 7),
    Bin(72.59, None, 8),
]

# Hip flexion angle (deg)
_SUP6_HIP = [
    Bin(0.00, 64.59, 1),
    Bin(64.59, 75.62, 2),
    Bin(75.62, 86.66, 3),
    Bin(86.66, 97.69, 4),
    Bin(97.69, 108.72, 5),
    Bin(108.72, 119.76, 6),
    Bin(119.76, None, 7),  # Above +2
]

# Knee flexion angle (deg)
_SUP6_KNEE = [
    Bin(0.00, 122.75, 1),
    Bin(122.75, 125.56, 2),
    Bin(125.56, 128.36, 3),
    Bin(128.36, 131.17, 4),
    Bin(131.17, 133.97, 5),
    Bin(133.97, None, 6),
]

# Hold duration (s)
_SUP6_HOLD = [
    Bin(0.00, 14.99, 1),
    Bin(14.99, 22.97, 2),
    Bin(22.97, 30.94, 3),
    Bin(30.94, 38.91, 4),
    Bin(38.91, 46.88, 5),
    Bin(46.88, 54.86, 6),
    Bin(54.86, 62.83, 7),
    Bin(62.83, None, 8),
]

_SUP6_TOTAL_RANGES = [
    (0, 13, "Extremely Below Average"),
    (13, 16, "Well-Below Average"),
    (16, 19, "Below Average"),
    (19, 25, "Average"),
    (25, 28, "Above average"),
    (28, 31, "Well-Above Average"),
    (31, 36, "Extremely Above Average"),
]


def score_neck_flex_6y(neck_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(neck_mean_deg, _SUP6_NECK)


def score_trunk_flex_6y(trunk_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(trunk_mean_deg, _SUP6_TRUNK)


def score_hip_flex_6y(hip_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(hip_mean_deg, _SUP6_HIP)


def score_knee_flex_6y(knee_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(knee_mean_deg, _SUP6_KNEE)


def score_hold_6y(hold_duration_s: Optional[float]) -> Optional[int]:
    return _score_from_bins(hold_duration_s, _SUP6_HOLD)


def score_row_supine_6y(row: Dict[str, float]) -> Dict[str, Optional[object]]:
    """Score a single clip (6 years supine flexion)."""
    neck = score_neck_flex_6y(row.get("neck_mean_deg"))
    trunk = score_trunk_flex_6y(row.get("trunk_mean_deg"))
    hip = score_hip_flex_6y(row.get("hip_mean_deg"))
    knee = score_knee_flex_6y(row.get("knee_mean_deg"))
    hold = score_hold_6y(row.get("hold_duration_s"))

    parts = [neck, trunk, hip, knee, hold]
    total = int(sum(p for p in parts if isinstance(p, int))) if all(isinstance(p, int) for p in parts) else None

    return {
        "neck_flex_score": neck,
        "trunk_flex_score": trunk,
        "hip_flex_score": hip,
        "knee_flex_score": knee,
        "hold_duration_score": hold,
        "total_score": total,
        "interpretation": _interpret_total(total, _SUP6_TOTAL_RANGES),
        "max_score": 35,
    }


# ---------------------------
# Supine Flexion — 7 Years
# ---------------------------

_SUP7_NECK = [
    Bin(0.00, 37.92, 1),
    Bin(37.92, 39.83, 2),
    Bin(39.83, 41.73, 3),
    Bin(41.73, 43.64, 4),
    Bin(43.64, 45.00, 5),
    Bin(45.00, None, 6),
]

_SUP7_TRUNK = [
    Bin(0.00, 27.11, 1),
    Bin(27.11, 35.38, 2),
    Bin(35.38, 43.66, 3),
    Bin(43.66, 51.93, 4),
    Bin(51.93, 60.20, 5),
    Bin(60.20, 68.47, 6),
    Bin(68.47, 76.74, 7),
    Bin(76.74, None, 8),
]

_SUP7_HIP = [
    Bin(0.00, 67.25, 1),
    Bin(67.25, 78.64, 2),
    Bin(78.64, 90.03, 3),
    Bin(90.03, 101.42, 4),
    Bin(101.42, 112.80, 5),
    Bin(112.80, None, 6),
]

_SUP7_KNEE = [
    Bin(0.00, 125.52, 1),
    Bin(125.52, 127.88, 2),
    Bin(127.88, 130.24, 3),
    Bin(130.24, 132.60, 4),
    Bin(132.60, 134.96, 5),
    Bin(134.96, None, 6),
]

_SUP7_HOLD = [
    Bin(0.00, 9.44, 1),
    Bin(9.44, 22.41, 2),
    Bin(22.41, 35.38, 3),
    Bin(35.38, 48.35, 4),
    Bin(48.35, 61.31, 5),
    Bin(61.31, 74.28, 6),
    Bin(74.28, 87.25, 7),
    Bin(87.25, None, 8),
]

_SUP7_TOTAL_RANGES = [
    (0, 14, "Extremely Below Average"),
    (14, 17, "Well-Below Average"),
    (17, 20, "Below Average"),
    (20, 26, "Average"),
    (26, 29, "Above average"),
    (29, 32, "Well-Above Average"),
    (32, 35, "Extremely Above Average"),
]


def score_neck_flex_7y(neck_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(neck_mean_deg, _SUP7_NECK)


def score_trunk_flex_7y(trunk_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(trunk_mean_deg, _SUP7_TRUNK)


def score_hip_flex_7y(hip_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(hip_mean_deg, _SUP7_HIP)


def score_knee_flex_7y(knee_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(knee_mean_deg, _SUP7_KNEE)


def score_hold_7y(hold_duration_s: Optional[float]) -> Optional[int]:
    return _score_from_bins(hold_duration_s, _SUP7_HOLD)


def score_row_supine_7y(row: Dict[str, float]) -> Dict[str, Optional[object]]:
    neck = score_neck_flex_7y(row.get("neck_mean_deg"))
    trunk = score_trunk_flex_7y(row.get("trunk_mean_deg"))
    hip = score_hip_flex_7y(row.get("hip_mean_deg"))
    knee = score_knee_flex_7y(row.get("knee_mean_deg"))
    hold = score_hold_7y(row.get("hold_duration_s"))

    parts = [neck, trunk, hip, knee, hold]
    total = int(sum(p for p in parts if isinstance(p, int))) if all(isinstance(p, int) for p in parts) else None

    return {
        "neck_flex_score": neck,
        "trunk_flex_score": trunk,
        "hip_flex_score": hip,
        "knee_flex_score": knee,
        "hold_duration_score": hold,
        "total_score": total,
        "interpretation": _interpret_total(total, _SUP7_TOTAL_RANGES),
        "max_score": 34,
    }


# ---------------------------
# Convenience router
# ---------------------------

def score_row_supine(row: Dict[str, float], age_years: int) -> Dict[str, Optional[object]]:
    """age_years: 6 or 7"""
    if age_years == 6:
        return score_row_supine_6y(row)
    if age_years == 7:
        return score_row_supine_7y(row)
    raise ValueError("age_years must be 6 or 7")
