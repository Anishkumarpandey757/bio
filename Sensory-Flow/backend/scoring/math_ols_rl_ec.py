# ols_rl_ec_math.py - Right Leg, Eyes Closed OLS Scoring
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
# Right Leg (RL) — Eyes Closed (EC) — 6 YEARS
# Source: One leg standing - Right Leg Eyes Closed (6 Years)
# ============================================================

def score_sway_ss_mean_6y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 11.89: return 1
    if 9.75 <= x < 11.89: return 2
    if 7.61 <= x <  9.75: return 3
    if 5.47 <= x <  7.61: return 4
    if 3.33 <= x <  5.47: return 5
    if 1.19 <= x <  3.33: return 6
    if 0.00 <= x <  1.19: return 7
    return 7

def score_sway_ss_sd_6y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 7.31: return 1
    if 6.07 <= x < 7.31: return 2
    if 4.83 <= x < 6.07: return 3
    if 3.59 <= x < 4.83: return 4
    if 2.35 <= x < 3.59: return 5
    if 1.11 <= x < 2.35: return 6
    if 0.00 <= x < 1.11: return 7
    return 7

def score_sway_ap_mean_6y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 10.95: return 1
    if 8.65 <= x < 10.95: return 2
    if 6.35 <= x <  8.65: return 3
    if 4.05 <= x <  6.35: return 4
    if 1.75 <= x <  4.05: return 5
    if 0.00 <= x <  1.75: return 6
    return 6

def score_sway_ap_sd_6y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 6.82: return 1
    if 5.49 <= x < 6.82: return 2
    if 4.16 <= x < 5.49: return 3
    if 2.83 <= x < 4.16: return 4
    if 1.50 <= x < 2.83: return 5
    if 0.17 <= x < 1.50: return 6
    if 0.00 <= x < 0.17: return 7
    return 7

def score_toe_touches_6y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 19: return 1
    if 16 <= x < 19: return 2
    if 13 <= x < 16: return 3
    if 10 <= x < 13: return 4
    if 7  <= x < 10: return 5
    if 4  <= x <  7: return 6
    if 1  <= x <  4: return 7
    if 0  <= x <  1: return 8
    return 8

def interpret_total_6y_rl_ec(total):
    if total is None:
        return None
    total = float(total)
    if 0  <= total < 10: return "Extremely Below Average"
    if 10 <= total < 14: return "Well-Below Average"
    if 14 <= total < 18: return "Below Average"
    if 18 <= total < 26: return "Average"
    if 26 <= total < 30: return "Above average"
    if 30 <= total < 34: return "Well-Above Average"
    if 34 <= total <= 35: return "Extremely Above Average"
    return "Out of range"

def score_row_6y_rl_ec(row: dict, use_toe_touch=True):
    ss_mean = row.get("sway_SS_mean")
    ss_sd   = row.get("sway_SS_SD")
    ap_mean = row.get("sway_AP_mean")
    ap_sd   = row.get("sway_AP_SD")
    toe     = row.get("toe_touches")

    out = {}
    out["sway_SS_mean_score"] = score_sway_ss_mean_6y_rl_ec(ss_mean)
    out["sway_SS_SD_score"]   = score_sway_ss_sd_6y_rl_ec(ss_sd)
    out["sway_AP_mean_score"] = score_sway_ap_mean_6y_rl_ec(ap_mean)
    out["sway_AP_SD_score"]   = score_sway_ap_sd_6y_rl_ec(ap_sd)

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
        out["toe_touches_score"] = score_toe_touches_6y_rl_ec(toe)
        if out["toe_touches_score"] is None:
            out["total_score"] = None
            out["interpretation"] = None
            return out
        total5 = total4 + out["toe_touches_score"]
        out["total_score"] = total5
        out["interpretation"] = interpret_total_6y_rl_ec(total5)
    else:
        out["total_score"] = total4
        out["interpretation"] = f"4-parameter total (RL EC 6y): {total4}"

    return out


# ============================================================
# Right Leg (RL) — Eyes Closed (EC) — 7 YEARS
# Source: One leg standing - Right Leg Eyes Closed (7 Years)
# ============================================================

def score_sway_ss_mean_7y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 9.19: return 1
    if 7.55 <= x < 9.19: return 2
    if 5.91 <= x < 7.55: return 3
    if 4.27 <= x < 5.91: return 4
    if 2.63 <= x < 4.27: return 5
    if 0.99 <= x < 2.63: return 6
    if 0.00 <= x < 0.99: return 7
    return 7

def score_sway_ss_sd_7y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 5.57: return 1
    if 4.59 <= x < 5.57: return 2
    if 3.61 <= x < 4.59: return 3
    if 2.63 <= x < 3.61: return 4
    if 1.65 <= x < 2.63: return 5
    if 0.67 <= x < 1.65: return 6
    if 0.00 <= x < 0.67: return 7
    return 7

def score_sway_ap_mean_7y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 8.48: return 1
    if 6.74 <= x < 8.48: return 2
    if 5.00 <= x < 6.74: return 3
    if 3.26 <= x < 5.00: return 4
    if 1.52 <= x < 3.26: return 5
    if 0.00 <= x < 1.52: return 6
    return 6

def score_sway_ap_sd_7y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 4.81: return 1
    if 3.94 <= x < 4.81: return 2
    if 3.07 <= x < 3.94: return 3
    if 2.20 <= x < 3.07: return 4
    if 1.33 <= x < 2.20: return 5
    if 0.46 <= x < 1.33: return 6
    if 0.00 <= x < 0.46: return 7
    return 7

def score_toe_touches_7y_rl_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 22: return 1
    if 17 <= x < 22: return 2
    if 12 <= x < 17: return 3
    if 7  <= x < 12: return 4
    if 2  <= x <  7: return 5
    if 0  <= x <  2: return 6
    return 6

def interpret_total_7y_rl_ec(total):
    if total is None:
        return None
    total = float(total)
    if 0  <= total < 13: return "Extremely Below Average"
    if 13 <= total < 16: return "Well-Below Average"
    if 16 <= total < 19: return "Below Average"
    if 19 <= total < 25: return "Average"
    if 25 <= total < 28: return "Above average"
    if 28 <= total < 31: return "Well-Above Average"
    if 31 <= total <= 33: return "Extremely Above Average"
    return "Out of range"

def score_row_7y_rl_ec(row: dict, use_toe_touch=True):
    ss_mean = row.get("sway_SS_mean")
    ss_sd   = row.get("sway_SS_SD")
    ap_mean = row.get("sway_AP_mean")
    ap_sd   = row.get("sway_AP_SD")
    toe     = row.get("toe_touches")

    out = {}
    out["sway_SS_mean_score"] = score_sway_ss_mean_7y_rl_ec(ss_mean)
    out["sway_SS_SD_score"]   = score_sway_ss_sd_7y_rl_ec(ss_sd)
    out["sway_AP_mean_score"] = score_sway_ap_mean_7y_rl_ec(ap_mean)
    out["sway_AP_SD_score"]   = score_sway_ap_sd_7y_rl_ec(ap_sd)

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
        out["toe_touches_score"] = score_toe_touches_7y_rl_ec(toe)
        if out["toe_touches_score"] is None:
            out["total_score"] = None
            out["interpretation"] = None
            return out
        total5 = total4 + out["toe_touches_score"]
        out["total_score"] = total5
        out["interpretation"] = interpret_total_7y_rl_ec(total5)
    else:
        out["total_score"] = total4
        out["interpretation"] = f"4-parameter total (RL EC 7y): {total4}"

    return out


# ============================================================
# Convenience wrapper
# ============================================================

def score_row_rl_ec(row: dict, age_years: int = 7, use_toe_touch: bool = True):
    """
    age_years: 6 or 7
    row keys expected:
      sway_SS_mean, sway_SS_SD, sway_AP_mean, sway_AP_SD, toe_touches
    """
    if age_years == 6:
        return score_row_6y_rl_ec(row, use_toe_touch=use_toe_touch)
    return score_row_7y_rl_ec(row, use_toe_touch=use_toe_touch)
