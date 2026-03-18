# 📋 Processor Functions - What Was Ported

## OLS (One Leg Standing) - Complete List

### Helper Functions (9 total)
```python
✅ _angle_signed_to_vertical(p1, p2)
   └─ Signed angle from vertical (+right, -left)

✅ _angle_to_vertical(p1, p2)  
   └─ Unsigned angle from vertical

✅ _neck_goniometer_deg(P3, LM)
   └─ Cervical angle (3D) = angle between trunk and head vectors

✅ _count_toe_touches(toe_h, fps, norm_thr, min_frames, min_gap_s)
   └─ Count floor-contact events with debounce

✅ _count_transitions(boolean_series, min_gap_frames)
   └─ Count rising edges True with simple debounce

✅ _supporting_foot_xy(df, raised_leg)
   └─ Midpoint of heel & big-toe of stance foot

✅ _stance_ball_xy(df, raised_leg, alpha=0.30)
   └─ Ball of stance foot (distal 1/3 along sole)

✅ _foot_drift_metrics(df, raised_leg, px_per_cm)
   └─ Displacement: max/mean (cm), lateral/AP components, pelvis-normalized
   └─ Returns 10 metrics

✅ _summarize_neck(df)
   └─ Neck statistics: mean, SD, peak (deg)

✅ _ols_events_and_strategy(df, fps, raised_leg, age_tag, ...)
   └─ Foot touches, toe touches, hands off hips, balance strategy
   └─ Returns 8 metrics
```

### Main Functions (3 total)
```python
✅ measure_ols_video(video_path, view, raised_leg, smooth_k, model_complexity)
   └─ Stage 1: Extract per-frame metrics
   └─ Returns: (DataFrame with 20+ columns, fps)
   └─ Columns: trunk_signed_deg, trunk_abs_deg, neck_deg, hip_R, hip_L, knee_R, 
              knee_L, raised_ank_h, raised_toe_h, wristL_hipL_norm, 
              wristR_hipR_norm, x29-x32, y29-y32, x23, y23, x24, y24, 
              y_floor, pelvis_px

✅ summarize_ols_clip(df, fps)
   └─ Helper: calculates sway from df

✅ extract_ols_metrics(front_video_path, side_video_path, raised_leg, age_tag, px_per_cm)
   └─ Stage 2: Calculate all clip-level metrics
   └─ Returns: dict with 20+ metrics (sway, drift, neck, events, strategy)

✅ process_one_leg_standing(front_video_path, side_video_path, age_years, eyes_open, raised_leg)
   └─ Stage 3: Score and interpret
   └─ Returns: {rawMetrics, scores, totalScore, maxScore, interpretation}
```

---

## Prone Extension - Complete List

### Helper Functions (8 total)
```python
✅ _hip_extension_from_internal(a)
   └─ Convert internal hip angle to clinical extension (0..30°)

✅ _knee_flexion_from_internal(a)
   └─ Convert internal knee angle to clinical flexion (0..13°)

✅ _angle_to_vertical(p1, p2)
   └─ Unsigned angle from vertical

✅ _pelvis_width_xy(P2)
   └─ Pelvis width in pixels (for normalization)

✅ _estimate_floor_y(P2, H)
   └─ Robust floor y-coordinate estimate

✅ _baseline(x, n=12)
   └─ Robust baseline = median of first n frames

✅ _held_at_start(metric_increasing_when_up, thr, n=12)
   └─ Hysteresis check: was metric already above threshold at start?

✅ _onset_time_seconds(series_inc_up, fps, amp_thr, z_thresh, ...)
   └─ Detect first sustained movement via amplitude + velocity gates
   └─ Returns: time (seconds) or nan

✅ _ue_le_delta_t_seconds(df, fps, neck_hold_deg, trunk_hold_deg, ...)
   └─ Upper Extremity vs Lower Extremity timing delta
   └─ Detects if UE moved before/after/simultaneously with LE
   └─ Returns: delta-t in seconds
```

### Main Functions (3 total)
```python
✅ measure_prone_extension_video(video_path)
   └─ Stage 1: Extract per-frame metrics
   └─ Returns: (DataFrame with 13 columns, fps)
   └─ Columns: neck, trunk, hip_R, hip_L, knee_R, knee_L, thigh_R, thigh_L, 
              y_floor, pelvis_px, sh_y, wr_min_y, an_min_y

✅ extract_prone_extension_metrics(video_path, age_years)
   └─ Stage 2: Calculate all clip-level metrics
   └─ Returns: dict with 15+ metrics (angles, thigh heights, timing, leg used)

✅ process_prone_extension(video_path, age_years)
   └─ Stage 3: Score and interpret  
   └─ Returns: {rawMetrics, scores, totalScore, maxScore, interpretation}
```

---

## Pattern Used - Apply to Supine, Tandem, Jumping

### Template Structure
```python
# FILE: backend/processors/<exercise_name>.py

"""<Exercise> Processor - Description
Ported from: <notebook_name>.py
"""

import os, cv2, numpy as np, pandas as pd
from typing import Dict, Any, Optional, Tuple
import mediapipe as mp
from .common import LM, rolling_med, angle_3pt, angle_between_vecs

# ---- HELPER FUNCTIONS (from original notebook) ----
# Copy all utility functions that were used to calculate metrics

def _helper_1(...): ...
def _helper_2(...): ...
# ... etc

# ---- MAIN FUNCTIONS (3-stage pipeline) ----

def measure_<exercise>_video(video_path: str) -> Tuple[pd.DataFrame, float]:
    """Stage 1: Extract per-frame metrics"""
    # 1. Open video, get FPS
    # 2. For each frame: run pose, calculate per-frame metrics
    # 3. Smooth kinematic series
    # 4. Return (DataFrame, fps)

def extract_<exercise>_metrics(video_path: str, age_years: int) -> Dict[str, Any]:
    """Stage 2: Calculate clip-level metrics"""
    # 1. Call measure_*_video()
    # 2. Calculate summary statistics
    # 3. Detect events/strategy/timing
    # 4. Return dict with all metrics

def process_<exercise>(video_path: Optional[str], age_years: int) -> Dict[str, Any]:
    """Stage 3: Score and interpret"""
    # 1. Call extract_*_metrics()
    # 2. Call scoring module (from backend/scoring/)
    # 3. Return {rawMetrics, scores, totalScore, maxScore, interpretation}
```

---

## Where to Get Helper Functions

When porting remaining processors:

✅ **Ready to copy from OLS**:
- `_count_toe_touches()` → any exercise with toe events
- `_count_transitions()` → any exercise with on/off events

✅ **Ready to copy from Prone**:
- `_baseline()` → any exercise that needs robust baseline
- `_held_at_start()` → any exercise with hysteresis
- `_onset_time_seconds()` → any exercise with movement onsets
- `_ue_le_delta_t_seconds()` template → adapt for Supine/Tandem/Jumping

✅ **Common helpers** (from `common.py`):
- `angle_3pt()` → all exercises
- `angle_between_vecs()` → all exercises
- `rolling_med()` → all exercises for smoothing
- `LM` (landmark dictionary) → all exercises

---

## Implementation Checklist per Exercise

When implementing remaining processors:

### Supine Flexion (Estimate: 30 mins)
- [ ] Copy helper functions from Prone
- [ ] Update `measure_supine_flexion_video()` for all neck_flex, trunk_flex, hip, knee, shoulder_h, nose_sh_dist
- [ ] Add `_chin_tuck_mask()` for chin tuck detection
- [ ] Adapt `_ue_le_delta_t_supine()` (different candidate selection)
- [ ] Write `extract_supine_flexion_metrics()` 
- [ ] Update `process_supine_flexion()`
- [ ] Syntax check: no errors
- [ ] Test with sample video

### Tandem Walking (Estimate: 3-4 hours)
- [ ] Identify gait events (stance/swing transitions)
- [ ] Implement step detection
- [ ] Port coordinate transformation logic
- [ ] Calculate per-step metrics
- [ ] Implement stability/sway metrics
- [ ] Write extraction function
- [ ] Test against original notebook

### Jumping Jacks (Estimate: 2-3 hours)
- [ ] Port peak detection logic
- [ ] Implement jump counting
- [ ] Calculate angle metrics (shoulders, hips)
- [ ] Calculate displacement metrics
- [ ] Implement symmetry analysis
- [ ] Write extraction function
- [ ] Test against original notebook

---

## Verification Steps

For each completed processor:

```bash
# 1. Syntax check
pylance --check backend/processors/<exercise>.py
# Expected: "No syntax errors found"

# 2. Import check
python -c "from backend.processors.<exercise> import measure_*_video, extract_*_metrics, process_*"
# Expected: No ImportError

# 3. Test with sample video
# Upload test video → Check database
# Compare extracted metrics vs original notebook

# 4. Scoring integration
# Verify scores calculated correctly
# Check against expected ranges per age
```

---

## Quick Links

- **OLS Source**: `/ols_left_leg_eo/ols_leftleg_eo.py`
- **Prone Source**: `/proneextention/prone2_0.py`
- **Supine Source**: `/suplineflexion/supine.py`
- **Tandem Source**: `/tademwalkingec/tademmanin (3).py`
- **Jumping Source**: `/jumping_jacks/jumping_jacks (4).py`

**Migration Guide**: `Sensory-Flow/PROCESSOR_MIGRATION_GUIDE.md`

---

**Status**: OLS ✅ + Prone ✅ → 2/5 Complete (40%)  
**Next**: Supine 🟡 (in progress, 30 mins remaining)
