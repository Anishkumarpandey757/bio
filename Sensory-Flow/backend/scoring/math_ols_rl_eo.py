# ols_rl_eo_math.py - Right Leg, Eyes Open OLS Scoring
import math

def _clamp_nonneg(x):
    if x is None:
        return None
    try:
        x = float(x)
    except Exception:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    return max(x, 0.0)

# ============================================================
# Right Leg (RL) — Eyes Open (EO) — 6 YEARS
# Source: One Leg Standing (RL EO) FS (6 Years).docx
# ============================================================

def score_sway_ss_mean_6y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 11.56: return 1
    if 9.39 <= x < 11.56: return 2
    if 7.22 <= x <  9.39: return 3
    if 5.05 <= x <  7.22: return 4
    if 2.88 <= x <  5.05: return 5
    if 0.71 <= x <  2.88: return 6
    if 0.00 <= x <  0.71: return 7
    return 7

def score_sway_ss_sd_6y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 6.11: return 1
    if 4.87 <= x < 6.11: return 2
    if 3.63 <= x < 4.87: return 3
    if 2.39 <= x < 3.63: return 4
    if 1.15 <= x < 2.39: return 5
    if 0.00 <= x < 1.15: return 6
    return 6

def score_sway_ap_mean_6y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 14.02: return 1
    if 10.60 <= x < 14.02: return 2
    if 7.18  <= x < 10.60: return 3
    if 3.76  <= x <  7.18: return 4
    if 0.34  <= x <  3.76: return 5
    if 0.00  <= x <  0.34: return 6
    return 6

def score_sway_ap_sd_6y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 7.09: return 1
    if 5.46 <= x < 7.09: return 2
    if 3.83 <= x < 5.46: return 3
    if 2.20 <= x < 3.83: return 4
    if 0.57 <= x < 2.20: return 5
    if 0.00 <= x < 0.57: return 6
    return 6

def score_toe_touches_6y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 18: return 1
    if 14 <= x < 18: return 2
    if 10 <= x < 14: return 3
    if 6  <= x < 10: return 4
    if 2  <= x <  6: return 5
    if 0  <= x <  2: return 6
    return 6

def interpret_total_6y_rl_eo(total):
    if total is None:
        return None
    total = float(total)
    if 0  <= total < 10: return "Extremely Below Average"
    if 10 <= total < 14: return "Well-Below Average"
    if 14 <= total < 18: return "Below Average"
    if 18 <= total < 26: return "Average"
    if 26 <= total < 30: return "Above average"
    if 30 <= total <= 31: return "Well-Above Average"
    return "Out of range"

def score_row_6y_rl_eo(row: dict, use_toe_touch=True):
    ss_mean = row.get("sway_SS_mean")
    ss_sd   = row.get("sway_SS_SD")
    ap_mean = row.get("sway_AP_mean")
    ap_sd   = row.get("sway_AP_SD")
    toe     = row.get("toe_touches")

    out = {}
    out["sway_SS_mean_score"] = score_sway_ss_mean_6y_rl_eo(ss_mean)
    out["sway_SS_SD_score"]   = score_sway_ss_sd_6y_rl_eo(ss_sd)
    out["sway_AP_mean_score"] = score_sway_ap_mean_6y_rl_eo(ap_mean)
    out["sway_AP_SD_score"]   = score_sway_ap_sd_6y_rl_eo(ap_sd)

    base = [
        out["sway_SS_mean_score"],
        out["sway_SS_SD_score"],
        out["sway_AP_mean_score"],
        out["sway_AP_SD_score"],
    ]
    if any(v is None for v in base):
        out["total_score"] = None
        out["interpretation"] = None
        return out

    total4 = sum(base)
    out["total_score_4params"] = total4

    if use_toe_touch:
        out["toe_touches_score"] = score_toe_touches_6y_rl_eo(toe)
        if out["toe_touches_score"] is None:
            out["total_score"] = None
            out["interpretation"] = None
            return out
        total5 = total4 + out["toe_touches_score"]
        out["total_score"] = total5
        out["interpretation"] = interpret_total_6y_rl_eo(total5)
    else:
        out["total_score"] = total4
        out["interpretation"] = f"4-parameter total (RL EO 6y): {total4}"

    out["max_score"] = 31  # 7+6+6+6+6 for 6y
    return out


# ============================================================
# Right Leg (RL) — Eyes Open (EO) — 7 YEARS
# Source: One Leg Standing (RL EO) FS (7 Years).docx
# Original form: 5 bands per param (scores 1–5), total max 25.
# ============================================================

def score_sway_ss_mean_7y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 10.24: return 1
    if 8.21 <= x < 10.24: return 2
    if 6.18 <= x <  8.21: return 3
    if 4.15 <= x <  6.18: return 4
    if 0.00 <= x <  4.15: return 5
    return 5

def score_sway_ss_sd_7y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 4.43: return 1
    if 3.56 <= x < 4.43: return 2
    if 2.69 <= x < 3.56: return 3
    if 1.82 <= x < 2.69: return 4
    if 0.00 <= x < 1.82: return 5
    return 5

def score_sway_ap_mean_7y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 9.02: return 1
    if 7.01 <= x < 9.02: return 2
    if 5.00 <= x < 7.01: return 3
    if 2.99 <= x < 5.00: return 4
    if 0.00 <= x < 2.99: return 5
    return 5

def score_sway_ap_sd_7y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 4.62: return 1
    if 3.63 <= x < 4.62: return 2
    if 2.64 <= x < 3.63: return 3
    if 1.65 <= x < 2.64: return 4
    if 0.00 <= x < 1.65: return 5
    return 5

def score_toe_touches_7y_rl_eo(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 8: return 1
    if 6 <= x < 8: return 2
    if 4 <= x < 6: return 3
    if 2 <= x < 4: return 4
    if 0 <= x < 2: return 5
    return 5

def interpret_total_7y_rl_eo(total):
    if total is None:
        return None
    total = float(total)
    # Total max = 25 (5 params × max 5)
    if 0  <= total < 8:  return "Extremely Below Average"
    if 8  <= total < 11: return "Well-Below Average"
    if 11 <= total < 14: return "Below Average"
    if 14 <= total < 20: return "Average"
    if 20 <= total < 24: return "Above average"
    if 24 <= total <= 25: return "Well-Above Average"
    return "Out of range"

def score_row_7y_rl_eo(row: dict, use_toe_touch=True):
    ss_mean = row.get("sway_SS_mean")
    ss_sd   = row.get("sway_SS_SD")
    ap_mean = row.get("sway_AP_mean")
    ap_sd   = row.get("sway_AP_SD")
    toe     = row.get("toe_touches")

    out = {}
    out["sway_SS_mean_score"] = score_sway_ss_mean_7y_rl_eo(ss_mean)
    out["sway_SS_SD_score"]   = score_sway_ss_sd_7y_rl_eo(ss_sd)
    out["sway_AP_mean_score"] = score_sway_ap_mean_7y_rl_eo(ap_mean)
    out["sway_AP_SD_score"]   = score_sway_ap_sd_7y_rl_eo(ap_sd)

    base = [
        out["sway_SS_mean_score"],
        out["sway_SS_SD_score"],
        out["sway_AP_mean_score"],
        out["sway_AP_SD_score"],
    ]
    if any(v is None for v in base):
        out["total_score"] = None
        out["interpretation"] = None
        return out

    total4 = sum(base)
    out["total_score_4params"] = total4

    if use_toe_touch:
        out["toe_touches_score"] = score_toe_touches_7y_rl_eo(toe)
        if out["toe_touches_score"] is None:
            out["total_score"] = None
            out["interpretation"] = None
            return out
        total5 = total4 + out["toe_touches_score"]
        out["total_score"] = total5
        out["interpretation"] = interpret_total_7y_rl_eo(total5)
    else:
        out["total_score"] = total4
        out["interpretation"] = f"4-parameter total (RL EO 7y): {total4}"

    out["max_score"] = 25
    return out


# ============================================================
# Convenience wrapper
# ============================================================

def score_row_rl_eo(row: dict, age_years: int = 7, use_toe_touch: bool = True):
    """
    age_years: 6 or 7
    row keys expected:
      sway_SS_mean, sway_SS_SD, sway_AP_mean, sway_AP_SD, toe_touches
    """
    if age_years == 6:
        return score_row_6y_rl_eo(row, use_toe_touch=use_toe_touch)
    return score_row_7y_rl_eo(row, use_toe_touch=use_toe_touch)
