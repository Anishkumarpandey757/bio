"""
math_total_assessment.py

Assessment-level scoring aggregator.

This file DOES NOT re-score per-exercise kinematics; it only:
1) Consumes already-scored exercise outputs (per-exercise total_score),
2) Sums them to produce Total Assessment Score,
3) Computes z-score using age-specific Mean/SD from your "Total Score of the Assessment" sheet,
4) Provides a simple interpretation band.

Age norms (from your document):
- 7 Years: Mean = 197, SD = 15
- 6 Years: Mean = 197, SD = 17

Expected input:
A dict like:
{
  "prone_extension": {"total_score": 33, ...},
  "supine_flexion": {"total_score": 31, ...},
  "ols_ll_ec": {"total_score": 30, ...},
  "ols_ll_eo": {"total_score": 28, ...},
  "ols_rl_ec": {"total_score": 31, ...},
  "ols_rl_eo": {"total_score": 27, ...},
  "tandem_ec": {"total_score": 29, ...},
  "tandem_eo": {"total_score": 30, ...},
  "jumping_jacks": {"total_score": 32, ...},
}

If a key is missing or the exercise total_score is None, it will be skipped (and flagged).

Interpretation bands (z-score based):
- z <= -2.0  -> "Extremely Below Average"
- -2 < z <= -1.0 -> "Below Average"
- -1 < z < 1.0 -> "Average"
- 1.0 <= z < 2.0 -> "Above Average"
- z >= 2.0 -> "Extremely Above Average"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class AgeNorm:
    mean: float
    sd: float


NORMS = {
    6: AgeNorm(mean=197.0, sd=17.0),
    7: AgeNorm(mean=197.0, sd=15.0),
}

# Canonical exercise keys (you can rename in your app, but keep consistent here)
EXERCISE_KEYS = (
    "prone_extension",
    "supine_flexion",
    "ols_ll_ec",
    "ols_ll_eo",
    "ols_rl_ec",
    "ols_rl_eo",
    "tandem_ec",
    "tandem_eo",
    "jumping_jacks",
)


def _to_number(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
    except Exception:
        return None
    if v != v:  # NaN
        return None
    return v


def z_score(total: Optional[float], age_years: int) -> Optional[float]:
    total = _to_number(total)
    if total is None:
        return None
    norm = NORMS.get(int(age_years))
    if norm is None or norm.sd <= 0:
        return None
    return (total - norm.mean) / norm.sd


def interpret_z(z: Optional[float]) -> Optional[str]:
    z = _to_number(z)
    if z is None:
        return None
    if z <= -2.0:
        return "Extremely Below Average"
    if z <= -1.0:
        return "Below Average"
    if z < 1.0:
        return "Average"
    if z < 2.0:
        return "Above Average"
    return "Extremely Above Average"


def total_assessment_score(exercise_scores: Dict[str, Dict[str, Any]]) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    Returns:
      total_score (float or None),
      breakdown dict: {key: used_total or None, "missing": [...], "skipped": [...]}
    """
    breakdown: Dict[str, Any] = {}
    missing = []
    skipped = []
    total = 0.0
    used_any = False

    for k in EXERCISE_KEYS:
        if k not in exercise_scores:
            missing.append(k)
            breakdown[k] = None
            continue
        ex = exercise_scores.get(k) or {}
        t = _to_number(ex.get("total_score"))
        if t is None:
            skipped.append(k)
            breakdown[k] = None
            continue
        breakdown[k] = t
        total += t
        used_any = True

    breakdown["missing"] = missing
    breakdown["skipped"] = skipped

    return (total if used_any else None), breakdown


def score_assessment(exercise_scores: Dict[str, Dict[str, Any]], age_years: int) -> Dict[str, Any]:
    """
    Main entrypoint.
    """
    total, breakdown = total_assessment_score(exercise_scores)
    z = z_score(total, age_years=age_years)
    interp = interpret_z(z)

    norm = NORMS.get(int(age_years))
    return {
        "age_years": int(age_years),
        "total_score": total,
        "mean": norm.mean if norm else None,
        "sd": norm.sd if norm else None,
        "z_score": z,
        "interpretation": interp,
        "breakdown": breakdown,
    }
