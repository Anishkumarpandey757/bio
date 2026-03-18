import math

def _clamp_nonneg(x):
    if x is None:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    return max(float(x), 0.0)

# ============================================================
# OLS LL EYES CLOSED (EC) — 6 YEARS
# Source: "One Leg Standing (LL EC) FS (6 Years).docx"
# ============================================================

def score_sway_ss_mean_6y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 12.31: return 1
    if 10.42 <= x < 12.31: return 2
    if 8.53  <= x < 10.42: return 3
    if 6.64  <= x <  8.53: return 4
    if 4.75  <= x <  6.64: return 5
    if 2.86  <= x <  4.75: return 6
    if 0.97  <= x <  2.86: return 7
    # Below 0.97
    if 0.00  <= x <  0.97: return 8
    return 8

def score_sway_ss_sd_6y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 8.73: return 1
    if 7.12 <= x < 8.73: return 2
    if 5.51 <= x < 7.12: return 3
    if 3.90 <= x < 5.51: return 4
    if 2.29 <= x < 3.90: return 5
    if 0.68 <= x < 2.29: return 6
    # Below 0.68
    if 0.00 <= x < 0.68: return 7
    return 7

def score_sway_ap_mean_6y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 9.98: return 1
    if 7.94 <= x < 9.98: return 2
    if 5.90 <= x < 7.94: return 3
    if 3.86 <= x < 5.90: return 4
    if 1.82 <= x < 3.86: return 5
    # Below 1.82
    if 0.00 <= x < 1.82: return 6
    return 6

def score_sway_ap_sd_6y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 6.92: return 1
    if 5.54 <= x < 6.92: return 2
    if 4.16 <= x < 5.54: return 3
    if 2.78 <= x < 4.16: return 4
    if 1.40 <= x < 2.78: return 5
    if 0.00 <= x < 1.40: return 6
    return 6

def score_toe_touches_6y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 22: return 1
    if 18 <= x < 22: return 2
    if 14 <= x < 18: return 3
    if 10 <= x < 14: return 4
    if 6  <= x < 10: return 5
    if 2  <= x <  6: return 6
    if 0  <= x <  2: return 7
    return 7

def interpret_total_6y_ec(total):
    if total is None:
        return None
    total = float(total)
    if 0  <= total < 10: return "Extremely Below Average"
    if 10 <= total < 14: return "Well-Below Average"
    if 14 <= total < 18: return "Below Average"
    if 18 <= total < 26: return "Average"
    if 26 <= total < 30: return "Above average"
    if 30 <= total <= 34: return "Well-Above Average"
    return "Out of range"

def score_row_6y_ec(row: dict, use_toe_touch=True):
    ss_mean = row.get("sway_SS_mean")
    ss_sd   = row.get("sway_SS_SD")
    ap_mean = row.get("sway_AP_mean")
    ap_sd   = row.get("sway_AP_SD")
    toe     = row.get("toe_touches")

    out = {}
    out["sway_SS_mean_score"] = score_sway_ss_mean_6y_ec(ss_mean)
    out["sway_SS_SD_score"]   = score_sway_ss_sd_6y_ec(ss_sd)
    out["sway_AP_mean_score"] = score_sway_ap_mean_6y_ec(ap_mean)
    out["sway_AP_SD_score"]   = score_sway_ap_sd_6y_ec(ap_sd)

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
        out["toe_touches_score"] = score_toe_touches_6y_ec(toe)
        if out["toe_touches_score"] is None:
            out["total_score"] = None
            out["interpretation"] = None
            return out
        total5 = total4 + out["toe_touches_score"]
        out["total_score"] = total5
        out["interpretation"] = interpret_total_6y_ec(total5)
    else:
        out["total_score"] = total4
        out["interpretation"] = f"4-parameter total (EC 6y): {total4}"

    return out


# ============================================================
# OLS LL EYES CLOSED (EC) — 7 YEARS
# Source: "One Leg Standing (LL EC) FS (7 Years).docx"
# ============================================================

def score_sway_ss_mean_7y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 10.32: return 1
    if 8.50 <= x < 10.32: return 2
    if 6.68 <= x <  8.50: return 3
    if 4.86 <= x <  6.68: return 4
    if 3.04 <= x <  4.86: return 5
    if 1.22 <= x <  3.04: return 6
    if 0.00 <= x <  1.22: return 7
    return 7

def score_sway_ss_sd_7y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 5.34: return 1
    if 4.45 <= x < 5.34: return 2
    if 3.56 <= x < 4.45: return 3
    if 2.67 <= x < 3.56: return 4
    if 1.78 <= x < 2.67: return 5
    if 0.89 <= x < 1.78: return 6
    if 0.00 <= x < 0.89: return 7
    return 7

def score_sway_ap_mean_7y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 9.15: return 1
    if 7.34 <= x < 9.15: return 2
    if 5.53 <= x < 7.34: return 3
    if 3.72 <= x < 5.53: return 4
    if 1.91 <= x < 3.72: return 5
    if 0.10 <= x < 1.91: return 6
    if 0.00 <= x < 0.10: return 7
    return 7

def score_sway_ap_sd_7y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 5.55: return 1
    if 4.49 <= x < 5.55: return 2
    if 3.43 <= x < 4.49: return 3
    if 2.37 <= x < 3.43: return 4
    if 1.31 <= x < 2.37: return 5
    if 0.25 <= x < 1.31: return 6
    if 0.00 <= x < 0.25: return 7
    return 7

def score_toe_touches_7y_ec(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 20: return 1
    if 16 <= x < 20: return 2
    if 12 <= x < 16: return 3
    if 8  <= x < 12: return 4
    if 4  <= x <  8: return 5
    if 0  <= x <  4: return 6
    return 6

def interpret_total_7y_ec(total):
    if total is None:
        return None
    total = float(total)
    if 0  <= total < 13: return "Extremely Below Average"
    if 13 <= total < 16: return "Well-Below Average"
    if 16 <= total < 19: return "Below Average"
    if 19 <= total < 25: return "Average"
    if 25 <= total < 28: return "Above average"
    if 28 <= total < 31: return "Well-Above Average"
    if 31 <= total <= 34: return "Extremely Above Average"
    return "Out of range"

def score_row_7y_ec(row: dict, use_toe_touch=True):
    ss_mean = row.get("sway_SS_mean")
    ss_sd   = row.get("sway_SS_SD")
    ap_mean = row.get("sway_AP_mean")
    ap_sd   = row.get("sway_AP_SD")
    toe     = row.get("toe_touches")

    out = {}
    out["sway_SS_mean_score"] = score_sway_ss_mean_7y_ec(ss_mean)
    out["sway_SS_SD_score"]   = score_sway_ss_sd_7y_ec(ss_sd)
    out["sway_AP_mean_score"] = score_sway_ap_mean_7y_ec(ap_mean)
    out["sway_AP_SD_score"]   = score_sway_ap_sd_7y_ec(ap_sd)

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
        out["toe_touches_score"] = score_toe_touches_7y_ec(toe)
        if out["toe_touches_score"] is None:
            out["total_score"] = None
            out["interpretation"] = None
            return out
        total5 = total4 + out["toe_touches_score"]
        out["total_score"] = total5
        out["interpretation"] = interpret_total_7y_ec(total5)
    else:
        out["total_score"] = total4
        out["interpretation"] = f"4-parameter total (EC 7y): {total4}"

    return out


# ============================================================
# Convenience wrapper (optional)
# ============================================================

def score_row_ec(row: dict, age_tag: str = "7yrs", use_toe_touch: bool = True):
    """
    age_tag: "6yrs" or "7yrs"
    """
    if age_tag.lower().startswith("6"):
        return score_row_6y_ec(row, use_toe_touch=use_toe_touch)
    return score_row_7y_ec(row, use_toe_touch=use_toe_touch)
