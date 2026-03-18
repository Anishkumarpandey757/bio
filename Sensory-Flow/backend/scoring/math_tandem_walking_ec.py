"""Tandem Walking — Eyes Closed (EC) scoring (6y & 7y)

Implements deterministic scoring based on the Form Sheet (FS) ranges.

Expected inputs (from your CV/preprocess pipeline), per clip:
- ml_sway_mean_deg   (Mediolateral sway mean; front view)
- ml_sway_sd_deg     (Mediolateral sway variability/SD; front view)
- ap_sway_mean_deg   (Anteroposterior sway mean; side/profile view)
- ap_sway_sd_deg     (Anteroposterior sway variability/SD; side/profile view)
- mean_step_gap_cm   (Mean step gap in cm; profile)
- n_understeps       (Number of understeps; raw display only; not scored)

Doc sources used:
- Tandem Walking EC FS (6 Years).docx
- Tandem Walking EC FS (7 Years).docx
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
# EC — 6 Years (from FS)
# ==========================

_EC6_ML_MEAN = [
    Bin(7.53, None, 1),
    Bin(5.96, 7.53, 2),
    Bin(4.39, 5.96, 3),
    Bin(2.82, 4.39, 4),
    Bin(1.25, 2.82, 5),
    Bin(0.00, 1.25, 6),
]

_EC6_ML_SD = [
    Bin(4.33, None, 1),
    Bin(3.63, 4.33, 2),
    Bin(2.93, 3.63, 3),
    Bin(2.23, 2.93, 4),
    Bin(1.53, 2.23, 5),
    Bin(0.83, 1.53, 6),
    Bin(0.13, 0.83, 7),
    Bin(0.00, 0.13, 8),
]

_EC6_AP_MEAN = [
    Bin(4.15, None, 1),
    Bin(3.54, 4.15, 2),
    Bin(2.93, 3.54, 3),
    Bin(2.32, 2.93, 4),
    Bin(1.71, 2.32, 5),
    Bin(1.10, 1.71, 6),
    Bin(0.49, 1.10, 7),
    Bin(0.00, 0.49, 8),
]

_EC6_AP_SD = [
    Bin(4.19, None, 1),
    Bin(3.54, 4.19, 2),
    Bin(2.89, 3.54, 3),
    Bin(2.24, 2.89, 4),
    Bin(1.59, 2.24, 5),
    Bin(0.94, 1.59, 6),
    Bin(0.29, 0.94, 7),
    Bin(0.00, 0.29, 8),
]

_EC6_STEP_GAP = [
    Bin(5.52, None, 1),
    Bin(4.57, 5.52, 2),
    Bin(3.62, 4.57, 3),
    Bin(2.67, 3.62, 4),
    Bin(1.72, 2.67, 5),
    Bin(0.77, 1.72, 6),
    Bin(0.00, 0.77, 7),
]

_EC6_TOTAL_RANGES = [
    (0, 13, "Extremely Below Average"),
    (13, 16, "Well-Below Average"),
    (16, 19, "Below Average"),
    (19, 25, "Average"),
    (25, 28, "Above average"),
    (28, 31, "Well-Above Average"),
    (31, 38, "Extremely Above Average"),  # max=37
]

_EC6_MAX = 37


def score_ml_mean_ec_6y(ml_sway_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ml_sway_mean_deg, _EC6_ML_MEAN)


def score_ml_sd_ec_6y(ml_sway_sd_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ml_sway_sd_deg, _EC6_ML_SD)


def score_ap_mean_ec_6y(ap_sway_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ap_sway_mean_deg, _EC6_AP_MEAN)


def score_ap_sd_ec_6y(ap_sway_sd_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ap_sway_sd_deg, _EC6_AP_SD)


def score_step_gap_ec_6y(mean_step_gap_cm: Optional[float]) -> Optional[int]:
    return _score_from_bins(mean_step_gap_cm, _EC6_STEP_GAP)


def score_row_tandem_ec_6y(row: Dict[str, float]) -> Dict[str, Optional[object]]:
    ml_mean = score_ml_mean_ec_6y(row.get("ml_sway_mean_deg"))
    ml_sd = score_ml_sd_ec_6y(row.get("ml_sway_sd_deg"))
    ap_mean = score_ap_mean_ec_6y(row.get("ap_sway_mean_deg"))
    ap_sd = score_ap_sd_ec_6y(row.get("ap_sway_sd_deg"))
    step_gap = score_step_gap_ec_6y(row.get("mean_step_gap_cm"))

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
        "interpretation": _interpret_total(total, _EC6_TOTAL_RANGES),
        "max_score": _EC6_MAX,
    }


# ==========================
# EC — 7 Years (from FS)
# ==========================

_EC7_ML_MEAN = [
    Bin(7.43, None, 1),
    Bin(5.77, 7.43, 2),
    Bin(4.11, 5.77, 3),
    Bin(2.45, 4.11, 4),
    Bin(0.79, 2.45, 5),
    Bin(0.00, 0.79, 6),
]

# NOTE: FS for EC 7y ML SD lists only 6 point-scores (no <0 range bin).
_EC7_ML_SD = [
    Bin(6.07, None, 1),
    Bin(4.74, 6.07, 2),
    Bin(3.41, 4.74, 3),
    Bin(2.08, 3.41, 4),
    Bin(0.75, 2.08, 5),
    Bin(0.00, 0.75, 6),
]

_EC7_AP_MEAN = [
    Bin(4.60, None, 1),
    Bin(3.88, 4.60, 2),
    Bin(3.16, 3.88, 3),
    Bin(2.44, 3.16, 4),
    Bin(1.72, 2.44, 5),
    Bin(1.00, 1.72, 6),
    Bin(0.28, 1.00, 7),
    Bin(0.00, 0.28, 8),
]

_EC7_AP_SD = [
    Bin(3.71, None, 1),
    Bin(3.20, 3.71, 2),
    Bin(2.69, 3.20, 3),
    Bin(2.18, 2.69, 4),
    Bin(1.67, 2.18, 5),
    Bin(1.16, 1.67, 6),
    Bin(0.65, 1.16, 7),
    Bin(0.00, 0.65, 8),
]

_EC7_STEP_GAP = [
    Bin(5.87, None, 1),
    Bin(4.64, 5.87, 2),
    Bin(3.41, 4.64, 3),
    Bin(2.18, 3.41, 4),
    Bin(0.95, 2.18, 5),
    Bin(0.00, 0.95, 6),
]

_EC7_TOTAL_RANGES = [
    (0, 13, "Extremely Below Average"),
    (13, 16, "Well-Below Average"),
    (16, 19, "Below Average"),
    (19, 25, "Average"),
    (25, 28, "Above average"),
    (28, 31, "Well-Above Average"),
    (31, 35, "Extremely Above Average"),  # max=34
]

_EC7_MAX = 34


def score_ml_mean_ec_7y(ml_sway_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ml_sway_mean_deg, _EC7_ML_MEAN)


def score_ml_sd_ec_7y(ml_sway_sd_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ml_sway_sd_deg, _EC7_ML_SD)


def score_ap_mean_ec_7y(ap_sway_mean_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ap_sway_mean_deg, _EC7_AP_MEAN)


def score_ap_sd_ec_7y(ap_sway_sd_deg: Optional[float]) -> Optional[int]:
    return _score_from_bins(ap_sway_sd_deg, _EC7_AP_SD)


def score_step_gap_ec_7y(mean_step_gap_cm: Optional[float]) -> Optional[int]:
    return _score_from_bins(mean_step_gap_cm, _EC7_STEP_GAP)


def score_row_tandem_ec_7y(row: Dict[str, float]) -> Dict[str, Optional[object]]:
    ml_mean = score_ml_mean_ec_7y(row.get("ml_sway_mean_deg"))
    ml_sd = score_ml_sd_ec_7y(row.get("ml_sway_sd_deg"))
    ap_mean = score_ap_mean_ec_7y(row.get("ap_sway_mean_deg"))
    ap_sd = score_ap_sd_ec_7y(row.get("ap_sway_sd_deg"))
    step_gap = score_step_gap_ec_7y(row.get("mean_step_gap_cm"))

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
        "interpretation": _interpret_total(total, _EC7_TOTAL_RANGES),
        "max_score": _EC7_MAX,
    }


# Convenience dispatcher
def score_row_tandem_ec(row: Dict[str, float], age_years: int) -> Dict[str, Optional[object]]:
    """age_years must be 6 or 7."""
    if int(age_years) == 6:
        return score_row_tandem_ec_6y(row)
    if int(age_years) == 7:
        return score_row_tandem_ec_7y(row)
    raise ValueError("age_years must be 6 or 7 for Tandem Walking EC")
