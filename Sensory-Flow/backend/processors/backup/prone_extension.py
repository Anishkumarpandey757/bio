"""Prone Extension Processor - Side view required
Ported from: prone2_0.py
Calculates: neck/trunk/hip/knee angles, thigh lift height, 
UE/LE delta-t (onset timing), hold duration metrics
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

def _hip_extension_from_internal(a):
    """Convert internal hip angle to clinical extension angle"""
    if not np.isfinite(a):
        return np.nan
    return max(0.0, 180.0 - float(a))  # clinical hip extension 0..30


def _knee_flexion_from_internal(a):
    """Convert internal knee angle to clinical flexion angle"""
    if not np.isfinite(a):
        return np.nan
    return max(0.0, 180.0 - float(a))  # clinical knee flexion 0..13


def _angle_to_vertical(p1: np.ndarray, p2: np.ndarray) -> float:
    """Unsigned angle from vertical"""
    v = (p2 - p1).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8:
        return np.nan
    v /= n
    return float(np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0, -1.0])), -1, 1))))


def _pelvis_width_xy(P2):
    """Pelvis width in pixels"""
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan


def _estimate_floor_y(P2, H=None):
    """Estimate floor y-coordinate"""
    ys = [P2[LM['L_AN'], 1], P2[LM['R_AN'], 1]]
    if P2.shape[0] >= 33:
        ys += [P2[29, 1], P2[30, 1], P2[31, 1], P2[32, 1]]
    y = np.array(ys, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H * 0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))


def _baseline(x, n=12):
    """Median of the first n frames; robust when clips start near rest/hold"""
    x = pd.Series(x, dtype=float)
    return float(x.iloc[:max(3, n)].median(skipna=True))


def _held_at_start(metric_increasing_when_up, thr, n=12):
    """True if the first n frames are already above the 'hold' threshold"""
    x = pd.Series(metric_increasing_when_up, dtype=float)
    return bool((x.iloc[:max(3, n)] >= thr).sum() >= max(3, n) // 2)


def _onset_time_seconds(series_inc_up, fps, amp_thr, z_thresh=0.6, min_frames=3, max_frac=0.4, smooth_k=5):
    """
    Detect first sustained upward movement in a metric that INCREASES when the body part moves up.
    Combines amplitude gate (>= amp_thr above baseline) + velocity z-threshold.
    """
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


def _ue_le_delta_t_seconds(df, fps,
                           neck_hold_deg=15.0, trunk_hold_deg=5.0, thigh_hold_norm=0.05,
                           ue_amp_thr_deg=3.0, le_amp_thr_norm=0.02):
    """
    UE metric: prefer NECK angle; fallback to -wrist_y or -shoulder_y.
    LE metric: max(thigh_R, thigh_L) – increases with thigh lift.
    Returns delta-t between LE and UE onsets (s).
    """
    # --- UE series (increasing when up) ---
    ue_candidates = []
    if "neck" in df.columns:
        ue_candidates.append(df["neck"])
    if "wr_min_y" in df.columns:
        ue_candidates.append(-df["wr_min_y"])  # y↓ is up → negate
    if "sh_y" in df.columns:
        ue_candidates.append(-df["sh_y"])

    if not ue_candidates or not {"thigh_R", "thigh_L"}.issubset(df.columns):
        return np.nan

    # pick most dynamic UE proxy
    ue_stack = np.vstack([pd.Series(s, dtype=float).to_numpy() for s in ue_candidates])
    ue_series = ue_candidates[int(np.nanargmax(np.nanvar(ue_stack, axis=1)))]

    # LE series: max thigh height
    le_series = df[["thigh_R", "thigh_L"]].max(axis=1)

    # --- held-at-start checks ---
    ue_held = _held_at_start(ue_series, thr=neck_hold_deg) or _held_at_start(df.get("trunk", ue_series), thr=trunk_hold_deg)
    le_held = _held_at_start(le_series, thr=thigh_hold_norm)

    if ue_held and le_held:
        return 0.0
    if ue_held and not le_held:
        t_le = _onset_time_seconds(le_series, fps=fps, amp_thr=le_amp_thr_norm)
        return float(t_le) if pd.notna(t_le) else 0.0
    if (not ue_held) and le_held:
        t_ue = _onset_time_seconds(ue_series, fps=fps, amp_thr=ue_amp_thr_deg)
        return float(t_ue) if pd.notna(t_ue) else 0.0

    # neither held at t=0 → detect both
    t_ue = _onset_time_seconds(ue_series, fps=fps, amp_thr=ue_amp_thr_deg)
    t_le = _onset_time_seconds(le_series, fps=fps, amp_thr=le_amp_thr_norm)
    if pd.isna(t_ue) or pd.isna(t_le):
        return np.nan
    return float(t_le - t_ue)


def measure_prone_extension_video(video_path: str) -> Tuple[pd.DataFrame, float]:
    """Extract prone extension metrics from video (comprehensive - all metrics from original notebook)"""
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
    
    with mp_pose.Pose(model_complexity=1, min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            
            H, W = frame.shape[:2]
            res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if not res.pose_landmarks:
                rows.append({col: np.nan for col in [
                    "neck", "trunk", "hip_R", "hip_L", "knee_R", "knee_L",
                    "thigh_R", "thigh_L", "y_floor", "pelvis_px",
                    "sh_y", "wr_min_y", "an_min_y"
                ]})
                continue
            
            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.concatenate([P2, np.zeros((P2.shape[0], 1))], axis=1)

            # Neck and trunk angles (2D-based)
            sh2 = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
            hp2 = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
            head2 = (P2[LM['L_EAR']] + P2[LM['R_EAR']]) / 2.0

            neck_rel = angle_between_vecs(sh2 - hp2, head2 - sh2)
            neck_deg = min(neck_rel, 90.0) if np.isfinite(neck_rel) else np.nan
            trunk_deg = max(0.0, 90.0 - _angle_to_vertical(hp2, sh2))

            # Hip and knee angles (3D-based from world coords)
            hip_R = _hip_extension_from_internal(angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']]))
            hip_L = _hip_extension_from_internal(angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']]))
            knee_R = _knee_flexion_from_internal(angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']]))
            knee_L = _knee_flexion_from_internal(angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']]))

            # Floor and pelvis scale
            y_floor = _estimate_floor_y(P2, H=H)
            px_scale = _pelvis_width_xy(P2)

            # Thigh (distal 1/3) height - normalized by pelvis width
            hipR_xy, kneeR_xy = P2[LM['R_HP']], P2[LM['R_KN']]
            hipL_xy, kneeL_xy = P2[LM['L_HP']], P2[LM['L_KN']]
            distalR_xy = hipR_xy + (2.0 / 3.0) * (kneeR_xy - hipR_xy)
            distalL_xy = hipL_xy + (2.0 / 3.0) * (kneeL_xy - hipL_xy)

            thigh_R = (y_floor - distalR_xy[1]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan
            thigh_L = (y_floor - distalL_xy[1]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan
            thigh_R = max(thigh_R, 0.0) if np.isfinite(thigh_R) else np.nan
            thigh_L = max(thigh_L, 0.0) if np.isfinite(thigh_L) else np.nan

            # y-series for UE/LE onset timing
            sh_y = float(sh2[1])
            wr_min_y = float(min(P2[LM['L_WR'], 1], P2[LM['R_WR'], 1]))
            an_min_y = float(min(P2[LM['L_AN'], 1], P2[LM['R_AN'], 1]))

            rows.append({
                "neck": neck_deg,
                "trunk": trunk_deg,
                "hip_R": hip_R,
                "hip_L": hip_L,
                "knee_R": knee_R,
                "knee_L": knee_L,
                "thigh_R": thigh_R,
                "thigh_L": thigh_L,
                "y_floor": y_floor,
                "pelvis_px": px_scale,
                "sh_y": sh_y,
                "wr_min_y": wr_min_y,
                "an_min_y": an_min_y
            })

    cap.release()
    df = pd.DataFrame(rows)

    # Smooth kinematic series
    for k in ["neck", "trunk", "hip_R", "hip_L", "knee_R", "knee_L", "thigh_R", "thigh_L"]:
        if k in df.columns:
            df[k] = rolling_med(df[k].values, k=5)

    return df, fps


def extract_prone_extension_metrics(video_path: str, age_years: int = 7) -> Dict[str, Any]:
    """Extract comprehensive metrics from prone extension video (all metrics from original notebook)
    
    Output keys match scoring module expectations:
    - neck_mean_deg, trunk_mean_deg, hip_mean_deg, knee_mean_deg, hold_duration_s
    """
    df, fps = measure_prone_extension_video(video_path)
    
    if df is None or len(df) < 10:
        return {"error": "Insufficient pose data"}
    
    # Determine which leg was more lifted (for reporting and scoring)
    medR = float(np.nanmedian(df.get("thigh_R", pd.Series([]))))
    medL = float(np.nanmedian(df.get("thigh_L", pd.Series([]))))
    leg_used = "R" if medR >= medL else "L"

    metrics = {}
    
    # Clip-level means for all columns (for raw display)
    for col in ["neck", "trunk", "hip_R", "hip_L", "knee_R", "knee_L", "thigh_R", "thigh_L"]:
        if col in df.columns:
            mean_val = float(df[col].mean(skipna=True))
            metrics[f"{col}_mean"] = mean_val if np.isfinite(mean_val) else None
    
    # Scoring module expects these specific keys (with _deg suffix)
    # Use the lifted leg's values for hip/knee
    metrics["neck_mean_deg"] = metrics.get("neck_mean")
    metrics["trunk_mean_deg"] = metrics.get("trunk_mean")
    
    # Use the active leg's hip/knee values for scoring
    if leg_used == "R":
        metrics["hip_mean_deg"] = metrics.get("hip_R_mean")
        metrics["knee_mean_deg"] = metrics.get("knee_R_mean")
    else:
        metrics["hip_mean_deg"] = metrics.get("hip_L_mean")
        metrics["knee_mean_deg"] = metrics.get("knee_L_mean")
    
    # Hold duration
    metrics["hold_duration_s"] = len(df) / fps if fps > 0 else len(df) / 30.0

    # UE/LE delta-t (onset timing)
    delta_t = _ue_le_delta_t_seconds(df, fps, 
                                      neck_hold_deg=15.0, trunk_hold_deg=5.0,
                                      thigh_hold_norm=0.05,
                                      ue_amp_thr_deg=3.0, le_amp_thr_norm=0.02)
    metrics["ue_le_delta_t_s"] = delta_t if pd.notna(delta_t) else None

    metrics["leg_used"] = leg_used
    metrics["fps"] = fps
    
    return metrics


def process_prone_extension(
    video_path: Optional[str],
    age_years: int
) -> Dict[str, Any]:
    """Process prone extension video and return scores"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_row_prone
    
    if not video_path or not os.path.exists(video_path):
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": "Error: No video provided"
        }
    
    # Handle MOV files - try to convert if needed
    video_path, video_err = ensure_video_readable(video_path)
    if video_err:
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": f"Error: {video_err}"
        }
    
    raw_metrics = extract_prone_extension_metrics(video_path, age_years)
    
    if "error" in raw_metrics:
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": f"Error: {raw_metrics['error']}"
        }
    
    # Call scoring function with raw metrics
    score_result = score_row_prone(raw_metrics, age_years=age_years)
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k or k == "total_score"},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": score_result.get("max_score", 36),
        "interpretation": score_result.get("interpretation", "N/A")
    }
