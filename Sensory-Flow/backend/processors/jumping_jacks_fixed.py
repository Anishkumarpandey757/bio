
"""
Fixed Jumping Jacks backend for Colab/backend use.

What is fixed:
- Uses notebook-style raw signal extraction.
- Uses hysteresis rep counting instead of naive peak counting.
- Computes reps from arm + leg + jump opening/closing cycle.
- Keeps metric names aligned to your Colab outputs.
"""

import os
from typing import Dict, Any, Tuple, Optional

import cv2
import numpy as np
import pandas as pd
import mediapipe as mp

# Import MOV conversion utilities
try:
    from .common import ensure_video_readable
except ImportError:
    # Fallback if common not available
    def ensure_video_readable(path):
        return path, None

mp_pose = mp.solutions.pose
cv2.setNumThreads(1)

LM = dict(
    L_SH=11, R_SH=12, L_EL=13, R_EL=14, L_WR=15, R_WR=16,
    L_HP=23, R_HP=24, L_KN=25, R_KN=26, L_AN=27, R_AN=28,
    L_HEEL=29, R_HEEL=30, L_TOE=31, R_TOE=32,
    L_EAR=7, R_EAR=8,
)


def rolling_med(x, k=5):
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()


def angle_3pt(A, B, C, eps=1e-8):
    A = np.asarray(A, float); B = np.asarray(B, float); C = np.asarray(C, float)
    BA, BC = A - B, C - B
    na, nc = np.linalg.norm(BA), np.linalg.norm(BC)
    if na < eps or nc < eps:
        return np.nan
    cosv = np.dot(BA, BC) / (na * nc)
    return float(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))))


def angle_between_vecs(v1, v2, eps=1e-8):
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < eps or n2 < eps:
        return np.nan
    c = np.dot(v1, v2) / (n1 * n2)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def _pelvis_width_xy(P2):
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan


def _estimate_floor_y(P2, H=None):
    ys = [P2[LM['L_AN'], 1], P2[LM['R_AN'], 1]]
    if P2.shape[0] >= 33:
        ys += [P2[29, 1], P2[30, 1], P2[31, 1], P2[32, 1]]
    y = np.asarray(ys, float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H * 0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))


def adaptive_arm_levels(arm_angle):
    a = pd.Series(arm_angle, dtype=float).dropna()
    if len(a) < 20:
        return np.nan, np.nan
    mn, mx = float(a.min()), float(a.max())
    rng = mx - mn
    return mn + 0.2 * rng, mn + 0.6 * rng


def adaptive_leg_levels(leg_ratio):
    x = pd.Series(leg_ratio, dtype=float).dropna()
    if len(x) < 20:
        return np.nan, np.nan
    return float(np.percentile(x, 25)), float(np.percentile(x, 75))


def adaptive_jump_mask(hip_y_norm):
    y = pd.Series(hip_y_norm, dtype=float).dropna()
    if len(y) < 20:
        return None
    thr = 0.5 * float(np.std(y.to_numpy()))
    mu = float(np.mean(y.to_numpy()))
    return thr, mu


def hysteresis_state_from_levels(x, close_low, open_high):
    x = np.asarray(x, dtype=float)
    st = np.zeros(len(x), dtype=int)
    cur = 0
    for i, v in enumerate(x):
        if np.isnan(v):
            st[i] = cur
            continue
        if cur == 0 and v > open_high:
            cur = 1
        elif cur == 1 and v < close_low:
            cur = 0
        st[i] = cur
    return st.astype(bool)


def extract_jj_raw_colab_style(video_path, smooth_k=5, model_complexity=1):
    """Extract JJ raw data using exact Colab notebook method"""
    if not isinstance(video_path, str) or not os.path.exists(video_path):
        return pd.DataFrame(), 30.0
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return pd.DataFrame(), 30.0
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or not (10 < fps < 120):
        fps = 30.0
    rows = []
    with mp_pose.Pose(model_complexity=model_complexity,
                      min_detection_confidence=0.6,
                      min_tracking_confidence=0.6) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            H, W = frame.shape[:2]
            res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if not res.pose_landmarks:
                rows.append([np.nan] * 9)
                continue
            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.concatenate([P2, np.zeros((P2.shape[0], 1))], axis=1)
            sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
            hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
            trunk_vec = sh3 - hp3
            L_arm_vec = P3[LM['L_EL']] - P3[LM['L_SH']]
            R_arm_vec = P3[LM['R_EL']] - P3[LM['R_SH']]
            L_sh_open_deg = angle_between_vecs(trunk_vec, L_arm_vec)
            R_sh_open_deg = angle_between_vecs(trunk_vec, R_arm_vec)
            px_scale = _pelvis_width_xy(P2)
            y_floor = _estimate_floor_y(P2, H=H)
            ankle_dist = np.linalg.norm(P2[LM['L_AN']] - P2[LM['R_AN']])
            leg_spread_norm = ankle_dist / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan
            hip_y = float(((P2[LM['L_HP'], 1] + P2[LM['R_HP'], 1]) / 2.0) / px_scale) if np.isfinite(px_scale) and px_scale > 0 else np.nan
            hip_up = None
            rows.append([L_sh_open_deg, R_sh_open_deg, leg_spread_norm, hip_y,
                         y_floor, px_scale,
                         P2[LM['L_HP'], 1], P2[LM['R_HP'], 1],
                         np.nan])
    cap.release()
    df = pd.DataFrame(rows, columns=[
        'L_sh_open_deg', 'R_sh_open_deg', 'leg_spread_norm', 'hip_y_norm',
        'y_floor', 'pelvis_px', 'hipL_y_px', 'hipR_y_px', 'hip_up_disp_norm'
    ])
    n0 = int(max(15, min(30, len(df)))) if len(df) else 0
    hip_base = float(np.nanmean(df['hip_y_norm'].iloc[:n0])) if n0 else np.nan
    df['hip_up_disp_norm'] = hip_base - df['hip_y_norm']
    for c in ['L_sh_open_deg', 'R_sh_open_deg', 'leg_spread_norm', 'hip_y_norm', 'hip_up_disp_norm']:
        df[c] = rolling_med(df[c].to_numpy(), k=smooth_k)
    return df, float(fps)


def extract_jumping_jacks_metrics(video_path: str) -> Dict[str, Any]:
    """Extract jumping jacks metrics matching Colab notebook calculations exactly"""
    df, fps = extract_jj_raw_colab_style(video_path)
    if df is None or len(df) < 30:
        return {'error': 'Insufficient pose data', 'fps': fps}

    spread = df['leg_spread_norm'].to_numpy()
    hip_y = df['hip_y_norm'].to_numpy() 
    hip_up = df['hip_up_disp_norm'].to_numpy()
    arm_sig = np.nanmean(np.vstack([df['L_sh_open_deg'].to_numpy(), df['R_sh_open_deg'].to_numpy()]), axis=0)

    arm_close_low, arm_open_high = adaptive_arm_levels(arm_sig)
    leg_close_low, leg_open_high = adaptive_leg_levels(spread)
    jump_pack = adaptive_jump_mask(hip_y)
    if jump_pack is None:
        jump_now = np.zeros(len(spread), dtype=bool)
    else:
        jump_thr, jump_mu = jump_pack
        jump_now = hip_y < (jump_mu - jump_thr)

    arm_open_state = hysteresis_state_from_levels(arm_sig, arm_close_low, arm_open_high)
    leg_open_state = hysteresis_state_from_levels(spread, leg_close_low, leg_open_high)

    state = 'CLOSED'
    reps = 0
    partial_reps = 0
    seen_arm_open = seen_leg_open = seen_jump = False
    seen_arm_close = seen_leg_close = False
    rep_peak_shoulder, rep_peak_legspread, rep_peak_hipup = [], [], []
    open_start = None
    rep_windows = []

    for i in range(len(spread)):
        arm_open_now = bool(arm_open_state[i])
        arm_close_now = not arm_open_now
        leg_open_now = bool(leg_open_state[i])
        leg_close_now = not leg_open_now

        if state == 'CLOSED':
            if arm_open_now:
                seen_arm_open = True
            if leg_open_now:
                seen_leg_open = True
            if bool(jump_now[i]):
                seen_jump = True
            if seen_arm_open and seen_leg_open and seen_jump:
                state = 'OPENED'
                open_start = i
                seen_arm_close = False
                seen_leg_close = False
        else:
            if arm_close_now:
                seen_arm_close = True
            if leg_close_now:
                seen_leg_close = True
            if seen_arm_close and seen_leg_close:
                reps += 1
                s0, s1 = open_start, i
                if s0 is None or s1 <= s0:
                    s0, s1 = max(0, i - 1), i
                rep_windows.append((int(s0), int(s1)))
                rep_peak_shoulder.append(float(np.nanmax(arm_sig[s0:s1+1])))
                rep_peak_legspread.append(float(np.nanmax(spread[s0:s1+1])))
                rep_peak_hipup.append(float(np.nanmax(hip_up[s0:s1+1])))
                state = 'CLOSED'
                seen_arm_open = seen_leg_open = seen_jump = False
                open_start = None

    if state == 'OPENED':
        partial_reps = 1

    # Calculate sync properly via edges
    def rising_edges(st_bool):
        st = np.asarray(st_bool, dtype=bool)
        return np.where((~st[:-1]) & (st[1:]))[0] + 1

    def falling_edges(st_bool):
        st = np.asarray(st_bool, dtype=bool)
        return np.where((st[:-1]) & (~st[1:]))[0] + 1
        
    def first_edge_in_window(edges, s, e):
        for idx in edges:
            if s <= idx <= e:
                return int(idx)
        return None

    terms_arm_open = arm_open_state 
    A_open_idx = rising_edges(terms_arm_open)
    A_close_idx = falling_edges(terms_arm_open)
    
    terms_leg_open = leg_open_state
    G_open_idx = rising_edges(terms_leg_open)
    G_close_idx = falling_edges(terms_leg_open)

    arm_leg_open_dt = []
    arm_leg_close_dt = []

    for (s, e) in rep_windows:
        a_o = first_edge_in_window(A_open_idx, s, e)
        g_o = first_edge_in_window(G_open_idx, s, e)
        if a_o is not None and g_o is not None:
            dt = abs(a_o - g_o) / fps
            rep_dur = (e - s) / fps
            if dt <= rep_dur:
                arm_leg_open_dt.append(dt)

        a_c = first_edge_in_window(A_close_idx, s, e)
        g_c = first_edge_in_window(G_close_idx, s, e)
        if a_c is not None and g_c is not None:
            dt = abs(a_c - g_c) / fps
            rep_dur = (e - s) / fps
            if dt <= rep_dur:
                arm_leg_close_dt.append(dt)

    return {
        'valid_reps_total_jumps': int(reps),
        'jump_count': int(reps),
        'partial_reps': int(partial_reps),
        'shoulder_abduction_angle_mean_deg': float(np.nanmean(arm_sig)) if np.any(np.isfinite(arm_sig)) else None,
        'shoulder_abduction_angle_max_deg': float(np.nanmax(arm_sig)) if np.any(np.isfinite(arm_sig)) else None,
        'hip_abduction_distance_mean_norm': float(np.nanmean(spread)) if np.any(np.isfinite(spread)) else None,
        'hip_abduction_distance_max_norm': float(np.nanmax(spread)) if np.any(np.isfinite(spread)) else None,
        'hip_upward_displacement_mean_norm': float(np.nanmean(hip_up)) if np.any(np.isfinite(hip_up)) else None,
        'hip_upward_displacement_max_norm': float(np.nanmax(hip_up)) if np.any(np.isfinite(hip_up)) else None,
        'arm_leg_open_sync_mean_s': float(np.nanmean(arm_leg_open_dt)) if len(arm_leg_open_dt) else None,
        'arm_leg_close_sync_mean_s': float(np.nanmean(arm_leg_close_dt)) if len(arm_leg_close_dt) else None,
        'rep_peak_shoulder_mean_deg': float(np.nanmean(rep_peak_shoulder)) if len(rep_peak_shoulder) else None,
        'rep_peak_legspread_mean_norm': float(np.nanmean(rep_peak_legspread)) if len(rep_peak_legspread) else None,
        'rep_peak_hipup_mean_norm': float(np.nanmean(rep_peak_hipup)) if len(rep_peak_hipup) else None,
        'duration_s': len(df) / fps if fps > 0 else None,
        'repeat_rate': (reps / (len(df) / fps) * 60.0) if fps > 0 and len(df) else None,
        'fps': fps,
    }


def process_jumping_jacks(
    video_path: Optional[str],
    age_years: int
) -> Dict[str, Any]:
    """Process jumping jacks video and return scores - API wrapper."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_jumping_jacks
    
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
    
    raw_metrics = extract_jumping_jacks_metrics(video_path)
    
    if "error" in raw_metrics:
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 35,
            "interpretation": f"Error: {raw_metrics['error']}"
        }
    
    score_result = score_jumping_jacks(raw_metrics, age_years=age_years)
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k or k == "total_score"},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": 35,
        "interpretation": score_result.get("interpretation", "N/A"),
    }
