# Processor Migration Guide: Original Notebooks → Backend

**Goal**: Port exact metric calculations from Colab notebooks into backend processors while maintaining the 3-stage pipeline.

## ✅ COMPLETED

### 1. **One Leg Standing (OLS)** - `backend/processors/one_leg_standing.py`

**Status**: ✅ **FULLY PORTED** (Syntax verified, no errors)

**Original Notebooks Integrated**:
- `ols_leftleg_eo.py`
- `ols_leftleg_ec.py` 
- `ols_rightleg_eo.py`
- `ols_rightleg_ec.py`

**Key Functions Ported**:
- ✅ `_angle_signed_to_vertical()` - Signed trunk angle vs vertical
- ✅ `_angle_to_vertical()` - Unsigned angle vs vertical
- ✅ `_neck_goniometer_deg()` - Cervical angle (3D)
- ✅ `_count_toe_touches()` - Toe contact event counting
- ✅ `_count_transitions()` - Rising edge detection with debounce
- ✅ `_supporting_foot_xy()` - Stance foot midpoint
- ✅ `_stance_ball_xy()` - Stance foot ball (distal 1/3)
- ✅ `_foot_drift_metrics()` - Drift max/mean, lateral/AP components, pelvis-normalized
- ✅ `_summarize_neck()` - Neck mean/SD/peak angles
- ✅ `_ols_events_and_strategy()` - Foot touches, toe touches, hands off hips, balance strategy

**Metrics Extracted** (comprehensive):
- **Sway**: `sway_SS_mean`, `sway_SS_SD` (mediolateral from front view)
- **Sway**: `sway_AP_mean`, `sway_AP_SD` (anteroposterior from side view)
- **Foot Drift**: `drift_max_cm`, `drift_mean_cm`, `drift_lat_max_cm`, `drift_ap_max_cm` (and normalization variants)
- **Neck**: `neck_mean_deg`, `neck_sd_deg`, `neck_peak_deg`
- **Events**: `toe_touches`, `foot_touches`, `hands_off_cnt`, `hands_off_pct`
- **Strategy**: `balance_strategy` (Stepping/Knee/Hip/Ankle)
- **Supporting**: `med_trunk_deg`, `med_hip_deg`, `med_knee_deg`

**Per-Frame Columns Extracted** (from measure function):
All required 2D/3D coordinates, angles, and supporting features

---

### 2. **Prone Extension** - `backend/processors/prone_extension.py`

**Status**: ✅ **FULLY PORTED** (Syntax verified, no errors)

**Original Notebook Integrated**:
- `prone2_0.py`

**Key Functions Ported**:
- ✅ `_hip_extension_from_internal()` - Convert internal to clinical hip extension
- ✅ `_knee_flexion_from_internal()` - Convert internal to clinical knee flexion
- ✅ `_angle_to_vertical()` - Unsigned angle vs vertical
- ✅ `_baseline()` - Robust baseline estimation
- ✅ `_held_at_start()` - Hysteresis check
- ✅ `_onset_time_seconds()` - Amplitude + velocity gate onset detection
- ✅ `_ue_le_delta_t_seconds()` - UE/LE timing delta calculation

**Metrics Extracted** (comprehensive):
- **Angles**: `neck_mean`, `trunk_mean`, `hip_R_mean`, `hip_L_mean`, `knee_R_mean`, `knee_L_mean`
- **Thigh Height**: `thigh_R_mean`, `thigh_L_mean` (distal 1/3, pelvis-normalized)
- **Timing**: `ue_le_delta_t_s` (Upper Extremity vs Lower Extremity onset delta)
- **Duration**: `hold_duration_s`
- **Leg Selection**: `leg_used` (R/L based on which thigh lifted more)

**Per-Frame Columns Extracted**:
- Neck angle, trunk angle, hip angles (R/L), knee angles (R/L)
- Thigh height (R/L)
- Floor estimate, pelvis scale
- Y-series for timing (shoulder_y, wrist_min_y, ankle_min_y)

---

## 🔄 IN PROGRESS

### 3. **Supine Flexion** - `backend/processors/supine_flexion.py`

**Status**: 🟡 **STRUCTURE UPDATED** - Headers and imports fixed, measure function needs enhancement

**Original Notebook**:
- `supine.py`

**What Needs To Be Done**:

1. **Add Helper Functions** (before `measure_supine_flexion_video`):
   ```python
   def _baseline(x, n=12):
       """Median of first n frames"""
       x = pd.Series(x, dtype=float)
       return float(x.iloc[:max(3, n)].median(skipna=True))
   
   def _held_at_start(metric_increasing_when_up, thr, n=12):
       """True if first n frames are already above threshold"""
       x = pd.Series(metric_increasing_when_up, dtype=float)
       return bool((x.iloc[:max(3, n)] >= thr).sum() >= max(3, n) // 2)
   
   def _onset_time_seconds(series_inc_up, fps, amp_thr, z_thresh=0.6, ...):
       """Detect first sustained upward movement"""
       # (Copy from prone_extension.py)
   
   def _ue_le_delta_t_supine(df, fps, ...):
       """UE/LE delta-t for supine (different from prone)"""
       # UE candidates: shoulder_h, neck_flex, trunk_flex
       # LE: hip or knee flexion
       # (Copy logic from supine.py lines 121-153)
   
   def _chin_tuck_mask(df, fps, neck_thr_deg=12.0, nose_drop_frac=0.08):
       """Chin tuck present when neck_flex + nose drop"""
       # (Copy from supine.py lines 156-159)
   ```

2. **Enhance measure_supine_flexion_video**:
   - Extract per-frame metrics: neck_flex, trunk_flex, hip_R, hip_L, knee_R, knee_L
   - Extract height metrics: shoulder_h (normalized), nose_sh_dist
   - Extract timing proxies: sh_y, wr_min_y
   - Smooth appropriate series

3. **Add extract_supine_flexion_metrics**:
   - Returns: neck_flex_mean, trunk_flex_mean, hip means, knee means, shoulder_h_mean
   - Chin tuck presence/duration
   - UE/LE delta-t
   - Leg selection (R/L)

4. **Update process_supine_flexion**:
   - Call scoring module with raw metrics

**Key Differences from Prone**:
- Trunk flexion calculated as `180° - angle(Head, Shoulder, MidHip)` in 3D
- Chin tuck has dedicated detection (neck_flex + nose drop)
- UE/LE delta-t logic slightly different (more complex candidate selection)

---

## ❌ NOT STARTED

### 4. **Tandem Walking** - `backend/processors/tandem_walking.py`

**Original Notebooks**:
- `tademmanin (3).py` (Eyes Closed variant)
- `tademmanin (3).py` (Eyes Open variant)

**Complexity**: 🔴 **HIGH** - Most complex notebook with:
- State machine for gait analysis
- Multiple gait event detectors
- Complex coordinate transformations
- Per-step metrics

**Critical Functions to Port**:
- Stance/swing detection
- Step detection
- Step length calculation
- ML/AP sway extraction
- Step gap measurement
- Stability metrics

**Estimated Effort**: 3-4 hours to port carefully

---

### 5. **Jumping Jacks** - `backend/processors/jumping_jacks.py`

**Original Notebook**:
- `jumping_jacks (4).py`

**Complexity**: 🟠 **MEDIUM** - Moderately complex with:
- Shoulder/hip angle tracking
- Vertical displacement detection
- Jump counting
- Symmetry metrics

**Critical Functions to Port**:
- Peak detection
- Jump counting logic
- Angle calculations
- Displacement normalization

**Estimated Effort**: 2-3 hours to port carefully

---

## 📋 PORTING TEMPLATE

All processors follow this 3-stage pipeline:

```python
# Stage 1: MEASURE - Extract per-frame raw data
def measure_*_video(video_path: str) -> Tuple[pd.DataFrame, float]:
    """
    Returns: (per_frame_dataframe, fps)
    
    Key steps:
    1. Open video, get FPS
    2. For each frame:
       a. Run MediaPipe Pose extraction
       b. Calculate per-frame metrics (angles, distances, heights)
       c. Append row to dataframe
    3. Smooth kinematic series (rolling median, k=5)
    4. Return DataFrame + FPS
    """

# Stage 2: EXTRACT - Calculated clip-level metrics
def extract_*_metrics(video_path, age_tag, ...) -> Dict[str, Any]:
    """
    Takes measure() output, calculates summary statistics:
    - Means, SDs of angles/distances
    - Event counts (touching, transitions, etc.)
    - Strategy/classification
    - Timing metrics (onsets, deltas)
    
    Returns: dict with all metrics
    """

# Stage 3: PROCESS - Score and interpret
def process_*(video_path, age_years) -> Dict[str, Any]:
    """
    1. Call extract_*_metrics()
    2. Call scoring module from backend/scoring/
    3. Package results with interpretation
    
    Returns: {rawMetrics, scores, totalScore, maxScore, interpretation}
    """
```

---

## 🚀 QUICK START for Remaining Processors

### For Supine Flexion:

1. **Copy helper functions**:
   ```bash
   # Copy _baseline, _held_at_start, _onset_time_seconds from prone_extension.py
   # Adapt _ue_le_delta_t to supine-specific candidate selection
   ```

2. **Update measure function**:
   - Match the pattern in `measure_prone_extension_video()`
   - Extract: neck_flex, trunk_flex, hip angles, knee angles, shoulder_h, nose_sh_dist, timing proxies
   - Use 3D angles where possible; 2D for camera-tilt robustness where indicated

3. **Add extraction function**:
   - Calculate means from per-frame data
   - Detect chin tuck with `_chin_tuck_mask()`
   - Calculate UE/LE timing delta
   - Select reporting leg by larger median hip flexion

### For Tandem Walking & Jumping Jacks:

See original notebooks for complex state machines. Consider:
1. Start with per-frame calculations
2. Incrementally add event detection
3. Test against original notebook outputs

---

## ✅ Verification Checklist

For each processor:
- [ ] All helper functions imported or defined
- [ ] measure_*_video() extracts all original notebook columns
- [ ] Smoothing applied to kinematic series
- [ ] extract_*_metrics() calculates same metrics as original
- [ ] process_*() calls correct scoring module
- [ ] Syntax check: `pylance --check <file>`
- [ ] Integration test: Can Express route call it?

---

## 📚 Reference: Original Notebook Locations

- **OLS**: 
  - `/ols_left_leg_eo/ols_leftleg_eo.py` ✅
  - `/ols_leftleg_ec/ols_leftleg_ec.py` ✅
  - `/ols_rightleg_ec/ols_rightleg_ec_.py` ✅
  - `/ols_rightleg_eo/ols_rightleg_eo(2) (1).py` ✅

- **Prone Extension**:
  - `/proneextention/prone2_0.py` ✅

- **Supine Flexion**:
  - `/suplineflexion/supine.py` 🔄

- **Tandem Walking**:
  - `/tademwalkingec/tademmanin (3).py` ❌
  - `/tademwalkingeo/tademmanin (3).py` ❌

- **Jumping Jacks**:
  - `/jumping_jacks/jumping_jacks (4).py` ❌

---

## 📝 Next Steps

1. **Complete Supine Flexion** (straightforward, ~30 mins)
2. **Start Tandem Walking** (complex, ~3-4 hours)
3. **Complete Jumping Jacks** (~2-3 hours)
4. **Integration test**: Run full pipeline with sample videos
5. **Validation**: Compare processor outputs vs original notebooks on same test videos

---

**Last Updated**: 2026-02-18  
**Completed**: OLS + Prone Extension  
**In Progress**: Supine Flexion  
**To Do**: Tandem Walking + Jumping Jacks
