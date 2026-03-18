"""Jumping Jacks Processor - Front and Side views
Ported from: jumpingpck (2).py notebooks
Calculates: Jump count, shoulder/hip angles, vertical displacement, synchronization metrics
"""

import os
import cv2
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List

import mediapipe as mp
mp_pose = mp.solutions.pose

from .common import LM, angle_3pt, angle_between_vecs, rolling_med, detect_view_from_video


# ---- Helper functions from jumping jacks notebooks ----

def _pelvis_width_xy(P2: np.ndarray) -> float:
    """Pelvis width in pixels"""
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan


def _estimate_floor_y(P2: np.ndarray, H: Optional[int] = None) -> float:
    """Robust floor y-coordinate (95th percentile of foot positions)"""
    ys = [P2[LM['L_AN'], 1], P2[LM['R_AN'], 1]]
    if P2.shape[0] >= 33:  # foot landmarks
        ys += [P2[29, 1], P2[30, 1], P2[31, 1], P2[32, 1]]
    y = np.array(ys, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H * 0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))


def _detect_peaks(series: np.ndarray, min_height: float = 0.1, min_distance: int = 10) -> List[int]:
    """Detect local peaks in a series (for vertical displacement peaks)"""
    if not np.any(np.isfinite(series)):
        return []
    
    s = np.nan_to_num(series, nan=np.nanmean(series) if np.any(np.isfinite(series)) else 0.0)
    peaks = []
    
    for i in range(min_distance, len(s) - min_distance):
        is_peak = True
        # Check neighbors
        for j in range(i - min_distance, i + min_distance + 1):
            if j != i and s[j] >= s[i]:
                is_peak = False
                break
        
        # Check height relative to neighbors
        neighbor_mean = (np.mean(s[i - min_distance:i]) + np.mean(s[i + 1:i + min_distance + 1])) / 2.0
        if is_peak and (s[i] - neighbor_mean) >= min_height:
            peaks.append(i)
    
    return peaks


def measure_jumping_jacks_video(video_path: str, view: str = "front", smooth_k: int = 5) -> Tuple[pd.DataFrame, float]:
    """Extract jumping jacks per-frame metrics from video"""
    if not video_path or not isinstance(video_path, str) or not os.path.exists(video_path):
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
                    "shoulder_abd_deg", "hip_abd_dist_norm", "hip_vertical_norm",
                    "arm_elev_deg", "leg_spread_cm"
                ]})
                continue
            
            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            
            # Shoulder abduction (from front): angle at elbow between shoulder-elbow-wrist
            try:
                shoulder_abd = angle_3pt(P2[LM['L_SH']], P2[LM['L_EL']], P2[LM['L_WR']])
                shoulder_abd = float(shoulder_abd) if np.isfinite(shoulder_abd) else np.nan
            except:
                shoulder_abd = np.nan
            
            # Hip abduction (from front): angle at knee between hip-knee-ankle
            try:
                hip_abd = angle_3pt(P2[LM['L_HP']], P2[LM['L_KN']], P2[LM['L_AN']])
                hip_abd = float(hip_abd) if np.isfinite(hip_abd) else np.nan
            except:
                hip_abd = np.nan
            
            # Hip vertical displacement (normalized by pelvis width)
            px_scale = _pelvis_width_xy(P2)
            y_floor = _estimate_floor_y(P2, H=H)
            
            if np.isfinite(px_scale) and px_scale > 0 and np.isfinite(y_floor):
                hip_y = (P2[LM['L_HP'], 1] + P2[LM['R_HP'], 1]) / 2.0
                hip_vertical = max((y_floor - hip_y) / px_scale, 0.0)
            else:
                hip_vertical = np.nan
            
            # Shoulder abduction angle using 3D landmarks (more accurate - matches Colab)
            # trunk_vec = shoulder_mid - hip_mid, L_arm_vec = elbow - shoulder
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
                sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
                hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
                trunk_vec = sh3 - hp3
                L_arm_vec = P3[LM['L_EL']] - P3[LM['L_SH']]
                R_arm_vec = P3[LM['R_EL']] - P3[LM['R_SH']]
                # Use angle_between_vecs to match Colab implementation
                L_sh_open = angle_between_vecs(trunk_vec, L_arm_vec) if np.linalg.norm(L_arm_vec) > 1e-8 else np.nan
                R_sh_open = angle_between_vecs(trunk_vec, R_arm_vec) if np.linalg.norm(R_arm_vec) > 1e-8 else np.nan
                # Use mean of both shoulders for scoring (matches Colab arm_sig)
                shoulder_open_mean = float(np.nanmean([L_sh_open, R_sh_open]))
            else:
                shoulder_open_mean = shoulder_abd  # Fallback to 2D
            
            # Arm elevation (shoulder to wrist vertical distance, normalized)
            if np.isfinite(px_scale) and px_scale > 0:
                sh_y = (P2[LM['L_SH'], 1] + P2[LM['R_SH'], 1]) / 2.0
                wr_y_max = min(P2[LM['L_WR'], 1], P2[LM['R_WR'], 1])
                arm_elev = max((sh_y - wr_y_max) / px_scale, 0.0)
            else:
                arm_elev = np.nan
            
            # Leg spread (distance between ankles, normalized) - this is hip_abduction_distance in Colab
            L_an = P2[LM['L_AN']]
            R_an = P2[LM['R_AN']]
            leg_spread = np.linalg.norm(L_an - R_an)
            if np.isfinite(px_scale) and px_scale > 0:
                leg_spread_norm = leg_spread / px_scale
            else:
                leg_spread_norm = np.nan
            
            rows.append({
                "shoulder_open_deg": shoulder_open_mean,  # Shoulder abduction angle (mean of L/R)
                "leg_spread_norm": leg_spread_norm,       # Hip abduction distance (normalized ankle spread)
                "hip_vertical_norm": hip_vertical,
                "arm_elev_deg": arm_elev,
            })
    
    cap.release()
    df = pd.DataFrame(rows)
    
    # Smooth metrics (not jump detection) - matches Colab rolling_med
    for k in ["shoulder_open_deg", "leg_spread_norm", "arm_elev_deg"]:
        if k in df.columns:
            df[k] = rolling_med(df[k].values, k=smooth_k)
    
    return df, fps


def extract_jumping_jacks_metrics(video_path: str) -> Dict[str, Any]:
    """Extract comprehensive jumping jacks metrics from video"""
    
    # View detection and sanity check
    view_detection = detect_view_from_video(video_path) if video_path and os.path.exists(video_path) else None
    warnings = []
    
    if view_detection:
        # Jumping jacks typically needs FRONT view for best arm/leg spread analysis
        if view_detection["detected_view"] == "side" and view_detection["confidence"] > 0.6:
            warnings.append(f"Video appears to be SIDE view (confidence: {view_detection['confidence']:.0%}). FRONT view recommended for jumping jacks.")
        elif view_detection["detected_view"] == "unknown":
            warnings.append(f"Could not detect view type: {view_detection['details']}")
    
    df, fps = measure_jumping_jacks_video(video_path)
    
    if df is None or len(df) < 30:
        return {"error": "Insufficient pose data", "fps": fps, "view_detection": view_detection, "view_warnings": warnings}
    
    metrics = {"view_detection": view_detection, "view_warnings": warnings}
    
    # Jump counting via vertical displacement peaks (matching Colab rep detection)
    hip_vertical = df.get("hip_vertical_norm", pd.Series([])).values
    peaks = _detect_peaks(hip_vertical, min_height=0.05, min_distance=max(5, int(fps / 10)))
    jump_count = len(peaks)
    metrics["valid_reps_total_jumps"] = int(jump_count)  # Colab key name
    metrics["jump_count"] = int(jump_count)  # Also include for display
    
    # Shoulder abduction angle (from shoulder_open_deg) - matches Colab
    if "shoulder_open_deg" in df.columns:
        s = pd.Series(df["shoulder_open_deg"], dtype=float)
        valid = s.dropna()
        if len(valid) > 0:
            metrics["shoulder_abduction_angle_mean_deg"] = float(valid.mean())
            metrics["shoulder_abduction_angle_max_deg"] = float(valid.max())
        else:
            metrics["shoulder_abduction_angle_mean_deg"] = None
            metrics["shoulder_abduction_angle_max_deg"] = None
    else:
        metrics["shoulder_abduction_angle_mean_deg"] = None
        metrics["shoulder_abduction_angle_max_deg"] = None
    
    # Hip abduction distance (from leg_spread_norm) - matches Colab
    if "leg_spread_norm" in df.columns:
        s = pd.Series(df["leg_spread_norm"], dtype=float)
        valid = s.dropna()
        if len(valid) > 0:
            metrics["hip_abduction_distance_mean_norm"] = float(valid.mean())
            metrics["hip_abduction_distance_max_norm"] = float(valid.max())
        else:
            metrics["hip_abduction_distance_mean_norm"] = None
            metrics["hip_abduction_distance_max_norm"] = None
    else:
        metrics["hip_abduction_distance_mean_norm"] = None
        metrics["hip_abduction_distance_max_norm"] = None
    
    # Vertical displacement for jump scoring (hip_upward_displacement) - matches Colab
    if len(hip_vertical) > 0:
        hip_vert_valid = hip_vertical[np.isfinite(hip_vertical)]
        if len(hip_vert_valid) > 0:
            metrics["hip_upward_displacement_mean_norm"] = float(np.mean(hip_vert_valid))
            metrics["hip_upward_displacement_max_norm"] = float(np.max(hip_vert_valid))
        else:
            metrics["hip_upward_displacement_mean_norm"] = None
            metrics["hip_upward_displacement_max_norm"] = None
    else:
        metrics["hip_upward_displacement_mean_norm"] = None
        metrics["hip_upward_displacement_max_norm"] = None
    
    # Arm-leg sync timing - estimate from peak timing in same frame windows
    # Lower sync time = better synchronization (measured in seconds)
    # For accurate sync, we'd need per-rep analysis like Colab, but approximate here
    # using arm/leg peak correlation
    arm_signal = df.get("shoulder_open_deg", pd.Series([])).values if "shoulder_open_deg" in df.columns else np.array([])
    leg_signal = df.get("leg_spread_norm", pd.Series([])).values if "leg_spread_norm" in df.columns else np.array([])
    
    if len(arm_signal) > 30 and len(leg_signal) > 30:
        # Find peaks in both signals
        arm_peaks = _detect_peaks(arm_signal, min_height=5, min_distance=max(5, int(fps/10)))
        leg_peaks = _detect_peaks(leg_signal, min_height=0.1, min_distance=max(5, int(fps/10)))
        
        # Calculate sync timing as avg frame difference between closest arm/leg peaks
        if len(arm_peaks) > 0 and len(leg_peaks) > 0:
            sync_diffs = []
            for ap in arm_peaks:
                closest_leg = min(leg_peaks, key=lambda lp: abs(lp - ap))
                diff_frames = abs(ap - closest_leg)
                diff_seconds = diff_frames / fps
                sync_diffs.append(diff_seconds)
            avg_sync = float(np.mean(sync_diffs)) if sync_diffs else 0.0
            metrics["arm_leg_open_sync_mean_s"] = avg_sync
            metrics["arm_leg_close_sync_mean_s"] = avg_sync  # Approximate close sync = open sync
        else:
            metrics["arm_leg_open_sync_mean_s"] = 0.0
            metrics["arm_leg_close_sync_mean_s"] = 0.0
    else:
        metrics["arm_leg_open_sync_mean_s"] = 0.0
        metrics["arm_leg_close_sync_mean_s"] = 0.0
    
    # Exercise duration
    metrics["duration_s"] = len(df) / fps if fps > 0 else len(df) / 30.0
    metrics["repeat_rate"] = (jump_count / metrics["duration_s"] * 60.0) if metrics["duration_s"] > 0 else None
    
    metrics["fps"] = fps
    
    return metrics


def process_jumping_jacks(
    video_path: Optional[str],
    age_years: int
) -> Dict[str, Any]:
    """Process jumping jacks video and return scores (Stage 3: Scoring)"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_jumping_jacks
    
    if not video_path or not os.path.exists(video_path):
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 35,
            "interpretation": "Error: No video provided"
        }
    
    # Stage 1 & 2: Measure + Extract
    raw_metrics = extract_jumping_jacks_metrics(video_path)
    
    if "error" in raw_metrics:
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 35,
            "interpretation": f"Error: {raw_metrics['error']}"
        }
    
    # Stage 3: Score
    score_result = score_jumping_jacks(raw_metrics, age_years=age_years)
    
    # Build interpretation with view warnings
    view_warnings = raw_metrics.get("view_warnings", [])
    interpretation = score_result.get("interpretation", "N/A")
    if view_warnings:
        interpretation = "VIEW WARNING: " + "; ".join(view_warnings) + " | " + interpretation
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k or k == "total_score"},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": 35,
        "interpretation": interpretation,
        "viewWarnings": view_warnings
    }
