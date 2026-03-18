"""
One Leg Standing (OLS) Processor - Eyes Open and Eyes Closed variants
Ported from: ols_leftleg_eo.py, ols_leftleg_ec.py, ols_rightleg_*.py
Requires BOTH front and side view videos for complete assessment.

Metrics extracted (comprehensive):
- Sway: mediolateral (SS) & anteroposterior (AP) means and SDs
- Foot drift: max/mean displacement (cm), lateral/AP components, pelvis-normalized
- Toe touches: count of near-floor events
- Foot touches (ankle): contact transitions
- Hands off hips: count and percentage
- Neck metrics: mean, SD, peak angles
- Strategy classification: Stepping/Knee/Hip/Ankle
"""

import os
import cv2
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple

import mediapipe as mp
mp_pose = mp.solutions.pose

from .common import (
    LM, rolling_med, pelvis_width_xy, estimate_floor_y, angle_3pt, angle_between_vecs, detect_view_from_video
)


def _angle_signed_to_vertical(p1: np.ndarray, p2: np.ndarray) -> float:
    """Signed trunk angle (deg) vs vertical; + = lean to image +x (right), - = to -x (left).
    Matches Colab implementation exactly using arccos of dot product with upward vector [0,-1]."""
    v = (p2 - p1).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8:
        return np.nan
    v = v / n  # normalize
    # Unsigned angle from vertical (upward direction [0, -1] in image coords)
    unsigned = float(np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0, -1.0])), -1.0, 1.0))))
    # Sign based on x-component (lean direction)
    sgn = 1.0 if v[0] >= 0 else -1.0
    return sgn * unsigned


def _angle_to_vertical(p1: np.ndarray, p2: np.ndarray) -> float:
    """Unsigned angle from vertical"""
    v = (p2 - p1).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8:
        return np.nan
    v /= n
    return float(np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0, -1.0])), -1, 1))))


def _neck_goniometer_deg(P3, LM) -> float:
    """Goniometer-like cervical angle (deg) = angle between trunk and head vectors"""
    sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
    hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
    ear3 = (P3[LM['L_EAR']] + P3[LM['R_EAR']]) / 2.0
    trunk = sh3 - hp3
    head = ear3 - sh3
    return angle_between_vecs(trunk, head)


def _count_toe_touches(toe_h: np.ndarray, fps: float, norm_thr: float = 0.03, 
                       min_frames: int = 3, min_gap_s: float = 0.30) -> int:
    """Count toe touches with minimum gap between them (original notebook logic)"""
    near = toe_h <= norm_thr
    run, touch_idxs = 0, []
    for i, ok in enumerate(near):
        if ok and np.isfinite(toe_h[i]):
            run += 1
            if run == min_frames:
                touch_idxs.append(i)
        else:
            run = 0
    
    if fps <= 0:
        fps = 30.0
    refr = int(fps * min_gap_s)
    cnt, last = 0, -10**9
    for i in touch_idxs:
        if i - last >= refr:
            cnt += 1
            last = i
    return int(cnt)


def _count_transitions(boolean_series, min_gap_frames=6) -> int:
    """Count rising edges True with simple debounce"""
    b = pd.Series(boolean_series, dtype=bool).fillna(False).to_numpy()
    cnt = 0
    cool = 0
    for i in range(1, len(b)):
        if cool > 0:
            cool -= 1
            continue
        if (not b[i-1]) and b[i]:
            cnt += 1
            cool = min_gap_frames
    return int(cnt)


def measure_ols_video(
    video_path: str, 
    view: str = "front",
    raised_leg: str = "L",
    smooth_k: int = 5,
    model_complexity: int = 1
) -> Tuple[pd.DataFrame, float]:
    """Extract OLS kinematic parameters from video (comprehensive - all metrics from original notebook)."""
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
    
    with mp_pose.Pose(
        model_complexity=model_complexity,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as pose:
        
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            
            H, W = frame.shape[:2]
            res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if not res.pose_landmarks:
                rows.append({col: np.nan for col in [
                    "trunk_signed_deg", "trunk_abs_deg", "neck_deg",
                    "hip_R", "hip_L", "knee_R", "knee_L",
                    "raised_ank_h", "raised_toe_h",
                    "wristL_hipL_norm", "wristR_hipR_norm",
                    "x29", "y29", "x30", "y30", "x31", "y31", "x32", "y32",  # heels/toes
                    "x23", "y23", "x24", "y24", "y_floor", "pelvis_px"  # hips + floor info
                ]})
                continue
            
            # 2D (pixel) and 3D (world) coordinates
            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.concatenate([P2, np.zeros((P2.shape[0], 1))], axis=1)
            
            # Core sway measurements
            sh2 = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
            hp2 = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
            
            trunk_signed = _angle_signed_to_vertical(hp2, sh2)
            trunk_abs = abs(trunk_signed)
            
            # 3D neck goniometer angle (angle between trunk and head vectors)
            sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
            hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
            ear3 = (P3[LM['L_EAR']] + P3[LM['R_EAR']]) / 2.0
            trunk_vec = sh3 - hp3
            head_vec = ear3 - sh3
            num = np.dot(trunk_vec, head_vec)
            den = (np.linalg.norm(trunk_vec) * np.linalg.norm(head_vec)) + 1e-8
            c = np.clip(num / den, -1.0, 1.0)
            neck_deg = float(np.degrees(np.arccos(c)))
            
            # Hip/Knee angles (3D) - converted to clinical angles using 180 - angle
            # Original notebook formula: 180.0 - angle_3pt(shoulder, hip, knee) for hip flexion
            hip_R = 180.0 - angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])
            hip_L = 180.0 - angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])
            knee_R = 180.0 - angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])
            knee_L = 180.0 - angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])
            
            # Floor and scale
            y_floor = estimate_floor_y(P2, H=H)
            px_scale = pelvis_width_xy(P2)
            
            # Raised limb heights
            ankL_y = float(P2[LM['L_AN'], 1])
            ankR_y = float(P2[LM['R_AN'], 1])
            toeL_y = float(P2[31, 1]) if P2.shape[0] >= 33 else np.nan
            toeR_y = float(P2[32, 1]) if P2.shape[0] >= 33 else np.nan
            
            def _nh(y):
                if not np.isfinite(y) or not np.isfinite(y_floor) or not np.isfinite(px_scale) or px_scale <= 0:
                    return np.nan
                return max((y_floor - y) / px_scale, 0.0)
            
            if raised_leg.upper() == "L":
                raised_ank_h = _nh(ankL_y)
                raised_toe_h = _nh(toeL_y)
            else:
                raised_ank_h = _nh(ankR_y)
                raised_toe_h = _nh(toeR_y)
            
            # Wrist-hip distances (normalized)
            wristL_norm = np.linalg.norm(P2[LM['L_WR']] - P2[LM['L_HP']]) / (px_scale if np.isfinite(px_scale) and px_scale > 0 else 1.0)
            wristR_norm = np.linalg.norm(P2[LM['R_WR']] - P2[LM['R_HP']]) / (px_scale if np.isfinite(px_scale) and px_scale > 0 else 1.0)
            
            # Heel and toe coordinates (for foot drift)
            x29, y29 = float(P2[29, 0]) if P2.shape[0] >= 30 else np.nan, float(P2[29, 1]) if P2.shape[0] >= 30 else np.nan
            x30, y30 = float(P2[30, 0]) if P2.shape[0] >= 31 else np.nan, float(P2[30, 1]) if P2.shape[0] >= 31 else np.nan
            x31, y31 = float(P2[31, 0]) if P2.shape[0] >= 32 else np.nan, float(P2[31, 1]) if P2.shape[0] >= 32 else np.nan
            x32, y32 = float(P2[32, 0]) if P2.shape[0] >= 33 else np.nan, float(P2[32, 1]) if P2.shape[0] >= 33 else np.nan
            
            # Hip coordinates (for pelvis width validation)
            x23, y23 = float(P2[LM['L_HP'], 0]), float(P2[LM['L_HP'], 1])
            x24, y24 = float(P2[LM['R_HP'], 0]), float(P2[LM['R_HP'], 1])
            
            rows.append({
                "trunk_signed_deg": trunk_signed,
                "trunk_abs_deg": trunk_abs,
                "neck_deg": neck_deg,
                "hip_R": hip_R,
                "hip_L": hip_L,
                "knee_R": knee_R,
                "knee_L": knee_L,
                "raised_ank_h": raised_ank_h,
                "raised_toe_h": raised_toe_h,
                "wristL_hipL_norm": wristL_norm,
                "wristR_hipR_norm": wristR_norm,
                "x29": x29, "y29": y29,  # left heel
                "x30": x30, "y30": y30,  # right heel
                "x31": x31, "y31": y31,  # left toe
                "x32": x32, "y32": y32,  # right toe
                "x23": x23, "y23": y23,  # left hip
                "x24": x24, "y24": y24,  # right hip
                "y_floor": y_floor,
                "pelvis_px": px_scale
            })
    
    cap.release()
    df = pd.DataFrame(rows)
    
    # Smooth key kinematic series (from original notebook)
    for k in ["trunk_signed_deg", "trunk_abs_deg", "neck_deg", "hip_R", "hip_L", 
              "knee_R", "knee_L", "raised_ank_h", "raised_toe_h", "wristL_hipL_norm", "wristR_hipR_norm"]:
        if k in df.columns:
            df[k] = rolling_med(df[k].values, k=smooth_k)
    
    return df, fps


def summarize_ols_clip(df: pd.DataFrame, fps: float) -> Dict[str, Any]:
    """Calculate sway summary statistics from DF"""
    sway_abs = pd.Series(df["trunk_abs_deg"], dtype=float)
    
    mean_deg = float(sway_abs.mean()) if len(sway_abs.dropna()) > 0 else np.nan
    sd_deg = float(sway_abs.std(ddof=0)) if len(sway_abs.dropna()) > 0 else np.nan
    
    return {"sway_mean_deg": mean_deg, "sway_sd_deg": sd_deg}


def _supporting_foot_xy(df: pd.DataFrame, raised_leg="L"):
    """Midpoint of heel & big-toe of the supporting foot (opposite to raised_leg)."""
    if raised_leg.upper() == "L":
        # stance = RIGHT foot
        if not {"x30", "y30", "x32", "y32"}.issubset(df.columns):
            return None
        heel = df[["x30", "y30"]].to_numpy()  # RIGHT_HEEL
        toe = df[["x32", "y32"]].to_numpy()   # RIGHT_TOE
    else:
        # stance = LEFT foot
        if not {"x29", "y29", "x31", "y31"}.issubset(df.columns):
            return None
        heel = df[["x29", "y29"]].to_numpy()  # LEFT_HEEL
        toe = df[["x31", "y31"]].to_numpy()   # LEFT_TOE
    return 0.5 * (heel + toe)


def _stance_ball_xy(df: pd.DataFrame, raised_leg: str = "L", alpha: float = 0.30):
    """Returns (N,2) array for the BALL of the supporting foot"""
    rl = (raised_leg or "L").upper()
    if rl == "L":
        # stance = RIGHT (RIGHT_HEEL=30, RIGHT_TOE=32)
        need = {"x30", "y30", "x32", "y32"}
        if not need.issubset(df.columns):
            return None
        heel = df[["x30", "y30"]].to_numpy(dtype=float)
        toe = df[["x32", "y32"]].to_numpy(dtype=float)
    else:
        # stance = LEFT (LEFT_HEEL=29, LEFT_TOE=31)
        need = {"x29", "y29", "x31", "y31"}
        if not need.issubset(df.columns):
            return None
        heel = df[["x29", "y29"]].to_numpy(dtype=float)
        toe = df[["x31", "y31"]].to_numpy(dtype=float)
    return toe + alpha * (heel - toe)


def _foot_drift_metrics(df: pd.DataFrame, raised_leg: str = "L", 
                        px_per_cm: Optional[float] = None) -> Dict[str, Any]:
    """Foot Drift Displacement metrics (stance foot) - from original notebook"""
    ball = _stance_ball_xy(df, raised_leg=raised_leg, alpha=0.30)
    if ball is None or len(ball) == 0:
        return dict(
            drift_max_cm=None, drift_mean_cm=None,
            drift_max_px=None, drift_mean_px=None,
            drift_lat_max_cm=None, drift_lat_mean_cm=None,
            drift_ap_max_cm=None, drift_ap_mean_cm=None,
            drift_pelvis_max=None, drift_pelvis_mean=None
        )

    # Robust starting point: median of first up-to-10 frames
    k0 = min(10, len(ball))
    start = np.nanmedian(ball[:k0], axis=0)

    # Total and component drifts (pixels)
    delta = ball - start
    drift_px = np.linalg.norm(delta, axis=1)
    drift_lat_px = np.abs(delta[:, 0])
    drift_ap_px = np.abs(delta[:, 1])

    # Pelvis width for normalization
    if {"x23", "y23", "x24", "y24"}.issubset(df.columns):
        LHP = df[["x23", "y23"]].to_numpy(dtype=float)
        RHP = df[["x24", "y24"]].to_numpy(dtype=float)
        pelvis_px = float(np.nanmedian(np.linalg.norm(LHP - RHP, axis=1)))
    else:
        pelvis_px = np.nan

    def _to_cm(arr_px):
        return (arr_px / px_per_cm) if (px_per_cm and px_per_cm > 0) else None

    # Return all metrics (cm and px versions)
    return dict(
        drift_max_px=float(np.nanmax(drift_px)),
        drift_mean_px=float(np.nanmean(drift_px)),
        drift_max_cm=float(np.nanmax(_to_cm(drift_px))) if _to_cm(drift_px) is not None else None,
        drift_mean_cm=float(np.nanmean(_to_cm(drift_px))) if _to_cm(drift_px) is not None else None,
        drift_lat_max_cm=float(np.nanmax(_to_cm(drift_lat_px))) if _to_cm(drift_lat_px) is not None else None,
        drift_lat_mean_cm=float(np.nanmean(_to_cm(drift_lat_px))) if _to_cm(drift_lat_px) is not None else None,
        drift_ap_max_cm=float(np.nanmax(_to_cm(drift_ap_px))) if _to_cm(drift_ap_px) is not None else None,
        drift_ap_mean_cm=float(np.nanmean(_to_cm(drift_ap_px))) if _to_cm(drift_ap_px) is not None else None,
        drift_pelvis_max=float(np.nanmax(drift_px / pelvis_px)) if np.isfinite(pelvis_px) and pelvis_px > 0 else None,
        drift_pelvis_mean=float(np.nanmean(drift_px / pelvis_px)) if np.isfinite(pelvis_px) and pelvis_px > 0 else None,
    )


def _summarize_neck(df: pd.DataFrame) -> Dict[str, float]:
    """Clip-level neck angle stats (deg) from original notebook"""
    s = pd.Series(df.get("neck_deg", np.nan), dtype=float)
    s = s[np.isfinite(s)]
    
    return dict(
        neck_mean_deg=float(s.mean()) if len(s) > 0 else None,
        neck_sd_deg=float(s.std(ddof=0)) if len(s) > 0 else None,
        neck_peak_deg=float(s.max()) if len(s) > 0 else None
    )


def _ols_events_and_strategy(df: pd.DataFrame, fps: float, raised_leg: str = "L", age_tag: str = "7yrs",
                             ank_up: float = 0.15, ank_down: float = 0.05,
                             min_contact_gap_frames: int = 8,
                             onhip_thr: float = 0.35, min_off_gap_frames: int = 6) -> Dict[str, Any]:
    """Foot touches, toe touches, hands off hips, and balance strategy from original notebook"""
    
    # ---- Ankle-based contact count (airborne↔grounded transitions) ----
    ank = pd.Series(df.get("raised_ank_h", np.nan), dtype=float)
    up = ank > ank_up
    down = ank < ank_down
    grounded = pd.Series(False, index=ank.index)
    state = True if (len(down) and bool(down.iloc[0])) else False
    grounded.iloc[0] = state
    
    for i in range(1, len(ank)):
        if state:  # grounded
            if up.iloc[i]:
                state = False
        else:  # airborne
            if down.iloc[i]:
                state = True
        grounded.iloc[i] = state
    
    foot_touches_ankle = _count_transitions(grounded.diff().fillna(0) > 0, min_gap_frames=min_contact_gap_frames)

    # ---- Toe-touch count (age-tuned threshold) ----
    toe_thr = 0.035 if age_tag == "6yrs" else 0.025
    toe_touches = _count_toe_touches(
        df.get("raised_toe_h", np.array([])).values if "raised_toe_h" in df.columns else np.array([]), 
        fps, norm_thr=toe_thr, min_frames=3,
        min_gap_s=0.35 if age_tag == "6yrs" else 0.30
    )

    # ---- Hands off hips count ----
    onL = pd.Series(df.get("wristL_hipL_norm", np.nan), dtype=float) <= onhip_thr
    onR = pd.Series(df.get("wristR_hipR_norm", np.nan), dtype=float) <= onhip_thr
    both_on = (onL & onR)
    hands_off = ~both_on
    hands_off_cnt = _count_transitions(hands_off, min_gap_frames=min_off_gap_frames)
    hands_off_pct = float(hands_off.mean()) if len(hands_off) > 0 else 0.0

    # ---- Strategy (medians while airborne to avoid contact artifacts) ----
    airborne = ~grounded
    
    def _med(series_name):
        s = df.loc[airborne, series_name] if airborne.any() and series_name in df.columns else df.get(series_name, pd.Series([]))
        s = pd.Series(s, dtype=float)
        return float(s.median()) if len(s) > 0 else np.nan

    med_trunk = _med("trunk_abs_deg")
    
    hip_data = pd.concat([df.get("hip_L", pd.Series()), df.get("hip_R", pd.Series())], axis=1)
    med_hip = float(hip_data.median().median()) if len(hip_data) > 0 else np.nan
    
    knee_data = pd.concat([df.get("knee_L", pd.Series()), df.get("knee_R", pd.Series())], axis=1)
    med_knee = float(knee_data.median().median()) if len(knee_data) > 0 else np.nan

    if foot_touches_ankle > 0 or toe_touches > 0:
        strategy = "Stepping"
    elif np.isfinite(med_knee) and med_knee >= 15 and np.isfinite(med_trunk) and med_trunk < 10:
        strategy = "Knee strategy"
    elif np.isfinite(med_hip) and med_hip >= 15 and np.isfinite(med_trunk) and med_trunk >= 7:
        strategy = "Hip strategy"
    else:
        strategy = "Ankle/minimal"

    return dict(
        foot_touches_ankle=int(foot_touches_ankle),
        toe_touches=int(toe_touches),
        hands_off_cnt=int(hands_off_cnt),
        hands_off_pct=hands_off_pct,
        strategy=strategy,
        med_trunk_deg=med_trunk,
        med_hip_deg=med_hip,
        med_knee_deg=med_knee
    )


def extract_ols_metrics(
    front_video_path: Optional[str] = None,
    side_video_path: Optional[str] = None,
    raised_leg: str = "L",
    age_tag: str = "7yrs",
    px_per_cm: Optional[float] = 3.2
) -> Dict[str, Any]:
    """Extract comprehensive OLS metrics from front and side videos (all metrics from original notebook)."""
    
    metrics = {
        # Sway metrics
        "sway_SS_mean": None, "sway_SS_SD": None,
        "sway_AP_mean": None, "sway_AP_SD": None,
        # Foot drift metrics
        "drift_max_cm": None, "drift_mean_cm": None,
        "drift_lat_max_cm": None, "drift_lat_mean_cm": None,
        "drift_ap_max_cm": None, "drift_ap_mean_cm": None,
        # Neck metrics
        "neck_mean_deg": None, "neck_sd_deg": None, "neck_peak_deg": None,
        # Event metrics
        "toe_touches": None, "foot_touches": None, "hands_off_cnt": None, "hands_off_pct": None,
        # Strategy
        "balance_strategy": None,
        # Supporting metrics
        "med_trunk_deg": None, "med_hip_deg": None, "med_knee_deg": None,
        "fps": 30.0,
        # View detection results
        "front_view_detection": None,
        "side_view_detection": None,
        "view_warnings": []
    }
    
    warnings = []
    
    # Auto-detect views and sanity check
    if front_video_path and os.path.exists(front_video_path):
        front_detection = detect_view_from_video(front_video_path)
        metrics["front_view_detection"] = front_detection
        
        if front_detection["detected_view"] == "side" and front_detection["confidence"] > 0.6:
            warnings.append(f"FRONT video appears to be SIDE view (confidence: {front_detection['confidence']:.0%}). Videos may be swapped.")
        elif front_detection["detected_view"] == "unknown":
            warnings.append(f"Could not detect view type for FRONT video: {front_detection['details']}")
    
    if side_video_path and os.path.exists(side_video_path):
        side_detection = detect_view_from_video(side_video_path)
        metrics["side_view_detection"] = side_detection
        
        if side_detection["detected_view"] == "front" and side_detection["confidence"] > 0.6:
            warnings.append(f"SIDE video appears to be FRONT view (confidence: {side_detection['confidence']:.0%}). Videos may be swapped.")
        elif side_detection["detected_view"] == "unknown":
            warnings.append(f"Could not detect view type for SIDE video: {side_detection['details']}")
    
    metrics["view_warnings"] = warnings
    
    if front_video_path and os.path.exists(front_video_path):
        df_front, fps_front = measure_ols_video(front_video_path, view="front", raised_leg=raised_leg)
        
        if df_front is not None and len(df_front) > 10:
            # Sway metrics
            summ = summarize_ols_clip(df_front, fps_front)
            metrics["sway_SS_mean"] = summ.get("sway_mean_deg")
            metrics["sway_SS_SD"] = summ.get("sway_sd_deg")
            metrics["fps"] = fps_front
            
            # Neck metrics
            neck_stats = _summarize_neck(df_front)
            metrics["neck_mean_deg"] = neck_stats.get("neck_mean_deg")
            metrics["neck_sd_deg"] = neck_stats.get("neck_sd_deg")
            metrics["neck_peak_deg"] = neck_stats.get("neck_peak_deg")
            
            # Events and strategy
            thr_deg = 0.035 if age_tag == "6yrs" else 0.025
            events = _ols_events_and_strategy(df_front, fps_front, raised_leg=raised_leg, age_tag=age_tag)
            metrics["toe_touches"] = events.get("toe_touches")
            metrics["foot_touches"] = events.get("foot_touches_ankle")
            metrics["hands_off_cnt"] = events.get("hands_off_cnt")
            metrics["hands_off_pct"] = events.get("hands_off_pct")
            metrics["balance_strategy"] = events.get("strategy")
            metrics["med_trunk_deg"] = events.get("med_trunk_deg")
            metrics["med_hip_deg"] = events.get("med_hip_deg")
            metrics["med_knee_deg"] = events.get("med_knee_deg")
            
            # Foot drift (from front view which has more lateral info)
            drift = _foot_drift_metrics(df_front, raised_leg=raised_leg, px_per_cm=px_per_cm)
            metrics["drift_max_cm"] = drift.get("drift_max_cm")
            metrics["drift_mean_cm"] = drift.get("drift_mean_cm")
            metrics["drift_lat_max_cm"] = drift.get("drift_lat_max_cm")
            metrics["drift_lat_mean_cm"] = drift.get("drift_lat_mean_cm")
            metrics["drift_ap_max_cm"] = drift.get("drift_ap_max_cm")
            metrics["drift_ap_mean_cm"] = drift.get("drift_ap_mean_cm")
    
    if side_video_path and os.path.exists(side_video_path):
        df_side, fps_side = measure_ols_video(side_video_path, view="side", raised_leg=raised_leg)
        
        if df_side is not None and len(df_side) > 10:
            # Sway metrics (AP from side view)
            summ = summarize_ols_clip(df_side, fps_side)
            metrics["sway_AP_mean"] = summ.get("sway_mean_deg")
            metrics["sway_AP_SD"] = summ.get("sway_sd_deg")
    
    return metrics


def process_one_leg_standing(
    front_video_path: Optional[str],
    side_video_path: Optional[str],
    age_years: int,
    eyes_open: bool = True,
    raised_leg: str = "L"
) -> Dict[str, Any]:
    """Process OLS videos and return scores."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_ols
    
    age_tag = "6yrs" if age_years == 6 else "7yrs"
    raw_metrics = extract_ols_metrics(front_video_path, side_video_path, raised_leg, age_tag)
    
    # Extract view warnings for interpretation
    view_warnings = raw_metrics.get("view_warnings", [])
    
    if raw_metrics["sway_SS_mean"] is None and raw_metrics["sway_AP_mean"] is None:
        error_msg = "Error: No valid pose data extracted"
        if view_warnings:
            error_msg += ". View warnings: " + "; ".join(view_warnings)
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": error_msg
        }
    
    score_result = score_ols(raw_metrics, age_years=age_years, eyes_open=eyes_open, raised_leg=raised_leg)
    
    # Build interpretation with view warnings
    interpretation = score_result.get("interpretation", "N/A")
    if view_warnings:
        interpretation = "VIEW WARNING: " + "; ".join(view_warnings) + " | " + interpretation
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": 34,
        "interpretation": interpretation,
        "eyesOpen": eyes_open,
        "raisedLeg": raised_leg,
        "viewWarnings": view_warnings
    }
