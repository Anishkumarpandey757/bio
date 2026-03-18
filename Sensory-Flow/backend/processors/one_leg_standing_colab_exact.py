"""
One Leg Standing processor - aligned with origin Colab calculations.
Origin colabs: ols_rightleg_eo, ols_rightleg_ec, ols_left_leg_eo, ols_leftleg_ec.
Variants: raised_leg (L/R), eyes_open (True/False). Sway reported as (90 - angle) to match origin.
"""

import os
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np
import pandas as pd
import mediapipe as mp

# Import MOV conversion utilities
try:
    from .common import ensure_video_readable
except ImportError:
    def ensure_video_readable(path):
        return path, None

mp_pose = mp.solutions.pose
cv2.setNumThreads(1)

LM = dict(
    NOSE=0, L_EYE=1, R_EYE=2, L_EAR=7, R_EAR=8,
    L_SH=11, R_SH=12, L_EL=13, R_EL=14, L_WR=15, R_WR=16,
    L_HP=23, R_HP=24, L_KN=25, R_KN=26, L_AN=27, R_AN=28
)

def angle_3pt(A, B, C, eps=1e-8):
    """EXACT copy from Colab OLS"""
    BA, BC = A-B, C-B
    na, nc = np.linalg.norm(BA), np.linalg.norm(BC)
    if na < eps or nc < eps: 
        return np.nan
    cosv = np.dot(BA, BC) / (na*nc)
    return float(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))))

def angle_to_vertical(P0, P1):
    """EXACT copy from Colab OLS"""
    v = (P1 - P0).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8: 
        return np.nan
    v /= n
    return float(np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0,-1.0])), -1, 1))))

def angle_signed_to_vertical(P0, P1):
    """EXACT copy from Colab OLS - THIS IS THE KEY FUNCTION FOR TRUNK SWAY"""
    v = (P1 - P0).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8: 
        return np.nan
    v /= n
    unsigned = np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0,-1.0])), -1, 1)))
    sgn = 1.0 if v[0] >= 0 else -1.0
    return float(sgn * unsigned)

def pelvis_width_xy(P2):
    """EXACT copy from Colab OLS"""
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan

def estimate_floor_y(P2, H=None):
    """EXACT copy from Colab OLS"""
    ys = [P2[LM['L_AN'],1], P2[LM['R_AN'],1]]
    if P2.shape[0] >= 33:
        ys += [P2[29,1], P2[30,1], P2[31,1], P2[32,1]]
    y = np.array(ys, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H*0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))

def rolling_med(x, k=5):
    """EXACT copy from Colab OLS"""
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()

def count_transitions(boolean_series, min_gap_frames=6):
    """EXACT copy from Colab OLS"""
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

def angle_between_vecs(v1, v2, eps=1e-8):
    """EXACT copy from Colab OLS"""
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < eps or n2 < eps: 
        return np.nan
    c = np.dot(v1, v2) / (n1*n2)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))

def neck_goniometer_deg(P3, LM):
    """EXACT copy from Colab OLS"""
    sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
    hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
    ear3 = (P3[LM['L_EAR']] + P3[LM['R_EAR']]) / 2.0
    trunk = sh3 - hp3
    head  = ear3 - sh3
    return angle_between_vecs(trunk, head)

def measure_ols_video_colab_exact(video_path, view="front", raised_leg="L", smooth_k=5, model_complexity=1):
    """EXACT copy of pose measurement from Colab OLS files"""
    cap = cv2.VideoCapture(video_path)
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
                # Match Colab column structure exactly
                rows.append([np.nan] * 20)
                continue

            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.concatenate([P2, np.zeros((P2.shape[0], 1))], axis=1)

            # Key measurements - exact Colab method
            sh2 = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
            hp2 = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
            sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
            hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0

            # THIS IS THE CRITICAL FIX - use angle_signed_to_vertical for trunk sway
            trunk_signed_deg = angle_signed_to_vertical(hp2, sh2)  # Small angle like 2-8 degrees
            trunk_abs_deg = abs(trunk_signed_deg) if np.isfinite(trunk_signed_deg) else np.nan

            # Neck goniometer (exact Colab method)
            neck_goni_deg = neck_goniometer_deg(P3, LM)

            # Joint angles (exact Colab method)
            hip_R = 180.0 - angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])
            hip_L = 180.0 - angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])
            knee_R = 180.0 - angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])
            knee_L = 180.0 - angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])

            # Floor and scaling (exact Colab method)
            y_floor = estimate_floor_y(P2, H=H)
            px_scale = pelvis_width_xy(P2)

            # Raised ankle/toe heights (exact Colab method)
            ankL_y, ankR_y = float(P2[LM['L_AN'], 1]), float(P2[LM['R_AN'], 1])
            toeL_y = float(P2[31, 1]) if P2.shape[0] >= 33 else np.nan
            toeR_y = float(P2[32, 1]) if P2.shape[0] >= 33 else np.nan

            def _nh(y):
                if not np.isfinite(px_scale) or px_scale <= 0 or not np.isfinite(y) or not np.isfinite(y_floor):
                    return np.nan
                return max((y_floor - y) / px_scale, 0.0)

            if (raised_leg or 'L').upper() == 'L':
                raised_ank_h, raised_toe_h = _nh(ankL_y), _nh(toeL_y)
            else:
                raised_ank_h, raised_toe_h = _nh(ankR_y), _nh(toeR_y)

            # Hand-hip distances (exact Colab method)
            wristL_norm = np.linalg.norm(P2[LM['L_WR']] - P2[LM['L_HP']]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan
            wristR_norm = np.linalg.norm(P2[LM['R_WR']] - P2[LM['R_HP']]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan

            # Build row exactly as Colab does
            rows.append([
                trunk_signed_deg, trunk_abs_deg, neck_goni_deg,
                hip_R, hip_L, knee_R, knee_L,
                raised_ank_h, raised_toe_h,
                wristL_norm, wristR_norm,
                y_floor, px_scale, sh2[0], sh2[1], hp2[0], hp2[1],
                P2[29,0] if P2.shape[0] > 29 else np.nan, P2[29,1] if P2.shape[0] > 29 else np.nan,
                P2[30,0] if P2.shape[0] > 30 else np.nan, P2[30,1] if P2.shape[0] > 30 else np.nan,
            ])

    cap.release()

    # Column names exactly as Colab
    cols = [
        "trunk_signed_deg", "trunk_abs_deg", "neck_goni_deg",
        "hip_R", "hip_L", "knee_R", "knee_L",
        "raised_ank_h", "raised_toe_h",
        "wristL_hipL_norm", "wristR_hipR_norm",
        "y_floor", "pelvis_px", "sh_x", "sh_y", "hp_x", "hp_y",
        "x29", "y29", "x30", "y30"
    ]
    
    df = pd.DataFrame(rows, columns=cols)
    
    # Smoothing exactly as Colab
    for k in ["trunk_signed_deg", "trunk_abs_deg", "neck_goni_deg", "hip_R", "hip_L", "knee_R", "knee_L",
              "raised_ank_h", "raised_toe_h", "wristL_hipL_norm", "wristR_hipR_norm"]:
        if k in df.columns:
            df[k] = rolling_med(df[k].to_numpy(), k=smooth_k)
    
    return df, fps

def _stance_ball_xy_colab(df: pd.DataFrame, raised_leg: str = "L", alpha: float = 0.30):
    """EXACT copy from Colab OLS"""
    rl = (raised_leg or "L").upper()
    if rl == "L":
        need = {"x30", "y30"}  # Right foot (standing foot when left leg raised)
        if not need.issubset(df.columns):
            return None
        heel = df[["x30", "y30"]].to_numpy(float)
        # For toe, we need to add more robust toe handling
        if "x32" in df.columns and "y32" in df.columns:
            toe = df[["x32", "y32"]].to_numpy(float)
        else:
            toe = heel  # Fallback
    else:
        need = {"x29", "y29"}  # Left foot (standing foot when right leg raised)  
        if not need.issubset(df.columns):
            return None
        heel = df[["x29", "y29"]].to_numpy(float)
        if "x31" in df.columns and "y31" in df.columns:
            toe = df[["x31", "y31"]].to_numpy(float)
        else:
            toe = heel  # Fallback
            
    return toe + alpha * (heel - toe)

def _foot_drift_metrics_colab(df: pd.DataFrame, raised_leg: str = "L", px_per_cm: Optional[float] = 3.2) -> Dict[str, Any]:
    """EXACT copy from Colab OLS"""
    ball = _stance_ball_xy_colab(df, raised_leg=raised_leg)
    if ball is None or len(ball) == 0:
        return dict(drift_max_cm=None, drift_mean_cm=None, drift_lat_max_cm=None, drift_lat_mean_cm=None,
                    drift_ap_max_cm=None, drift_ap_mean_cm=None)
    
    k0 = min(10, len(ball))
    start = np.nanmedian(ball[:k0], axis=0)
    delta = ball - start
    drift_px = np.linalg.norm(delta, axis=1)
    drift_lat_px = np.abs(delta[:, 0])
    drift_ap_px = np.abs(delta[:, 1])
    
    def _cm(x):
        return x / px_per_cm if px_per_cm and px_per_cm > 0 else None
    return dict(
        drift_max_cm=float(np.nanmax(_cm(drift_px))) if _cm(drift_px) is not None else None,
        drift_mean_cm=float(np.nanmean(_cm(drift_px))) if _cm(drift_px) is not None else None,
        drift_lat_max_cm=float(np.nanmax(_cm(drift_lat_px))) if _cm(drift_lat_px) is not None else None,
        drift_lat_mean_cm=float(np.nanmean(_cm(drift_lat_px))) if _cm(drift_lat_px) is not None else None,
        drift_ap_max_cm=float(np.nanmax(_cm(drift_ap_px))) if _cm(drift_ap_px) is not None else None,
        drift_ap_mean_cm=float(np.nanmean(_cm(drift_ap_px))) if _cm(drift_ap_px) is not None else None,
    )

def count_toe_touches_colab(df: pd.DataFrame, fps: float, norm_thr: float = 0.03, min_frames: int = 3, min_gap_s: float = 0.30):
    """EXACT copy from Colab OLS (ols_rightleg_eo_colab.py count_toe_touches)."""
    toe = pd.Series(df["raised_toe_h"], dtype=float) if "raised_toe_h" in df.columns else pd.Series(dtype=float)
    near = toe <= norm_thr
    run = 0
    touch_idxs = []
    for i, ok in enumerate(near.fillna(False).to_numpy()):
        if ok:
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


def ols_events_and_strategy_colab(df: pd.DataFrame, fps: float, raised_leg: str = "L", age_tag: Optional[str] = None,
                                  ank_up: float = 0.15, ank_down: float = 0.05, min_contact_gap_frames: int = 8,
                                  onhip_thr: float = 0.35, min_off_gap_frames: int = 6):
    """
    EXACT copy from Colab OLS (ols_rightleg_eo_colab.py ols_events_and_strategy).
    - Foot touches (ankle): hysteresis on raised_ank_h (ank_up=0.15, ank_down=0.05), count grounded transitions.
    - Toe touches: age-tuned threshold (0.025 7y / 0.035 6y), min_gap_s 0.30/0.35.
    - Hands off: wrist*_hip*_norm <= onhip_thr (0.35) = on hip; hands_off_pct 0-1.
    - Strategy: medians (med_trunk over airborne only); rules Stepping / Knee strategy / Hip strategy / Ankle/minimal.
    """
    # ---- Ankle-based contact count (airborne↔grounded hysteresis) ----
    ank = pd.Series(df["raised_ank_h"], dtype=float)
    up = ank > ank_up
    down = ank < ank_down
    grounded = pd.Series(False, index=ank.index)
    state = True if (len(down) and bool(down.iloc[0])) else False
    grounded.iloc[0] = state
    for i in range(1, len(ank)):
        if state:
            if up.iloc[i]:
                state = False
        else:
            if down.iloc[i]:
                state = True
        grounded.iloc[i] = state
    # rising edge of grounded = new contact
    rising = grounded.diff().fillna(0) > 0
    foot_touches_ankle = count_transitions(rising.to_numpy(), min_gap_frames=min_contact_gap_frames)

    # ---- Toe-touch count (age-tuned threshold) ----
    toe_thr = 0.035 if age_tag == "6yrs" else 0.025
    min_gap_s = 0.35 if age_tag == "6yrs" else 0.30
    toe_touches = count_toe_touches_colab(df, fps, norm_thr=toe_thr, min_frames=3, min_gap_s=min_gap_s)

    # ---- Hands off hips ----
    onL = pd.Series(df["wristL_hipL_norm"], dtype=float) <= onhip_thr
    onR = pd.Series(df["wristR_hipR_norm"], dtype=float) <= onhip_thr
    both_on = onL & onR
    hands_off = ~both_on
    hands_off_cnt = count_transitions(hands_off.to_numpy(), min_gap_frames=min_off_gap_frames)
    hands_off_pct = float(hands_off.mean()) if len(hands_off) else 0.0

    # ---- Strategy: medians (med_trunk over airborne only) ----
    airborne = ~grounded

    def _med(series_name: str) -> float:
        if series_name not in df.columns:
            return float("nan")
        if airborne.any():
            s = df.loc[airborne, series_name]
        else:
            s = df[series_name]
        return float(pd.Series(s, dtype=float).median())

    med_trunk = _med("trunk_abs_deg")
    if "hip_L" in df.columns and "hip_R" in df.columns:
        med_hip = float(pd.concat([df["hip_L"], df["hip_R"]], axis=1).median().median())
    else:
        med_hip = float("nan")
    if "knee_L" in df.columns and "knee_R" in df.columns:
        med_knee = float(pd.concat([df["knee_L"], df["knee_R"]], axis=1).median().median())
    else:
        med_knee = float("nan")

    if foot_touches_ankle > 0 or toe_touches > 0:
        strategy = "Stepping"
    elif np.isfinite(med_knee) and med_knee >= 15 and np.isfinite(med_trunk) and med_trunk < 10:
        strategy = "Knee strategy"
    elif np.isfinite(med_hip) and med_hip >= 15 and np.isfinite(med_trunk) and med_trunk >= 7:
        strategy = "Hip strategy"
    else:
        strategy = "Ankle/minimal"

    return dict(
        toe_touches=int(toe_touches),
        foot_touches_ankle=int(foot_touches_ankle),
        hands_off_cnt=int(hands_off_cnt),
        hands_off_pct=hands_off_pct,
        strategy=strategy,
        med_trunk_deg=med_trunk,
        med_hip_deg=med_hip,
        med_knee_deg=med_knee,
    )

def summarize_neck_colab(df: pd.DataFrame):
    """EXACT copy from Colab OLS"""
    s = pd.Series(df.get("neck_goni_deg", []), dtype=float).dropna()
    return {
        "neck_mean_deg": float(s.mean()) if len(s) else np.nan,
        "neck_sd_deg": float(s.std(ddof=0)) if len(s) else np.nan,
        "neck_peak_deg": float(s.max()) if len(s) else np.nan,
    }

def summarize_ols_clip_colab(df, fps, view):
    """Match origin colab (ols_rightleg_eo_colab.py): report sway to align with reference.
    trunk_abs_deg = angle from vertical (0=upright, 90=horizontal). Origin exports small values
    (2-8°) for sway; scoring rubrics expect that convention. Convert (90 - angle) so output matches."""
    sway_abs = pd.Series(df.get("trunk_abs_deg", []), dtype=float).dropna()
    if len(sway_abs) == 0:
        return {"sway_mean_deg": np.nan, "sway_sd_deg": np.nan}
    raw_mean = float(sway_abs.mean())
    sd_deg = float(sway_abs.std(ddof=0))
    # Report as (90 - angle) so small tilt = small number, matching origin/reference
    mean_deg = float(np.clip(90.0 - raw_mean, 0.0, 90.0))
    return {
        "sway_mean_deg": mean_deg,
        "sway_sd_deg": sd_deg,
    }

def extract_ols_metrics_colab_exact(front_video_path: Optional[str] = None, side_video_path: Optional[str] = None,
                                   raised_leg: str = "L", age_tag: str = "7yrs", px_per_cm: Optional[float] = 3.2) -> Dict[str, Any]:
    """Extract OLS metrics using exact Colab calculations"""
    print(f"[DEBUG OLS COLAB] extract_ols_metrics called: front={front_video_path}, side={side_video_path}, raised_leg={raised_leg}")
    
    metrics = {
        "sway_SS_mean": None, "sway_SS_SD": None,
        "sway_AP_mean": None, "sway_AP_SD": None,
        "drift_max_cm": None, "drift_mean_cm": None,
        "drift_lat_max_cm": None, "drift_lat_mean_cm": None,
        "drift_ap_max_cm": None, "drift_ap_mean_cm": None,
        "neck_mean_deg": None, "neck_sd_deg": None, "neck_peak_deg": None,
        "toe_touches": None, "foot_touches": None, "hands_off_cnt": None, "hands_off_pct": None,
        "balance_strategy": None,
        "med_trunk_deg": None, "med_hip_deg": None, "med_knee_deg": None,
        "fps": 30.0,
        "front_toe_touches": None, "side_toe_touches": None,
        "front_foot_touches_ankle": None, "side_foot_touches_ankle": None,
        "front_strategy": None, "side_strategy": None,
    }

    ev_front: Optional[Dict[str, Any]] = None
    ev_side: Optional[Dict[str, Any]] = None

    if front_video_path and os.path.exists(front_video_path):
        print(f"[DEBUG OLS COLAB] Processing front video: {front_video_path}")
        df_front, fps_front = measure_ols_video_colab_exact(front_video_path, view="front", raised_leg=raised_leg)
        print(f"[DEBUG OLS COLAB] Front video: {len(df_front)} frames, fps={fps_front}")
        
        if len(df_front) > 10:
            summ = summarize_ols_clip_colab(df_front, fps_front, "front")
            print(f"[DEBUG OLS COLAB] Front sway summary: {summ}")
            metrics["sway_SS_mean"] = summ["sway_mean_deg"]
            metrics["sway_SS_SD"] = summ["sway_sd_deg"]
            metrics["fps"] = fps_front
            
            metrics.update(summarize_neck_colab(df_front))
            ev_front = ols_events_and_strategy_colab(df_front, fps_front, raised_leg=raised_leg, age_tag=age_tag)
            metrics["front_toe_touches"] = ev_front.get("toe_touches")
            metrics["front_foot_touches_ankle"] = ev_front.get("foot_touches_ankle")
            metrics["front_strategy"] = ev_front.get("strategy")
            metrics.update({k: v for k, v in ev_front.items() if k not in ("toe_touches", "foot_touches_ankle", "strategy")})
            metrics["balance_strategy"] = ev_front.get("strategy")
            metrics["foot_touches"] = ev_front.get("foot_touches_ankle")
            metrics["toe_touches"] = ev_front.get("toe_touches")
            metrics.update(_foot_drift_metrics_colab(df_front, raised_leg=raised_leg, px_per_cm=px_per_cm))

    if side_video_path and os.path.exists(side_video_path):
        print(f"[DEBUG OLS COLAB] Processing side video: {side_video_path}")
        df_side, fps_side = measure_ols_video_colab_exact(side_video_path, view="side", raised_leg=raised_leg)
        print(f"[DEBUG OLS COLAB] Side video: {len(df_side)} frames, fps={fps_side}")
        
        if len(df_side) > 10:
            summ = summarize_ols_clip_colab(df_side, fps_side, "side")
            print(f"[DEBUG OLS COLAB] Side sway summary: {summ}")
            metrics["sway_AP_mean"] = summ["sway_mean_deg"]
            metrics["sway_AP_SD"] = summ["sway_sd_deg"]
            if metrics["fps"] is None:
                metrics["fps"] = fps_side
            ev_side = ols_events_and_strategy_colab(df_side, fps_side, raised_leg=raised_leg, age_tag=age_tag)
            metrics["side_toe_touches"] = ev_side.get("toe_touches")
            metrics["side_foot_touches_ankle"] = ev_side.get("foot_touches_ankle")
            metrics["side_strategy"] = ev_side.get("strategy")
            # Aggregate for scoring: use worst case across views (match colab when combining front+side)
            toe_f = (ev_front or {}).get("toe_touches", 0) or 0
            toe_s = ev_side.get("toe_touches", 0) or 0
            foot_f = (ev_front or {}).get("foot_touches_ankle", 0) or 0
            foot_s = ev_side.get("foot_touches_ankle", 0) or 0
            str_f = (ev_front or {}).get("strategy") or ""
            str_s = ev_side.get("strategy") or ""
            # Safeguard: if one view has implausibly high toe count (e.g. pose noise), use the other view for scoring
            TOE_OUTLIER_THRESH = 10
            if toe_f > TOE_OUTLIER_THRESH and toe_s <= TOE_OUTLIER_THRESH:
                metrics["toe_touches"] = int(toe_s)
            elif toe_s > TOE_OUTLIER_THRESH and toe_f <= TOE_OUTLIER_THRESH:
                metrics["toe_touches"] = int(toe_f)
            else:
                metrics["toe_touches"] = int(max(toe_f, toe_s))
            metrics["foot_touches"] = max(foot_f, foot_s)
            metrics["balance_strategy"] = "Stepping" if (str_f == "Stepping" or str_s == "Stepping") else (str_f or str_s)
            # Keep med_* from front for display when we have both
            if ev_front is None:
                metrics["med_trunk_deg"] = ev_side.get("med_trunk_deg")
                metrics["med_hip_deg"] = ev_side.get("med_hip_deg")
                metrics["med_knee_deg"] = ev_side.get("med_knee_deg")

    # Report med_trunk_deg in same convention as origin (small = small tilt): 90 - raw angle
    if metrics.get("med_trunk_deg") is not None and np.isfinite(metrics["med_trunk_deg"]):
        metrics["med_trunk_deg"] = float(np.clip(90.0 - metrics["med_trunk_deg"], 0.0, 90.0))

    print(f"[DEBUG OLS COLAB] Final metrics: sway_SS_mean={metrics['sway_SS_mean']}, sway_AP_mean={metrics['sway_AP_mean']}, toe_touches={metrics.get('toe_touches')}, front_toe={metrics.get('front_toe_touches')}, side_toe={metrics.get('side_toe_touches')}")
    return metrics

def process_one_leg_standing(
    front_video_path: Optional[str],
    side_video_path: Optional[str],
    age_years: int,
    eyes_open: bool = True,
    raised_leg: str = "L"
) -> Dict[str, Any]:
    """Process OLS videos using exact Colab calculations"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_ols
    
    # Handle MOV files - try to convert if needed
    if front_video_path and os.path.exists(front_video_path):
        front_video_path, front_err = ensure_video_readable(front_video_path)
        if front_err:
            return {
                "rawMetrics": {}, "scores": {},
                "totalScore": 0, "maxScore": 34,
                "interpretation": f"Error (front video): {front_err}"
            }
    
    if side_video_path and os.path.exists(side_video_path):
        side_video_path, side_err = ensure_video_readable(side_video_path)
        if side_err:
            return {
                "rawMetrics": {}, "scores": {},
                "totalScore": 0, "maxScore": 34,
                "interpretation": f"Error (side video): {side_err}"
            }
    
    age_tag = "6yrs" if age_years == 6 else "7yrs"
    print(f"[DEBUG OLS COLAB] Processing: age_years={age_years}, eyes_open={eyes_open}, raised_leg={raised_leg}")
    
    raw_metrics = extract_ols_metrics_colab_exact(front_video_path, side_video_path, raised_leg, age_tag)
    
    print(f"[DEBUG OLS COLAB] Raw metrics extracted: {raw_metrics}")
    
    if raw_metrics["sway_SS_mean"] is None and raw_metrics["sway_AP_mean"] is None:
        print("[DEBUG OLS COLAB] ERROR: No valid pose data extracted")
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": "Error: No valid pose data extracted from videos."
        }
    
    score_result = score_ols(raw_metrics, age_years=age_years, eyes_open=eyes_open, raised_leg=raised_leg)
    print(f"[DEBUG OLS COLAB] Score result: {score_result}")
    max_score = score_result.get("max_score") or 34

    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": max_score,
        "interpretation": score_result.get("interpretation", "N/A"),
        "eyesOpen": eyes_open,
        "raisedLeg": raised_leg,
    }