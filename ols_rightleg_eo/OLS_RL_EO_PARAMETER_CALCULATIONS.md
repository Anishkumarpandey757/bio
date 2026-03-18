# OLS Right Leg Eyes Open – Parameter Calculations (from ols_rightleg_eo_colab.py)

## 1. Per-frame extraction (`measure_ols_video`)

**Landmarks:** MediaPipe pose; 2D `P2` (x*W, y*H), 3D `P3` (world or P2+zeros).

**Centers:**
- `sh2` = (L_SH + R_SH) / 2  (2D)
- `hp2` = (L_HP + R_HP) / 2  (2D)
- `sh3`, `hp3`, `ear3` = same in 3D

**Trunk sway (2D):**
- `trunk_signed` = `angle_signed_to_vertical(hp2, sh2)`  → angle of vector (hip→shoulder) vs vertical (0,−1); range ~−90 to +90°
- `trunk_abs` = |trunk_signed|  → 0–90°

**Neck (3D):**
- `neck_goni_deg` = angle between vectors (trunk = sh3−hp3, head = ear3−sh3) via dot/clip/arccos

**Hip/Knee (3D):**
- `hip_R` = 180 − angle_3pt(R_SH, R_HP, R_KN); `hip_L` = 180 − angle_3pt(L_SH, L_HP, L_KN)
- `knee_R` = 180 − angle_3pt(R_HP, R_KN, R_AN); `knee_L` = 180 − angle_3pt(L_HP, L_KN, L_AN)

**Floor & scale:**
- `y_floor` = 95th percentile of ankle (+ heel/toe if present) y
- `px_scale` = pelvis_width_xy(P2) = ‖L_HP − R_HP‖ in pixels

**Raised foot (normalized height):**
- If raised_leg == "L": raised ankle/toe = left ankle, left toe (31); else right
- `raised_ank_h` = max((y_floor − raised_ankle_y) / px_scale, 0)
- `raised_toe_h` = same for big toe

**Wrist–hip (normalized):**
- `wristL_hipL_norm` = ‖L_WR − L_HP‖ / px_scale; same for R

**Heel/toe pixels:** x29,y29 (L_HEEL), x30,y30 (R_HEEL), x31,y31 (L_TOE), x32,y32 (R_TOE)

**Smoothing:** Rolling median k=5, center=True on trunk_signed_deg, trunk_abs_deg, neck_goni_deg, hip_R, hip_L, knee_R, knee_L, raised_ank_h, raised_toe_h, wristL_hipL_norm, wristR_hipR_norm.

**DataFrame columns (24):**  
trunk_signed_deg, trunk_abs_deg, neck_goni_deg, hip_R, hip_L, knee_R, knee_L, raised_ank_h, raised_toe_h, wristL_hipL_norm, wristR_hipR_norm, y_floor, pelvis_px, sh_x, sh_y, hp_x, hp_y, x29,y29,x30,y30,x31,y31,x32,y32.

---

## 2. Sway summary (`summarize_ols_clip`)

- **sway_mean_deg** = mean(df["trunk_abs_deg"])
- **sway_sd_deg** = std(df["trunk_abs_deg"], ddof=0)
- **sway_peak_deg** = max(trunk_abs_deg)
- **best_idx** = idxmax(trunk_abs_deg)
- **clip_dur_s** = len(df) / fps

*(Origin exports these as raw 0–90°; backend converts to 90−angle so “small = small tilt” for scoring.)*

---

## 3. Events & strategy (`ols_events_and_strategy`)

**Foot touches (ankle):**
- Hysteresis on `raised_ank_h`: up threshold `ank_up=0.15`, down `ank_down=0.05`
- `grounded` = state after hysteresis
- **foot_touches_ankle** = count_transitions(grounded going True, min_gap_frames=8)

**Toe touches:**
- **toe_touches** = count_toe_touches(df, fps, norm_thr=0.025 for 7y / 0.035 for 6y, min_frames=3, min_gap_s=0.30 or 0.35)
- Logic: raised_toe_h ≤ norm_thr for ≥ min_frames → one touch; refractory min_gap_s between touches

**Hands off:**
- onL = wristL_hipL_norm ≤ 0.35; onR = wristR_hipR_norm ≤ 0.35
- both_on = onL & onR; **hands_off** = ~both_on
- **hands_off_cnt** = count_transitions(hands_off, min_gap_frames=6)
- **hands_off_pct** = mean(hands_off)  → 0–1 in colab (backend may report 0–100)

**Strategy (medians over airborne frames only):**
- **med_trunk** = median(trunk_abs_deg | airborne)
- **med_hip** = median of [hip_L, hip_R] over all frames
- **med_knee** = median of [knee_L, knee_R] over all frames
- Rules:
  - if foot_touches_ankle > 0 or toe_touches > 0 → **"Stepping"**
  - elif med_knee ≥ 15 and med_trunk < 10 → **"Knee strategy"**
  - elif med_hip ≥ 15 and med_trunk ≥ 7 → **"Hip strategy"**
  - else → **"Ankle/minimal"**

Output: foot_touches_ankle, toe_touches, hands_off_cnt, hands_off_pct, strategy, med_trunk_deg, med_hip_deg, med_knee_deg.  
*(med_trunk_deg is raw 0–90° in colab; backend converts to 90− for export.)*

---

## 4. Neck summary (`summarize_neck`)

- **neck_mean_deg** = mean(neck_deg or neck_goni_deg)
- **neck_sd_deg** = std(ddof=0)
- **neck_peak_deg** = max  
*(Colab code uses df.get("neck_deg"); main pipeline has "neck_goni_deg".)*

---

## 5. Joint means (`joint_means`)

- **trunk_mean_deg** = mean(trunk_abs_deg)
- **hip_L_mean_deg**, **hip_R_mean_deg** = mean(hip_L), mean(hip_R)
- **knee_L_mean_deg**, **knee_R_mean_deg** = mean(knee_L), mean(knee_R)
- **neck_mean_deg** = mean(neck_goni_deg)

---

## 6. Foot drift (`foot_drift_metrics`)

- **Stance ball:** toe + 0.30*(heel − toe) for supporting foot (opposite of raised_leg).  
  Right leg raised → stance = left → heel 29, toe 31. Left leg raised → stance = right → heel 30, toe 32.
- **Start:** median of ball positions in first 10 frames.
- **delta** = ball − start (per frame).
- **drift_px** = ‖delta‖; **drift_lat_px** = |delta_x|; **drift_ap_px** = |delta_y|.
- **To cm:** divide by `OLS_PX_PER_CM` (e.g. 3.2).
- **drift_max_cm**, **drift_mean_cm**, **drift_lat_max_cm**, **drift_lat_mean_cm**, **drift_ap_max_cm**, **drift_ap_mean_cm**.
- **drift_pelvis_max**, **drift_pelvis_mean** = drift_px / pelvis_px (if pelvis_px from x23,y23,x24,y24 available; else None).

---

## 7. Helpers

- **angle_signed_to_vertical(P0, P1):** v = (P1−P0)/‖…‖; angle = arccos(dot(v, (0,−1))); sign = +1 if v_x≥0 else −1.
- **angle_3pt(A,B,C):** angle at B between BA and BC (degrees).
- **count_transitions(bool_series, min_gap_frames=6):** count rising edges True with debounce (no new count for min_gap_frames after one).

---

## 8. Output row (per clip) – what gets exported

Combined from: summarize_ols_clip + ols_events_and_strategy + joint_means + foot_drift_metrics (and optionally summarize_neck if used).

So each clip row has: view, video, sway_mean_deg, sway_sd_deg, sway_peak_deg, best_idx, clip_dur_s, foot_touches_ankle, toe_touches, hands_off_cnt, hands_off_pct, strategy, med_trunk_deg, med_hip_deg, med_knee_deg, trunk_mean_deg, hip_L_mean_deg, hip_R_mean_deg, knee_L_mean_deg, knee_R_mean_deg, neck_mean_deg, drift_max_px, drift_mean_px, drift_max_cm, drift_mean_cm, drift_lat_max_cm, drift_lat_mean_cm, drift_ap_max_cm, drift_ap_mean_cm, drift_pelvis_max, drift_pelvis_mean.
