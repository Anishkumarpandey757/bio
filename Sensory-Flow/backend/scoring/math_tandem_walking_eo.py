"""Tandem Walking — Eyes Open (EO) scoring (6y & 7y)

Implements deterministic scoring based on the Form Sheet (FS) ranges.

Expected inputs (from your CV/preprocess pipeline), per clip:
- ml_sway_mean_deg   (Mediolateral sway mean; front view)
- ml_sway_sd_deg     (Mediolateral sway variability/SD; front view)
- ap_sway_mean_deg   (Anteroposterior sway mean; side/profile view)
- ap_sway_sd_deg     (Anteroposterior sway variability/SD; side/profile view)
- mean_step_gap_cm   (Mean step gap in cm; profile)
- n_understeps       (Number of understeps; raw display only; not scored)

Doc sources used:
- Tandem Walking EO FS (6 Years).docx
- Tandem Walking EO FS (7 Years).docx
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

Number = float


@dataclass(frozen=True)
class Bin:
    """Closed-open interval bin: [lo, hi) except last bin may be open-ended (hi=None)."""
    lo: float
    hi: Optional[float]  # None => +inf
    score: int

    def contains(self, x: float) -> bool:
        if self.hi is None:
            return x >= self.lo
        return self.lo <= x < self.hi


def _score_from_bins(x: Optional[float], bins: Sequence[Bin]) -> Optional[int]:
    """Return score for x using bins; None if x is None/NaN/non-numeric."""
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

    # Guard against tiny rounding error pushing outside.
    if bins:
        if xf < bins[0].lo:
            return int(bins[0].score)
        return int(bins[-1].score)
    return None


def _interpret_total(total: Optional[int], ranges: Sequence[Tuple[int, int, str]]) -> Optional[str]:
    """ranges are [lo, hi) with a label."""
    if total is None:
        return None
    for lo, hi, label in ranges:
        if lo <= total < hi:
            return label
    if ranges and total >= ranges[-1][0]:
        return ranges[-1][2]
    return None


# ==========================
# EO — 6 Years (from FS)
# ==========================

_EO6_ML_MEAN = [
    Bin(11.83, None, 1),
    Bin(8.97, 11.83, 2),
    Bin(6.11, 8.97, 3),
    Bin(3.25, 6.11, 4),
    Bin(0.39, 3.25, 5),
    Bin(0.00, 0.39, 6),
]

_EO6_ML_SD = [
    Bin(4.59, None, 1),
    Bin(3.78, 4.59, 2),
    Bin(2.97, 3.78, 3),
    Bin(2.16, 2.97, 4),
    Bin(1.35, 2.16, 5),
    Bin(0.54, 1.35, 6),
    Bin(0.00, 0.54, 7),
]

_EO6_AP_MEAN = [
    Bin(4.76, None, 1),
    Bin(3.98, 4.76, 2),
    Bin(3.20, 3.98, 3),
    Bin(2.42, 3.20, 4),
    Bin(1.64, 2.42, 5),
    Bin(0.86, 1.64, 6),
    Bin(0.00, 0.86, 7),
]

_EO6_AP_SD = [
    Bin(4.21, None, 1),
    Bin(3.55, 4.21, 2),
    Bin(2.89, 3.55, 3),
    Bin(2.23, 2.89, 4),
    Bin(1.57, 2.23, 5),
    Bin(0.91, 1.57, 6),
    Bin(0.25, 0.91, 7),
    Bin(0.00, 0.25, 8),
]

_EO6_STEP_GAP = [
    Bin(6.21, None, 1),
    Bin(4.97, 6.21, 2),
    Bin(3.73, 4.97, 3),
    Bin(2.49, 3.73, 4),
    Bin(1.25, 2.49, 5),
    Bin(0.00, 1.25, 6),  # FS shows "– 1.25" (interpreted as 0–1.25)
]

_EO6_TOTAL_RANGES = [
    (0, 14, "Extremely Below Average"),
    (14, 17, "Well-Below Average"),
    (17, 20, "Below Average"),
    (20, 26, "Average"),
    (26, 29, "Above average"),
    (29, 32, "Well-Above Average"),
    (32, 35, "Extremely Above Average"),  # max=34
]

_EO6_MAX = 34


def score_ml_mean_eo_6y(ml_sway_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ml_sway_mean_deg, _EO6_ML_MEAN)


def score_ml_sd_eo_6y(ml_sway_sd_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ml_sway_sd_deg, _EO6_ML_SD)


def score_ap_mean_eo_6y(ap_sway_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ap_sway_mean_deg, _EO6_AP_MEAN)


def score_ap_sd_eo_6y(ap_sway_sd_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ap_sway_sd_deg, _EO6_AP_SD)


def score_step_gap_eo_6y(mean_step_gap_cm: Optional[float]) -> Optional[int]:
    return _score_from_bins(mean_step_gap_cm, _EO6_STEP_GAP)


def score_row_tandem_eo_6y(row: Dict[str, float]) -> Dict[str, Optional[object]]:
    ml_mean = score_ml_mean_eo_6y(row.get("ml_sway_mean_deg"))
    ml_sd = score_ml_sd_eo_6y(row.get("ml_sway_sd_deg"))
    ap_mean = score_ap_mean_eo_6y(row.get("ap_sway_mean_deg"))
    ap_sd = score_ap_sd_eo_6y(row.get("ap_sway_sd_deg"))
    step_gap = score_step_gap_eo_6y(row.get("mean_step_gap_cm"))

    parts = [ml_mean, ml_sd, ap_mean, ap_sd, step_gap]
    total = int(sum(p for p in parts if isinstance(p, int))) if all(isinstance(p, int) for p in parts) else None

    return {
        "ml_sway_mean_score": ml_mean,
        "ml_sway_sd_score": ml_sd,
        "ap_sway_mean_score": ap_mean,
        "ap_sway_sd_score": ap_sd,
        "step_gap_score": step_gap,
        "n_understeps_raw": row.get("n_understeps"),
        "total_score": total,
        "interpretation": _interpret_total(total, _EO6_TOTAL_RANGES),
        "max_score": _EO6_MAX,
    }


# ==========================
# EO — 7 Years (from FS)
# ==========================

_EO7_ML_MEAN = [
    Bin(6.96, None, 1),
    Bin(5.48, 6.96, 2),
    Bin(4.00, 5.48, 3),
    Bin(2.52, 4.00, 4),
    Bin(1.04, 2.52, 5),
    Bin(0.00, 1.04, 6),
]

_EO7_ML_SD = [
    Bin(4.40, None, 1),
    Bin(3.59, 4.40, 2),
    Bin(2.78, 3.59, 3),
    Bin(1.97, 2.78, 4),
    Bin(1.16, 1.97, 5),
    Bin(0.35, 1.16, 6),
    Bin(0.00, 0.35, 7),
]

_EO7_AP_MEAN = [
    Bin(4.17, None, 1),
    Bin(3.57, 4.17, 2),
    Bin(2.97, 3.57, 3),
    Bin(2.37, 2.97, 4),
    Bin(1.77, 2.37, 5),
    Bin(1.17, 1.77, 6),
    Bin(0.57, 1.17, 7),
    Bin(0.00, 0.57, 8),
]

_EO7_AP_SD = [
    Bin(3.60, None, 1),
    Bin(3.12, 3.60, 2),
    Bin(2.64, 3.12, 3),
    Bin(2.16, 2.64, 4),
    Bin(1.68, 2.16, 5),
    Bin(1.20, 1.68, 6),
    Bin(0.72, 1.20, 7),
    Bin(0.00, 0.72, 8),
]

_EO7_STEP_GAP = [
    Bin(6.59, None, 1),
    Bin(5.17, 6.59, 2),
    Bin(3.75, 5.17, 3),
    Bin(2.33, 3.75, 4),
    Bin(0.91, 2.33, 5),
    Bin(0.00, 0.91, 6),
]

_EO7_TOTAL_RANGES = [
    (0, 14, "Extremely Below Average"),
    (14, 17, "Well-Below Average"),
    (17, 20, "Below Average"),
    (20, 26, "Average"),
    (26, 29, "Above average"),
    (29, 32, "Well-Above Average"),
    (32, 36, "Extremely Above Average"),  # max=35
]

_EO7_MAX = 35


def score_ml_mean_eo_7y(ml_sway_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ml_sway_mean_deg, _EO7_ML_MEAN)


def score_ml_sd_eo_7y(ml_sway_sd_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ml_sway_sd_deg, _EO7_ML_SD)


def score_ap_mean_eo_7y(ap_sway_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ap_sway_mean_deg, _EO7_AP_MEAN)


def score_ap_sd_eo_7y(ap_sway_sd_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ap_sway_sd_deg, _EO7_AP_SD)


def score_step_gap_eo_7y(mean_step_gap_cm: Optional[float]) -> Optional[int]:
    return _score_from_bins(mean_step_gap_cm, _EO7_STEP_GAP)


def score_row_tandem_eo_7y(row: Dict[str, float]) -> Dict[str, Optional[object]]:
    ml_mean = score_ml_mean_eo_7y(row.get("ml_sway_mean_deg"))
    ml_sd = score_ml_sd_eo_7y(row.get("ml_sway_sd_deg"))
    ap_mean = score_ap_mean_eo_7y(row.get("ap_sway_mean_deg"))
    ap_sd = score_ap_sd_eo_7y(row.get("ap_sway_sd_deg"))
    step_gap = score_step_gap_eo_7y(row.get("mean_step_gap_cm"))

    parts = [ml_mean, ml_sd, ap_mean, ap_sd, step_gap]
    total = int(sum(p for p in parts if isinstance(p, int))) if all(isinstance(p, int) for p in parts) else None

    return {
        "ml_sway_mean_score": ml_mean,
        "ml_sway_sd_score": ml_sd,
        "ap_sway_mean_score": ap_mean,
        "ap_sway_sd_score": ap_sd,
        "step_gap_score": step_gap,
        "n_understeps_raw": row.get("n_understeps"),
        "total_score": total,
        "interpretation": _interpret_total(total, _EO7_TOTAL_RANGES),
        "max_score": _EO7_MAX,
    }


# Convenience dispatcher
def score_row_tandem_eo(row: Dict[str, float], age_years: int) -> Dict[str, Optional[object]]:
    """age_years must be 6 or 7."""
    if int(age_years) == 6:
        return score_row_tandem_eo_6y(row)
    if int(age_years) == 7:
        return score_row_tandem_eo_7y(row)
    raise ValueError("age_years must be 6 or 7 for Tandem Walking EO")
