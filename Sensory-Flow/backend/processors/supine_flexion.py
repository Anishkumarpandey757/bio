"""Supine Flexion Processor - Side view required
Ported from: supine.py
Calculates: neck/trunk flexion, hip/knee angles, shoulder height,
chin tuck detection, UE/LE delta-t metrics
"""

import os
import cv2
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple

import mediapipe as mp
mp_pose = mp.solutions.pose

from .common import LM, rolling_med, angle_3pt, angle_between_vecs, ensure_video_readable


# ---- Helper functions from original notebook ----

def _baseline(x, n=12):
    """Median of first n frames; robust when clips start near rest/hold"""
    x = pd.Series(x, dtype=float)
    return float(x.iloc[:max(3, n)].median(skipna=True))


def _held_at_start(metric_increasing_when_up, thr, n=12):
    """True if the first n frames are already above the 'hold' threshold"""
    x = pd.Series(metric_increasing_when_up, dtype=float)
    return bool((x.iloc[:max(3, n)] >= thr).sum() >= max(3, n) // 2)


def _onset_time_seconds(series_inc_up, fps, amp_thr, z_thresh=0.6, min_frames=3, max_frac=0.4, smooth_k=5):
    """Detect first sustained upward movement via amplitude + velocity gates"""
    s = pd.Series(series_inc_up, dtype=float).rolling(smooth_k, center=True, min_periods=1).median()
    base = _baseline(s, n=12)
    
    # amplitude gate
    amp = s - base
    amp_gate = (amp >= amp_thr)

    # velocity gate
    vel = s.diff()
    vel_std = vel.rolling(7, center=True, min_periods=1).std()
    z = vel / vel_std.replace(0, np.nan)
    vel_gate = (z >= z_thresh)

    gate = (amp_gate & vel_gate)
    n = len(gate)
    cutoff = int(max_frac * n) if n else 0

    run = 0
    for i, ok in enumerate(gate.fillna(False).to_numpy()):
        if ok:
            run += 1
            if run >= min_frames:
                return (i / float(fps)) if (i <= cutoff) else np.nan
        else:
            run = 0
    return np.nan


def _ue_le_delta_t_supine(df, fps,
                          sh_hold_norm=0.02, trunk_hold_deg=10.0, neck_hold_deg=10.0,
                          le_hip_hold_deg=15.0, le_knee_hold_deg=15.0,
                          ue_amp_thr=0.01, le_amp_thr_deg=5.0, zero_tol_s=1/12):
    """UE/LE onset timing delta for supine (different from prone)"""
    
    # UE proxy: pick most dynamic among shoulder_h, neck_flex, trunk_flex
    candidates, names = [], []
    if "shoulder_h" in df.columns:
        candidates.append(df["shoulder_h"])
        names.append("shoulder_h")
    if "neck_flex" in df.columns:
        candidates.append(df["neck_flex"])
        names.append("neck_flex")
    if "trunk_flex" in df.columns:
        candidates.append(df["trunk_flex"])
        names.append("trunk_flex")
    
    if not candidates:
        return np.nan
    
    var = [np.nanvar(pd.Series(c, dtype=float)) for c in candidates]
    ue_series = pd.Series(candidates[int(np.nanargmax(var))], dtype=float)

    # LE proxy: prefer hip flexion; fallback to knee if more dynamic
    if "hip_R" in df.columns and "hip_L" in df.columns:
        hip_mean = np.nanmean(df[["hip_R", "hip_L"]].to_numpy(), axis=1)
    else:
        hip_mean = np.array([np.nan] * len(df))
    
    if "knee_R" in df.columns and "knee_L" in df.columns:
        knee_mean = np.nanmean(df[["knee_R", "knee_L"]].to_numpy(), axis=1)
    else:
        knee_mean = np.array([np.nan] * len(df))
    
    hip_var = np.nanvar(hip_mean)
    knee_var = np.nanvar(knee_mean)
    le_series = pd.Series(hip_mean if hip_var >= knee_var else knee_mean, dtype=float)

    # held-at-start checks
    ue_held = _held_at_start(df.get("shoulder_h", ue_series), sh_hold_norm) or \
              _held_at_start(df.get("trunk_flex", ue_series), trunk_hold_deg) or \
              _held_at_start(df.get("neck_flex", ue_series), neck_hold_deg)
    le_held = _held_at_start(hip_mean, le_hip_hold_deg) or _held_at_start(knee_mean, le_knee_hold_deg)

    if ue_held and le_held:
        return 0.0
    if ue_held and not le_held:
        t_le = _onset_time_seconds(le_series, fps=fps, amp_thr=le_amp_thr_deg)
        return float(t_le) if pd.notna(t_le) else 0.0
    if (not ue_held) and le_held:
        t_ue = _onset_time_seconds(ue_series, fps=fps, amp_thr=ue_amp_thr)
        return -float(t_ue) if pd.notna(t_ue) else 0.0

    t_ue = _onset_time_seconds(ue_series, fps=fps, amp_thr=ue_amp_thr)
    t_le = _onset_time_seconds(le_series, fps=fps, amp_thr=le_amp_thr_deg)
    if pd.isna(t_ue) or pd.isna(t_le):
        return np.nan
    dt = float(t_le - t_ue)
    return 0.0 if abs(dt) < zero_tol_s else dt


def _chin_tuck_mask(df, fps, neck_thr_deg=12.0, nose_drop_frac=0.08):
    """Chin tuck present when neck_flex >= threshold AND nose->shoulder distance drops >= fraction"""
    if "nose_sh_dist" not in df.columns or "neck_flex" not in df.columns:
        return pd.Series([False] * len(df))
    
    base_nose = _baseline(df["nose_sh_dist"], n=12)
    drop_ok = (base_nose - df["nose_sh_dist"]) >= (nose_drop_frac * base_nose)
    return (df["neck_flex"] >= neck_thr_deg) & drop_ok


def _estimate_floor_y(P2, H=None):
    """Robust floor y-coordinate estimate"""
    ys = [P2[LM['L_AN'], 1], P2[LM['R_AN'], 1]]
    if P2.shape[0] >= 33:
        ys += [P2[29, 1], P2[30, 1], P2[31, 1], P2[32, 1]]
    y = np.array(ys, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H * 0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))


def _pelvis_width_xy(P2):
    """Pelvis width in pixels"""
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan


def measure_supine_flexion_video(video_path: str, smooth_k: int = 5, model_complexity: int = 1) -> Tuple[pd.DataFrame, float]:
    """Extract supine flexion metrics from video (comprehensive)"""
    if not isinstance(video_path, str) or not os.path.exists(video_path):
        return pd.DataFrame(), 30.0
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return pd.DataFrame(), 30.0
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or not (10 < fps < 120):
        fps = 30.0
    fps = float(fps)
    
    rows = []
    
    with mp_pose.Pose(model_complexity=model_complexity, min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            
            H, W = frame.shape[:2]
            res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if not res.pose_landmarks or not res.pose_world_landmarks:
                rows.append({col: np.nan for col in [
                    "neck_flex", "trunk_flex", "hip_R", "hip_L", "knee_R", "knee_L",
                    "shoulder_h", "nose_sh_dist", "y_floor", "pelvis_px", "sh_y", "wr_min_y"
                ]})
                continue
            
            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)

            # Centroids
            sh2 = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
            hp2 = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
            sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
            hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0

            # Head landmark (avg ears else nose)
            if np.isfinite(P3[LM['L_EAR']]).all() and np.isfinite(P3[LM['R_EAR']]).all():
                head3 = (P3[LM['L_EAR']] + P3[LM['R_EAR']]) / 2.0
            else:
                head3 = P3[LM['NOSE']]

            head2 = (P2[LM['L_EAR']] + P2[LM['R_EAR']]) / 2.0 if np.isfinite(P2[LM['L_EAR']]).all() and np.isfinite(P2[LM['R_EAR']]).all() else P2[LM['NOSE']]

            # Neck flexion (relative in 2D)
            neck_flex = min(angle_between_vecs(sh2 - hp2, head2 - sh2), 90.0) if np.isfinite(sh2).all() and np.isfinite(hp2).all() and np.isfinite(head2).all() else np.nan

            # Trunk flexion (shoulder vertex): 180° - ∠(Head, Shoulder, MidHip) in 3D
            tf_int = angle_3pt(head3, sh3, hp3)
            trunk_flex = max(0.0, 180.0 - tf_int) if np.isfinite(tf_int) else np.nan

            # Hip/Knee flexion (3-point, world)
            hip_R = max(0.0, 180.0 - angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])) if np.isfinite(angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])) else np.nan
            hip_L = max(0.0, 180.0 - angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])) if np.isfinite(angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])) else np.nan
            knee_R = max(0.0, 180.0 - angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])) if np.isfinite(angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])) else np.nan
            knee_L = max(0.0, 180.0 - angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])) if np.isfinite(angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])) else np.nan

            # Floor and scale
            y_floor = _estimate_floor_y(P2, H=H)
            px_scale = _pelvis_width_xy(P2)
            
            # Shoulder height (normalized)
            sh_h = (y_floor - float(sh2[1])) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan
            sh_h = max(sh_h, 0.0) if np.isfinite(sh_h) else np.nan

            # Chin-tuck proxy (nose -> shoulder distance)
            ns_dist = np.linalg.norm(P2[LM['NOSE']] - sh2) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan

            # Timing proxies
            sh_y = float(sh2[1])
            wr_min_y = float(min(P2[LM['L_WR'], 1], P2[LM['R_WR'], 1]))

            rows.append({
                "neck_flex": neck_flex,
                "trunk_flex": trunk_flex,
                "hip_R": hip_R,
                "hip_L": hip_L,
                "knee_R": knee_R,
                "knee_L": knee_L,
                "shoulder_h": sh_h,
                "nose_sh_dist": ns_dist,
                "y_floor": y_floor,
                "pelvis_px": px_scale,
                "sh_y": sh_y,
                "wr_min_y": wr_min_y
            })

    cap.release()
    df = pd.DataFrame(rows)

    # Smooth kinematic series (keep timing proxies raw)
    for k in ["neck_flex", "trunk_flex", "hip_R", "hip_L", "knee_R", "knee_L", "shoulder_h", "nose_sh_dist"]:
        if k in df.columns:
            df[k] = rolling_med(df[k].values, k=smooth_k)

    return df, fps


def extract_supine_flexion_metrics(video_path: str, age_years: int = 7) -> Dict[str, Any]:
    """Extract comprehensive metrics from supine flexion video"""
    df, fps = measure_supine_flexion_video(video_path)
    
    if df is None or len(df) < 10:
        return {"error": "Insufficient pose data"}
    
    # Choose reporting leg by larger median hip flexion
    medR = float(np.nanmedian(df.get("hip_R", pd.Series([]))))
    medL = float(np.nanmedian(df.get("hip_L", pd.Series([]))))
    leg_used = "R" if medR >= medL else "L"

    metrics = {}
    
    # Clip-level means (raw display)
    for col in ["neck_flex", "trunk_flex", "hip_R", "hip_L", "knee_R", "knee_L", "shoulder_h", "nose_sh_dist"]:
        if col in df.columns:
            mean_val = float(df[col].mean(skipna=True))
            metrics[f"{col}_mean"] = mean_val if np.isfinite(mean_val) else None
    
    # Scoring module expects these specific keys (with _deg suffix)
    metrics["neck_mean_deg"] = metrics.get("neck_flex_mean")
    metrics["trunk_mean_deg"] = metrics.get("trunk_flex_mean")
    
    # Use the active leg's hip/knee values for scoring
    if leg_used == "R":
        metrics["hip_mean_deg"] = metrics.get("hip_R_mean")
        metrics["knee_mean_deg"] = metrics.get("knee_R_mean")
    else:
        metrics["hip_mean_deg"] = metrics.get("hip_L_mean")
        metrics["knee_mean_deg"] = metrics.get("knee_L_mean")
    
    # Chin tuck
    ct_mask = _chin_tuck_mask(df, fps, neck_thr_deg=12.0, nose_drop_frac=0.08)
    metrics["chin_tuck_pct"] = float(ct_mask.mean()) if len(ct_mask) > 0 else None

    # UE/LE delta-t
    delta_t = _ue_le_delta_t_supine(df, fps,
                                     sh_hold_norm=0.02, trunk_hold_deg=10.0, neck_hold_deg=10.0,
                                     le_hip_hold_deg=15.0, le_knee_hold_deg=15.0,
                                     ue_amp_thr=0.01, le_amp_thr_deg=5.0)
    metrics["ue_le_delta_t_s"] = delta_t if pd.notna(delta_t) else None

    # Hold duration
    metrics["hold_duration_s"] = len(df) / fps if fps > 0 else len(df) / 30.0
    
    metrics["leg_used"] = leg_used
    metrics["fps"] = fps
    
    return metrics


def process_supine_flexion(
    video_path: Optional[str],
    age_years: int
) -> Dict[str, Any]:
    """Process supine flexion video and return scores"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_row_supine
    
    if not video_path or not os.path.exists(video_path):
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 35,
            "interpretation": "Error: No video provided"
        }
    
    # Handle MOV files - try to convert if needed
    video_path, video_err = ensure_video_readable(video_path)
    if video_err:
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 35,
            "interpretation": f"Error: {video_err}"
        }
    
    raw_metrics = extract_supine_flexion_metrics(video_path, age_years)
    
    if "error" in raw_metrics:
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 35,
            "interpretation": f"Error: {raw_metrics['error']}"
        }
    
    # Call scoring function with raw metrics
    score_result = score_row_supine(raw_metrics, age_years=age_years)
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k or k == "total_score"},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": 35,
        "interpretation": score_result.get("interpretation", "N/A")
    }
