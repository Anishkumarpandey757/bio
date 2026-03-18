import math

def _clamp_nonneg(x):
    if x is None: 
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    return max(float(x), 0.0)

# ---------- 7 YEARS RUBRIC (from your doc) ----------
# SS mean (Front)
def score_sway_ss_mean_7y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x > 10.47: return 1
    if 8.41 <= x <= 10.47: return 2
    if 6.36 <= x <  8.41: return 3
    if 4.31 <= x <  6.36: return 4
    if 2.25 <= x <  4.31: return 5
    if 0.20 <= x <  2.25: return 6
    if 0.00 <= x <  0.20: return 7
    return 7  # fallback

# SS SD (Front)
def score_sway_ss_sd_7y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x > 5.49: return 1
    if 4.35 <= x <= 5.49: return 2
    if 3.21 <= x <  4.35: return 3
    if 2.08 <= x <  3.21: return 4
    if 0.94 <= x <  2.08: return 5
    # doc shows "– 0.94" meaning below 0.94
    if 0.00 <= x <  0.94: return 6
    return 6

# AP mean (Side)
def score_sway_ap_mean_7y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x > 8.98: return 1
    if 7.07 <= x <= 8.98: return 2
    if 5.17 <= x <  7.07: return 3
    if 3.26 <= x <  5.17: return 4
    if 1.35 <= x <  3.26: return 5
    if 0.00 <= x <  1.35: return 6
    return 6

# AP SD (Side)
def score_sway_ap_sd_7y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x > 5.02: return 1
    if 3.98 <= x <= 5.02: return 2
    if 2.94 <= x <  3.98: return 3
    if 1.89 <= x <  2.94: return 4
    if 0.85 <= x <  1.89: return 5
    if 0.00 <= x <  0.85: return 6
    return 6

# Toe touches (Side)
def score_toe_touches_7y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    if x >= 12: return 1
    if 9 <= x < 12: return 2
    if 6 <= x <  9: return 3
    if 3 <= x <  6: return 4
    if 0 <= x <  3: return 5
    return 5

def interpret_total_7y(total):
    if total is None: 
        return None
    total = float(total)
    if total < 13: return "Extremely Below Average"
    if 13 <= total < 16: return "Well-Below Average"
    if 16 <= total < 19: return "Below Average"
    if 19 <= total <= 25: return "Average"
    if 25 < total <= 28: return "Above Average"
    if 28 < total <= 30: return "Well-Above Average"
    return "Out of range"

def score_row_7y(row: dict, use_toe_touch=True):
    ss_mean = row.get("sway_SS_mean")
    ss_sd   = row.get("sway_SS_SD")
    ap_mean = row.get("sway_AP_mean")
    ap_sd   = row.get("sway_AP_SD")
    toe     = row.get("toe_touches")

    out = {}
    out["sway_SS_mean_score"] = score_sway_ss_mean_7y(ss_mean)
    out["sway_SS_SD_score"]   = score_sway_ss_sd_7y(ss_sd)
    out["sway_AP_mean_score"] = score_sway_ap_mean_7y(ap_mean)
    out["sway_AP_SD_score"]   = score_sway_ap_sd_7y(ap_sd)

    base_scores = [
        out["sway_SS_mean_score"],
        out["sway_SS_SD_score"],
        out["sway_AP_mean_score"],
        out["sway_AP_SD_score"],
    ]

    if any(v is None for v in base_scores):
        out["total_score"] = None
        out["interpretation"] = None
        return out

    total = sum(base_scores)

    # If you want exactly 4 parameters, stop here.
    out["total_score_4params"] = total

    if use_toe_touch:
        out["toe_touches_score"] = score_toe_touches_7y(toe)
        if out["toe_touches_score"] is None:
            out["total_score"] = None
            out["interpretation"] = None
            return out
        total5 = total + out["toe_touches_score"]
        out["total_score"] = total5
        out["interpretation"] = interpret_total_7y(total5)
    else:
        out["total_score"] = total
        # NOTE: the doc’s interpretation bands are for 5-parameter total (max 30).
        # If you truly remove toe touch permanently, define new bands for max=25.
        out["interpretation"] = f"4-parameter total (max 25): {total}"

    return out
# =========================
# ---------- 6 YEARS RUBRIC (from your doc)
# =========================

def score_sway_ss_mean_6y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    # >= 13.19 -> 1
    if x >= 13.19: return 1
    if 10.84 <= x < 13.19: return 2
    if 8.49  <= x < 10.84: return 3
    if 6.14  <= x <  8.49: return 4
    if 3.79  <= x <  6.14: return 5
    if 1.44  <= x <  3.79: return 6
    if 0.00  <= x <  1.44: return 7
    return 7

def score_sway_ss_sd_6y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    # >= 5.88 -> 1
    if x >= 5.88: return 1
    if 4.78 <= x < 5.88: return 2
    if 3.69 <= x < 4.78: return 3
    if 2.59 <= x < 3.69: return 4
    if 1.50 <= x < 2.59: return 5
    if 0.40 <= x < 1.50: return 6
    if 0.00 <= x < 0.40: return 7
    return 7

def score_sway_ap_mean_6y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    # >= 7.07 -> 1
    if x >= 7.07: return 1
    if 5.74 <= x < 7.07: return 2
    if 4.41 <= x < 5.74: return 3
    if 3.08 <= x < 4.41: return 4
    if 1.75 <= x < 3.08: return 5
    if 0.42 <= x < 1.75: return 6
    if 0.00 <= x < 0.42: return 7
    return 7

def score_sway_ap_sd_6y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    # >= 6.25 -> 1
    if x >= 6.25: return 1
    if 4.96 <= x < 6.25: return 2
    if 3.67 <= x < 4.96: return 3
    if 2.38 <= x < 3.67: return 4
    if 1.10 <= x < 2.38: return 5
    if 0.00 <= x < 1.10: return 6
    return 6

def score_toe_touches_6y(x):
    x = _clamp_nonneg(x)
    if x is None: return None
    # >= 14 -> 1
    if x >= 14: return 1
    if 11 <= x < 14: return 2
    if 8  <= x < 11: return 3
    if 5  <= x <  8: return 4
    if 2  <= x <  5: return 5
    if 0  <= x <  2: return 6
    return 6

def interpret_total_6y(total):
    """
    Total max for 6y = 33 (7+7+7+6+6).
    Using non-overlapping convention:
      <10, [10,14), [14,18), [18,26), [26,30), [30,33]
    """
    if total is None:
        return None
    total = float(total)
    if total < 10: return "Extremely Below Average"
    if 10 <= total < 14: return "Well-Below Average"
    if 14 <= total < 18: return "Below Average"
    if 18 <= total < 26: return "Average"
    if 26 <= total < 30: return "Above average"
    if 30 <= total <= 33: return "Well-Above Average"
    return "Out of range"

def score_row_6y(row: dict, use_toe_touch=True):
    ss_mean = row.get("sway_SS_mean")
    ss_sd   = row.get("sway_SS_SD")
    ap_mean = row.get("sway_AP_mean")
    ap_sd   = row.get("sway_AP_SD")
    toe     = row.get("toe_touches")

    out = {}
    out["sway_SS_mean_score"] = score_sway_ss_mean_6y(ss_mean)
    out["sway_SS_SD_score"]   = score_sway_ss_sd_6y(ss_sd)
    out["sway_AP_mean_score"] = score_sway_ap_mean_6y(ap_mean)
    out["sway_AP_SD_score"]   = score_sway_ap_sd_6y(ap_sd)

    base_scores = [
        out["sway_SS_mean_score"],
        out["sway_SS_SD_score"],
        out["sway_AP_mean_score"],
        out["sway_AP_SD_score"],
    ]

    if any(v is None for v in base_scores):
        out["total_score"] = None
        out["interpretation"] = None
        return out

    total = sum(base_scores)
    out["total_score_4params"] = total

    if use_toe_touch:
        out["toe_touches_score"] = score_toe_touches_6y(toe)
        if out["toe_touches_score"] is None:
            out["total_score"] = None
            out["interpretation"] = None
            return out
        total5 = total + out["toe_touches_score"]
        out["total_score"] = total5
        out["interpretation"] = interpret_total_6y(total5)
    else:
        out["total_score"] = total
        out["interpretation"] = f"4-parameter total (max 27): {total}"

    return out
