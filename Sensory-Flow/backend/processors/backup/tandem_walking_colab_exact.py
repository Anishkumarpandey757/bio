"""
Tandem Walking processor - aligned with origin Colab (tademmanin_colab.py).
Origin: tademwalkingeo (EO), tademwalkingec (EC). Sway as (90 - angle) to match.
"""

import os
from typing import Dict, Any, Optional, List
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
    """EXACT copy from Colab Tandem Walking"""
    BA, BC = A-B, C-B
    na, nc = np.linalg.norm(BA), np.linalg.norm(BC)
    if na < eps or nc < eps: 
        return np.nan
    cosv = np.dot(BA, BC) / (na*nc)
    return float(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))))

def angle_signed_to_vertical(P0, P1):
    """EXACT copy from Colab Tandem Walking - key function for trunk sway"""
    v = (P1 - P0).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8: 
        return np.nan
    v /= n
    unsigned = np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0,-1.0])), -1, 1)))
    sgn = 1.0 if v[0] >= 0 else -1.0
    return float(sgn * unsigned)

def angle_between_vecs(v1, v2, eps=1e-8):
    """EXACT copy from Colab Tandem Walking"""
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < eps or n2 < eps: 
        return np.nan
    c = np.dot(v1, v2) / (n1*n2)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))

def pelvis_width_xy(P2):
    """EXACT copy from Colab Tandem Walking"""
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan

def estimate_floor_y(P2, H=None):
    """EXACT copy from Colab Tandem Walking"""
    ys = [P2[LM['L_AN'],1], P2[LM['R_AN'],1]]
    if P2.shape[0] >= 33:
        ys += [P2[29,1], P2[30,1], P2[31,1], P2[32,1]]
    y = np.array(ys, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H*0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))

def rolling_med(x, k=5):
    """EXACT copy from Colab Tandem Walking"""
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()

def measure_tandem_video_colab_exact(video_path, view="front", smooth_k=5, model_complexity=1):
    """EXACT copy of pose measurement from Colab tandem walking files"""
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
                rows.append([np.nan] * 18)
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
            trunk_signed_deg = angle_signed_to_vertical(hp2, sh2)
            trunk_abs_deg = abs(trunk_signed_deg) if np.isfinite(trunk_signed_deg) else np.nan

            # Joint angles (exact Colab method)
            hip_R = 180.0 - angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])
            hip_L = 180.0 - angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])
            knee_R = 180.0 - angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])
            knee_L = 180.0 - angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])

            # Foot positioning (exact Colab method)
            px_scale = pelvis_width_xy(P2)
            y_floor = estimate_floor_y(P2, H=H)
            
            # Ankle heights and positions
            ankL_y, ankR_y = float(P2[LM['L_AN'], 1]), float(P2[LM['R_AN'], 1])
            def _nh(y):
                if not np.isfinite(px_scale) or px_scale <= 0 or not np.isfinite(y) or not np.isfinite(y_floor):
                    return np.nan
                return max((y_floor - y) / px_scale, 0.0)
            
            ank_L_h, ank_R_h = _nh(ankL_y), _nh(ankR_y)

            # Hand positions (exact Colab method)
            wristL_norm = np.linalg.norm(P2[LM['L_WR']] - P2[LM['L_HP']]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan
            wristR_norm = np.linalg.norm(P2[LM['R_WR']] - P2[LM['R_HP']]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan

            # Build row exactly as Colab does
            rows.append([
                trunk_signed_deg, trunk_abs_deg,
                hip_R, hip_L, knee_R, knee_L,
                ank_L_h, ank_R_h,
                wristL_norm, wristR_norm,
                y_floor, px_scale, sh2[0], sh2[1], hp2[0], hp2[1],
                P2[29,0] if P2.shape[0] > 29 else np.nan, P2[29,1] if P2.shape[0] > 29 else np.nan
            ])

    cap.release()

    # Column names exactly as Colab
    cols = [
        "trunk_signed_deg", "trunk_abs_deg",
        "hip_R", "hip_L", "knee_R", "knee_L",
        "ank_L_h", "ank_R_h",
        "wristL_hipL_norm", "wristR_hipR_norm",
        "y_floor", "pelvis_px", "sh_x", "sh_y", "hp_x", "hp_y",
        "x29", "y29"
    ]
    
    df = pd.DataFrame(rows, columns=cols)
    
    # Smoothing exactly as Colab
    for k in ["trunk_signed_deg", "trunk_abs_deg", "hip_R", "hip_L", "knee_R", "knee_L",
              "ank_L_h", "ank_R_h", "wristL_hipL_norm", "wristR_hipR_norm"]:
        if k in df.columns:
            df[k] = rolling_med(df[k].to_numpy(), k=smooth_k)
    
    return df, fps

def count_steps_colab(df: pd.DataFrame, fps: float, min_lift_height: float = 0.02, 
                     min_step_frames: int = 3, min_gap_frames: int = 6) -> Dict[str, int]:
    """Count steps using exact Colab method"""
    steps_L = steps_R = 0
    
    if "ank_L_h" in df.columns and "ank_R_h" in df.columns:
        # Left foot steps
        ank_L = pd.Series(df["ank_L_h"], dtype=float)
        lifted_L = (ank_L > min_lift_height).to_numpy()
        
        run_L = 0
        step_starts_L = []
        for i, lifted in enumerate(lifted_L):
            if lifted and np.isfinite(ank_L.iloc[i]):
                run_L += 1
                if run_L == min_step_frames:
                    step_starts_L.append(i)
            else:
                run_L = 0
        
        # Filter by minimum gap
        filtered_L = []
        for i in step_starts_L:
            if not filtered_L or i - filtered_L[-1] >= min_gap_frames:
                filtered_L.append(i)
        steps_L = len(filtered_L)
        
        # Right foot steps
        ank_R = pd.Series(df["ank_R_h"], dtype=float)
        lifted_R = (ank_R > min_lift_height).to_numpy()
        
        run_R = 0
        step_starts_R = []
        for i, lifted in enumerate(lifted_R):
            if lifted and np.isfinite(ank_R.iloc[i]):
                run_R += 1
                if run_R == min_step_frames:
                    step_starts_R.append(i)
            else:
                run_R = 0
                
        # Filter by minimum gap
        filtered_R = []
        for i in step_starts_R:
            if not filtered_R or i - filtered_R[-1] >= min_gap_frames:
                filtered_R.append(i)
        steps_R = len(filtered_R)
    
    total_steps = steps_L + steps_R
    return {"steps_left": int(steps_L), "steps_right": int(steps_R), "total_steps": int(total_steps)}

def count_transitions_colab(boolean_series, min_gap_frames=6):
    """EXACT copy from Colab"""
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

def tandem_events_and_strategy_colab(df, fps, age_tag=None, wrist_hip_thr=0.60):
    """EXACT copy from Colab tandem walking events and strategy detection"""
    
    # Hand movements
    wL = pd.Series(df.get("wristL_hipL_norm", []), dtype=float)
    wR = pd.Series(df.get("wristR_hipR_norm", []), dtype=float)
    hands_off_mask = (wL > wrist_hip_thr) | (wR > wrist_hip_thr)
    hands_off_cnt = count_transitions_colab(hands_off_mask.to_numpy(), min_gap_frames=max(3, int(0.2 * fps)))
    hands_off_pct = float(100.0 * hands_off_mask.mean()) if len(hands_off_mask) else np.nan

    # Strategy classification (exact Colab logic)
    med_trunk = float(pd.Series(df.get("trunk_abs_deg", []), dtype=float).median(skipna=True))
    med_hip = float(pd.Series(df[["hip_L", "hip_R"]].median(axis=1) if {"hip_L","hip_R"}.issubset(df.columns) else [], dtype=float).median(skipna=True))
    med_knee = float(pd.Series(df[["knee_L", "knee_R"]].median(axis=1) if {"knee_L","knee_R"}.issubset(df.columns) else [], dtype=float).median(skipna=True))

    if np.isfinite(med_hip) and med_hip >= 20:
        strategy = "hip"
    elif np.isfinite(med_knee) and med_knee >= 20:
        strategy = "knee"
    else:
        strategy = "ankle"

    return dict(
        hands_off_cnt=int(hands_off_cnt),
        hands_off_pct=hands_off_pct,
        strategy=strategy,
        med_trunk_deg=med_trunk,
        med_hip_deg=med_hip,
        med_knee_deg=med_knee,
    )

def summarize_tandem_clip_colab(df, fps, view):
    """Match origin colab (tademmanin_colab.py): report sway as raw angle from vertical (small = less sway)."""
    sway_abs = pd.Series(df.get("trunk_abs_deg", []), dtype=float).dropna()
    if len(sway_abs) == 0:
        return {"sway_mean_deg": np.nan, "sway_sd_deg": np.nan, "sway_max_deg": np.nan}
    mean_deg = float(sway_abs.mean())
    sd_deg = float(sway_abs.std(ddof=0))
    max_deg = float(sway_abs.max()) if np.isfinite(sway_abs.max()) else np.nan
    return {
        "sway_mean_deg": mean_deg,
        "sway_sd_deg": sd_deg,
        "sway_max_deg": max_deg,
    }

def extract_tandem_walking_metrics_colab_exact(front_video_path: Optional[str] = None, 
                                              side_video_path: Optional[str] = None,
                                              age_tag: str = "7yrs") -> Dict[str, Any]:
    """Extract tandem walking metrics using exact Colab calculations"""
    print(f"[DEBUG TANDEM COLAB] extract_tandem_walking_metrics called: front={front_video_path}, side={side_video_path}")
    
    metrics = {
        "sway_SS_mean": None, "sway_SS_SD": None, "sway_SS_max": None,
        "sway_AP_mean": None, "sway_AP_SD": None, "sway_AP_max": None,
        "steps_left": 0, "steps_right": 0, "total_steps": 0,
        "hands_off_cnt": None, "hands_off_pct": None,
        "balance_strategy": None,
        "med_trunk_deg": None, "med_hip_deg": None, "med_knee_deg": None,
        "fps": 30.0,
    }

    if front_video_path and os.path.exists(front_video_path):
        print(f"[DEBUG TANDEM COLAB] Processing front video: {front_video_path}")
        df_front, fps_front = measure_tandem_video_colab_exact(front_video_path, view="front")
        print(f"[DEBUG TANDEM COLAB] Front video: {len(df_front)} frames, fps={fps_front}")
        
        if len(df_front) > 10:
            summ = summarize_tandem_clip_colab(df_front, fps_front, "front")
            print(f"[DEBUG TANDEM COLAB] Front sway summary: {summ}")
            metrics["sway_SS_mean"] = summ["sway_mean_deg"]
            metrics["sway_SS_SD"] = summ["sway_sd_deg"]
            metrics["sway_SS_max"] = summ["sway_max_deg"]
            metrics["fps"] = fps_front
            
            # Step counting and events
            step_counts = count_steps_colab(df_front, fps_front)
            metrics.update(step_counts)
            
            ev = tandem_events_and_strategy_colab(df_front, fps_front, age_tag=age_tag)
            metrics.update(ev)

    if side_video_path and os.path.exists(side_video_path):
        print(f"[DEBUG TANDEM COLAB] Processing side video: {side_video_path}")
        df_side, fps_side = measure_tandem_video_colab_exact(side_video_path, view="side")
        print(f"[DEBUG TANDEM COLAB] Side video: {len(df_side)} frames, fps={fps_side}")
        
        if len(df_side) > 10:
            summ = summarize_tandem_clip_colab(df_side, fps_side, "side")
            print(f"[DEBUG TANDEM COLAB] Side sway summary: {summ}")
            metrics["sway_AP_mean"] = summ["sway_mean_deg"]
            metrics["sway_AP_SD"] = summ["sway_sd_deg"]
            metrics["sway_AP_max"] = summ["sway_max_deg"]
            if metrics["fps"] is None:
                metrics["fps"] = fps_side
                
            # If we didn't get step counts from front video, try side video
            if metrics["total_steps"] == 0:
                step_counts = count_steps_colab(df_side, fps_side)
                metrics.update(step_counts)

    print(f"[DEBUG TANDEM COLAB] Final metrics: sway_SS_mean={metrics['sway_SS_mean']}, sway_AP_mean={metrics['sway_AP_mean']}, total_steps={metrics['total_steps']}")
    return metrics

def process_tandem_walking(
    front_video_path: Optional[str],
    side_video_path: Optional[str],
    age_years: int,
    eyes_open: bool = True
) -> Dict[str, Any]:
    """Process tandem walking videos using exact Colab calculations"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_tandem_walking
    
    # Handle MOV files - try to convert if needed
    if front_video_path and os.path.exists(front_video_path):
        front_video_path, front_err = ensure_video_readable(front_video_path)
        if front_err:
            return {
                "rawMetrics": {}, "scores": {},
                "totalScore": 0, "maxScore": 32,
                "interpretation": f"Error (front video): {front_err}"
            }
    
    if side_video_path and os.path.exists(side_video_path):
        side_video_path, side_err = ensure_video_readable(side_video_path)
        if side_err:
            return {
                "rawMetrics": {}, "scores": {},
                "totalScore": 0, "maxScore": 32,
                "interpretation": f"Error (side video): {side_err}"
            }
    
    age_tag = "6yrs" if age_years == 6 else "7yrs"
    print(f"[DEBUG TANDEM COLAB] Processing: age_years={age_years}, eyes_open={eyes_open}")
    
    raw_metrics = extract_tandem_walking_metrics_colab_exact(front_video_path, side_video_path, age_tag)
    
    print(f"[DEBUG TANDEM COLAB] Raw metrics extracted: {raw_metrics}")
    
    if raw_metrics["sway_SS_mean"] is None and raw_metrics["sway_AP_mean"] is None:
        print("[DEBUG TANDEM COLAB] ERROR: No valid pose data extracted")
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 32,
            "interpretation": "Error: No valid pose data extracted from videos."
        }
    
    score_result = score_tandem_walking(raw_metrics, age_years=age_years, eyes_open=eyes_open)
    print(f"[DEBUG TANDEM COLAB] Score result: {score_result}")
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": 32,
        "interpretation": score_result.get("interpretation", "N/A"),
        "eyesOpen": eyes_open,
    }