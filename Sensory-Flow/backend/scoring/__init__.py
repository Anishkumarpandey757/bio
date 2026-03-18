"""
Scoring module - contains age-specific scoring bins for all exercises.

Each math file contains:
- Scoring bins (thresholds) for 6-year and 7-year age groups
- score_row_* functions that take raw metrics and return scores
- interpret_total* functions for interpretation bands

Exercise modules:
- math_prone_extension: Prone extension scoring
- math_supine_flexion: Supine flexion scoring  
- math_ols_eo: One Leg Standing Eyes Open - Left Leg scoring
- math_ols_ec: One Leg Standing Eyes Closed - Left Leg scoring
- math_ols_rl_eo: One Leg Standing Eyes Open - Right Leg scoring
- math_ols_rl_ec: One Leg Standing Eyes Closed - Right Leg scoring
- math_tandem_walking_eo: Tandem Walking Eyes Open scoring
- math_tandem_walking_ec: Tandem Walking Eyes Closed scoring
- math_jumping_jacks: Jumping Jacks scoring
- math_total_assessment: Total assessment aggregation across all exercises
"""

from .math_prone_extension import score_row_prone
from .math_supine_flexion import score_row_supine
# Left Leg OLS scoring (existing files)
from .math_ols_eo import score_row_6y as score_ols_ll_eo_6y, score_row_7y as score_ols_ll_eo_7y
from .math_ols_ec import score_row_6y_ec as score_ols_ll_ec_6y, score_row_7y_ec as score_ols_ll_ec_7y
# Right Leg OLS scoring (new files)
from .math_ols_rl_eo import score_row_rl_eo as score_ols_rl_eo
from .math_ols_rl_ec import score_row_rl_ec as score_ols_rl_ec
from .math_tandem_walking_eo import score_row_tandem_eo
from .math_tandem_walking_ec import score_row_tandem_ec
from .math_jumping_jacks import score_row_6y as score_jj_6y, score_row_7y as score_jj_7y
from .math_total_assessment import score_assessment


# Wrapper functions matching processor expectations
def score_jumping_jacks(raw_metrics, age_years):
    """Wrapper for jumping jacks scoring"""
    from .math_jumping_jacks import score_row
    return score_row(raw_metrics, age_years)

def score_tandem_walking(raw_metrics, age_years, eyes_open):
    """Wrapper for tandem walking scoring"""
    if eyes_open:
        return score_row_tandem_eo(raw_metrics, age_years)
    else:
        return score_row_tandem_ec(raw_metrics, age_years)


def score_ols(row: dict, age_years: int, eyes_open: bool, raised_leg: str = "L") -> dict:
    """Score One Leg Standing based on age, eyes condition, and raised leg.
    
    Args:
        row: Dict with sway_SS_mean, sway_SS_SD, sway_AP_mean, sway_AP_SD, toe_touches
        age_years: 6 or 7
        eyes_open: True for eyes open, False for eyes closed
        raised_leg: "L" for left leg raised, "R" for right leg raised
    """
    # Right Leg scoring uses separate bins
    if raised_leg.upper() == "R":
        if eyes_open:
            return score_ols_rl_eo(row, age_years=age_years)
        else:
            return score_ols_rl_ec(row, age_years=age_years)
    
    # Left Leg scoring (default)
    if eyes_open:
        return score_ols_ll_eo_6y(row) if age_years == 6 else score_ols_ll_eo_7y(row)
    else:
        return score_ols_ll_ec_6y(row) if age_years == 6 else score_ols_ll_ec_7y(row)


def score_tandem_walking(row: dict, age_years: int, eyes_open: bool) -> dict:
    """Score Tandem Walking based on age and eyes condition."""
    if eyes_open:
        return score_row_tandem_eo(row, age_years)
    else:
        return score_row_tandem_ec(row, age_years)


def score_jumping_jacks(row: dict, age_years: int) -> dict:
    """Score Jumping Jacks based on age."""
    return score_jj_6y(row) if age_years == 6 else score_jj_7y(row)


__all__ = [
    "score_row_prone",
    "score_row_supine", 
    "score_ols",
    "score_tandem_walking",
    "score_jumping_jacks",
    "score_assessment",
]
