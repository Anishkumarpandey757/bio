#!/usr/bin/env python3
"""
Streamlit Jumping Jacks Assessment & Scoring App
Based on jumping_jacks (4).py preprocessing and math_jump.py scoring
"""

import streamlit as st
import pandas as pd
import numpy as np
import cv2
import os
import tempfile
import importlib.util
import re
from io import BytesIO
from typing import Dict, Tuple, List, Optional
import warnings

# Load the local math_jump.py file explicitly
import sys

math_file_path = os.path.join(os.path.dirname(__file__), 'math_jump.py')
spec = importlib.util.spec_from_file_location("jumping_jacks_scoring_math", math_file_path)
jumping_jacks_scoring_math = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jumping_jacks_scoring_math)

# Extract scoring functions
score_row_6y = jumping_jacks_scoring_math.score_row_6y
score_row_7y = jumping_jacks_scoring_math.score_row_7y
score_row = jumping_jacks_scoring_math.score_row

# MediaPipe setup
try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except ImportError as e:
    st.error(f"❌ MediaPipe not installed. Please install: pip install mediapipe")
    st.stop()
except AttributeError as e:
    st.error(f"❌ MediaPipe version issue. Please update: pip install --upgrade mediapipe")
    st.stop()

# Landmark indices
LM = dict(
    L_SH=11, R_SH=12, L_EL=13, R_EL=14, L_WR=15, R_WR=16,
    L_HP=23, R_HP=24, L_KN=25, R_KN=26, L_AN=27, R_AN=28,
    L_HEEL=29, R_HEEL=30, L_TOE=31, R_TOE=32,
    L_EAR=7, R_EAR=8
)

# -------------------------
# Utility Functions
# -------------------------
def angle_between_vecs(v1, v2, eps=1e-8):
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < eps or n2 < eps:
        return np.nan
    c = float(np.dot(v1, v2) / (n1 * n2))
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))

def pelvis_width_xy(P2):
    d = np.linalg.norm(P2[LM["L_HP"]] - P2[LM["R_HP"]])
    return float(d) if d > 1e-8 else np.nan

def estimate_floor_y(P2, H=None):
    ys = [P2[LM["L_AN"], 1], P2[LM["R_AN"], 1]]
    if P2.shape[0] >= 33:
        ys += [
            P2[LM["L_HEEL"], 1], P2[LM["R_HEEL"], 1],
            P2[LM["L_TOE"], 1], P2[LM["R_TOE"], 1]
        ]
    y = np.array(ys, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H * 0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))

def rolling_med(x, k=5):
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()

def rising_edges(st_bool):
    st = np.asarray(st_bool, dtype=bool)
    return np.where((~st[:-1]) & (st[1:]))[0] + 1

def falling_edges(st_bool):
    st = np.asarray(st_bool, dtype=bool)
    return np.where((st[:-1]) & (~st[1:]))[0] + 1

def safe_mean(arr):
    s = pd.Series(arr, dtype=float).dropna()
    return float(s.mean()) if len(s) else np.nan

def safe_max(arr):
    s = pd.Series(arr, dtype=float).dropna()
    return float(s.max()) if len(s) else np.nan

def first_edge_in_window(edges, s, e):
    """Return first edge index inside [s,e], else None."""
    for idx in edges:
        if s <= idx <= e:
            return int(idx)
    return None

# -------------------------
# Adaptive Thresholds
# -------------------------
def adaptive_arm_levels(arm_angle):
    a = pd.Series(arm_angle, dtype=float).dropna()
    if len(a) < 20:
        return (np.nan, np.nan)
    mn, mx = float(a.min()), float(a.max())
    rng = mx - mn
    return (mn + 0.2 * rng, mn + 0.6 * rng)

def adaptive_leg_levels(leg_ratio):
    x = pd.Series(leg_ratio, dtype=float).dropna()
    if len(x) < 20:
        return (np.nan, np.nan)
    return (float(np.percentile(x, 25)), float(np.percentile(x, 75)))

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

# -------------------------
# Pose Extraction -> Raw Signals
# -------------------------
def extract_jj_raw(video_path, smooth_k=5, model_complexity=1, progress_bar=None):
    """Extract raw jumping jacks signals from video."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or not (10 < fps < 120):
        fps = 30.0
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    rows = []
    frame_idx = 0
    
    with mp_pose.Pose(
        model_complexity=model_complexity,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as pose:

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            
            if progress_bar and total_frames > 0:
                progress_bar.progress(min(frame_idx / total_frames, 1.0))

            H, W = frame.shape[:2]
            res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            if not res.pose_landmarks:
                rows.append([np.nan] * 22)
                frame_idx += 1
                continue

            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)

            vis = np.array([lm.visibility for lm in res.pose_landmarks.landmark], dtype=float)
            vis_L = float(np.nanmean([vis[LM["L_SH"]], vis[LM["L_HP"]], vis[LM["L_KN"]], vis[LM["L_AN"]]]))
            vis_R = float(np.nanmean([vis[LM["R_SH"]], vis[LM["R_HP"]], vis[LM["R_KN"]], vis[LM["R_AN"]]]))

            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.full((33, 3), np.nan, dtype=float)

            sh2 = (P2[LM["L_SH"]] + P2[LM["R_SH"]]) / 2.0
            hp2 = (P2[LM["L_HP"]] + P2[LM["R_HP"]]) / 2.0
            sh3 = (P3[LM["L_SH"]] + P3[LM["R_SH"]]) / 2.0
            hp3 = (P3[LM["L_HP"]] + P3[LM["R_HP"]]) / 2.0

            px_scale = pelvis_width_xy(P2) or np.nan
            y_floor = estimate_floor_y(P2, H=H)

            ankle_dist = np.linalg.norm(P2[LM["L_AN"]] - P2[LM["R_AN"]])
            leg_spread_norm = (ankle_dist / px_scale) if np.isfinite(px_scale) else np.nan

            L_ank_h = (y_floor - P2[LM["L_AN"], 1]) / px_scale if np.isfinite(px_scale) else np.nan
            R_ank_h = (y_floor - P2[LM["R_AN"], 1]) / px_scale if np.isfinite(px_scale) else np.nan

            trunk_vec = sh3 - hp3
            L_arm_vec = P3[LM["L_EL"]] - P3[LM["L_SH"]]
            R_arm_vec = P3[LM["R_EL"]] - P3[LM["R_SH"]]
            L_sh_open_deg = angle_between_vecs(trunk_vec, L_arm_vec)
            R_sh_open_deg = angle_between_vecs(trunk_vec, R_arm_vec)

            pelvis_axis = P3[LM["L_HP"]] - P3[LM["R_HP"]]
            L_thigh = P3[LM["L_KN"]] - P3[LM["L_HP"]]
            R_thigh = P3[LM["R_KN"]] - P3[LM["R_HP"]]
            L_hip_open_deg = angle_between_vecs(pelvis_axis, L_thigh)
            R_hip_open_deg = angle_between_vecs(pelvis_axis, R_thigh)

            ear3 = (P3[LM["L_EAR"]] + P3[LM["R_EAR"]]) / 2.0
            head_vec = ear3 - sh3
            neck_goni_deg = angle_between_vecs(trunk_vec, head_vec)

            def angle_3pt(A, B, C, eps=1e-8):
                ba = A - B
                bc = C - B
                n1, n2 = np.linalg.norm(ba), np.linalg.norm(bc)
                if n1 < eps or n2 < eps:
                    return np.nan
                c = float(np.dot(ba, bc) / (n1 * n2))
                return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))

            hip_L = 180.0 - angle_3pt(P3[LM["L_SH"]], P3[LM["L_HP"]], P3[LM["L_KN"]])
            hip_R = 180.0 - angle_3pt(P3[LM["R_SH"]], P3[LM["R_HP"]], P3[LM["R_KN"]])
            knee_L = 180.0 - angle_3pt(P3[LM["L_HP"]], P3[LM["L_KN"]], P3[LM["L_AN"]])
            knee_R = 180.0 - angle_3pt(P3[LM["R_HP"]], P3[LM["R_KN"]], P3[LM["R_AN"]])

            hip_y_px = float(hp2[1])
            hip_y_norm = (hip_y_px / (px_scale + 1e-6)) if np.isfinite(px_scale) else np.nan

            trunk2 = sh2 - hp2
            vertical_up = np.array([0.0, -1.0], dtype=float)
            trunk_flex_deg = angle_between_vecs(trunk2, vertical_up)

            rows.append([
                leg_spread_norm,
                L_ank_h, R_ank_h,
                L_sh_open_deg, R_sh_open_deg,
                L_hip_open_deg, R_hip_open_deg,
                neck_goni_deg,
                hip_L, hip_R, knee_L, knee_R,
                px_scale, y_floor,
                sh2[0], sh2[1], hp2[0], hp2[1],
                hip_y_norm,
                trunk_flex_deg,
                vis_L,
                vis_R,
            ])
            
            frame_idx += 1

    cap.release()

    cols = [
        "leg_spread_norm",
        "L_ank_h", "R_ank_h",
        "L_sh_open_deg", "R_sh_open_deg",
        "L_hip_open_deg", "R_hip_open_deg",
        "neck_goni_deg",
        "hip_L_deg", "hip_R_deg", "knee_L_deg", "knee_R_deg",
        "pelvis_px", "y_floor",
        "sh_x", "sh_y", "hp_x", "hp_y",
        "hip_y_norm",
        "trunk_flex_deg",
        "vis_L_chain",
        "vis_R_chain",
    ]
    df = pd.DataFrame(rows, columns=cols)

    # Compute baseline hip height displacement
    n0 = int(max(15, min(30, len(df))))
    hip_base = float(np.nanmean(df["hip_y_norm"].iloc[:n0])) if len(df) else np.nan
    df["hip_up_disp_norm"] = hip_base - df["hip_y_norm"]

    # Smooth signals
    smooth_cols = [
        "leg_spread_norm", "L_ank_h", "R_ank_h",
        "L_sh_open_deg", "R_sh_open_deg",
        "L_hip_open_deg", "R_hip_open_deg",
        "neck_goni_deg", "trunk_flex_deg",
        "hip_L_deg", "hip_R_deg", "knee_L_deg", "knee_R_deg",
        "hip_y_norm", "hip_up_disp_norm",
        "vis_L_chain", "vis_R_chain"
    ]
    for c in smooth_cols:
        if c in df.columns:
            df[c] = rolling_med(df[c].to_numpy(), k=smooth_k)

    return df, float(fps)

# -------------------------
# Strategy Summary (SIDE)
# -------------------------
def summarize_strategy(side_df):
    def mean_or_nan(x):
        x = pd.Series(x, dtype=float).dropna()
        return float(x.mean()) if len(x) else np.nan

    vL = mean_or_nan(side_df["vis_L_chain"].to_numpy())
    vR = mean_or_nan(side_df["vis_R_chain"].to_numpy())
    side_used = "L" if (np.isfinite(vL) and np.isfinite(vR) and vL >= vR) else "R"

    neck_mean = mean_or_nan(side_df["neck_goni_deg"].to_numpy())
    trunk_mean = mean_or_nan(side_df["trunk_flex_deg"].to_numpy())

    if side_used == "L":
        hip_mean = mean_or_nan(side_df["hip_L_deg"].to_numpy())
        knee_mean = mean_or_nan(side_df["knee_L_deg"].to_numpy())
    else:
        hip_mean = mean_or_nan(side_df["hip_R_deg"].to_numpy())
        knee_mean = mean_or_nan(side_df["knee_R_deg"].to_numpy())

    return {
        "side_used_for_flexion": side_used,
        "neck_flex_mean_deg": neck_mean,
        "trunk_flex_mean_deg": trunk_mean,
        "hip_flex_mean_deg": hip_mean,
        "knee_flex_mean_deg": knee_mean,
    }

# -------------------------
# Metrics from Raw
# -------------------------
def jj_metrics_from_raw(front_df, side_df, fps):
    """Compute jumping jacks metrics from front and side video data."""
    spread = front_df["leg_spread_norm"].to_numpy()
    hip_y = front_df["hip_y_norm"].to_numpy()
    hip_up = front_df["hip_up_disp_norm"].to_numpy()

    Lsh = front_df["L_sh_open_deg"].to_numpy()
    Rsh = front_df["R_sh_open_deg"].to_numpy()
    arm_sig = np.nanmean(np.vstack([Lsh, Rsh]), axis=0)

    arm_close_low, arm_open_high = adaptive_arm_levels(arm_sig)
    leg_close_low, leg_open_high = adaptive_leg_levels(spread)

    jump_pack = adaptive_jump_mask(hip_y)
    if jump_pack is None:
        jump_thr, jump_mu = 0.5, float(np.nanmean(hip_y)) if np.any(np.isfinite(hip_y)) else 0.0
        jump_now = np.zeros(len(spread), dtype=bool)
    else:
        jump_thr, jump_mu = jump_pack
        jump_now = hip_y < (jump_mu - jump_thr)

    arm_open_state = hysteresis_state_from_levels(arm_sig, close_low=arm_close_low, open_high=arm_open_high)
    leg_open_state = hysteresis_state_from_levels(spread, close_low=leg_close_low, open_high=leg_open_high)

    # Rep counting with state machine
    state = "CLOSED"
    reps = 0
    partial_reps = 0

    seen_arm_open = False
    seen_leg_open = False
    seen_jump = False
    seen_arm_close = False
    seen_leg_close = False

    open_start = None
    rep_windows = []

    rep_peak_shoulder = []
    rep_peak_legspread = []
    rep_peak_hipup = []

    for i in range(len(spread)):
        arm_open_now = bool(arm_open_state[i])
        arm_close_now = (not arm_open_now)

        leg_open_now = bool(leg_open_state[i])
        leg_close_now = (not leg_open_now)

        if state == "CLOSED":
            if arm_open_now:
                seen_arm_open = True
            if leg_open_now:
                seen_leg_open = True
            if jump_now[i]:
                seen_jump = True

            if seen_arm_open and seen_leg_open and seen_jump:
                state = "OPENED"
                open_start = i
                seen_arm_close = False
                seen_leg_close = False

        else:  # OPENED
            if arm_close_now:
                seen_arm_close = True
            if leg_close_now:
                seen_leg_close = True

            if seen_arm_close and seen_leg_close:
                reps += 1
                if open_start is not None:
                    rep_windows.append((open_start, i))
                    # Record peak values during this rep
                    seg_sh = arm_sig[open_start:i+1]
                    seg_leg = spread[open_start:i+1]
                    seg_hip = hip_up[open_start:i+1]
                    rep_peak_shoulder.append(float(np.nanmax(seg_sh)) if np.any(np.isfinite(seg_sh)) else np.nan)
                    rep_peak_legspread.append(float(np.nanmax(seg_leg)) if np.any(np.isfinite(seg_leg)) else np.nan)
                    rep_peak_hipup.append(float(np.nanmax(seg_hip)) if np.any(np.isfinite(seg_hip)) else np.nan)

                state = "CLOSED"
                seen_arm_open = False
                seen_leg_open = False
                seen_jump = False

    if state == "OPENED":
        partial_reps = 1

    # Shoulder L/R drift
    L_arm_state = hysteresis_state_from_levels(Lsh, *adaptive_arm_levels(Lsh))
    R_arm_state = hysteresis_state_from_levels(Rsh, *adaptive_arm_levels(Rsh))

    L_open_idx = rising_edges(L_arm_state)
    R_open_idx = rising_edges(R_arm_state)
    L_close_idx = falling_edges(L_arm_state)
    R_close_idx = falling_edges(R_arm_state)

    n_open = min(len(L_open_idx), len(R_open_idx))
    n_close = min(len(L_close_idx), len(R_close_idx))
    sh_open_dt = [abs(int(L_open_idx[i]) - int(R_open_idx[i])) / fps for i in range(n_open)]
    sh_close_dt = [abs(int(L_close_idx[i]) - int(R_close_idx[i])) / fps for i in range(n_close)]

    # Hip L/R drift
    Lhip = front_df["L_hip_open_deg"].to_numpy()
    Rhip = front_df["R_hip_open_deg"].to_numpy()
    Lh_state = hysteresis_state_from_levels(Lhip, *adaptive_arm_levels(Lhip))
    Rh_state = hysteresis_state_from_levels(Rhip, *adaptive_arm_levels(Rhip))

    Lh_open_idx = rising_edges(Lh_state)
    Rh_open_idx = rising_edges(Rh_state)
    Lh_close_idx = falling_edges(Lh_state)
    Rh_close_idx = falling_edges(Rh_state)

    n_hopen = min(len(Lh_open_idx), len(Rh_open_idx))
    n_hclose = min(len(Lh_close_idx), len(Rh_close_idx))
    hip_open_dt = [abs(int(Lh_open_idx[i]) - int(Rh_open_idx[i])) / fps for i in range(n_hopen)]
    hip_close_dt = [abs(int(Lh_close_idx[i]) - int(Rh_close_idx[i])) / fps for i in range(n_hclose)]

    # Arm-Leg Sync (per rep window)
    arms_both_open = L_arm_state & R_arm_state
    A_open_idx = rising_edges(arms_both_open)
    A_close_idx = falling_edges(arms_both_open)

    G_open_idx = rising_edges(leg_open_state)
    G_close_idx = falling_edges(leg_open_state)

    arm_leg_open_dt = []
    arm_leg_close_dt = []

    for (s, e) in rep_windows:
        a_o = first_edge_in_window(A_open_idx, s, e)
        g_o = first_edge_in_window(G_open_idx, s, e)
        if a_o is not None and g_o is not None:
            arm_leg_open_dt.append(abs(a_o - g_o) / fps)

        a_c = first_edge_in_window(A_close_idx, s, e)
        g_c = first_edge_in_window(G_close_idx, s, e)
        if a_c is not None and g_c is not None:
            arm_leg_close_dt.append(abs(a_c - g_c) / fps)

    # Strategy (SIDE)
    strat = summarize_strategy(side_df)

    out = {
        "valid_reps_total_jumps": int(reps),
        "partial_reps": int(partial_reps),

        "shoulder_abduction_angle_mean_deg": safe_mean(rep_peak_shoulder),
        "shoulder_abduction_angle_max_deg": safe_max(rep_peak_shoulder),

        "hip_abduction_distance_mean_norm": safe_mean(rep_peak_legspread),
        "hip_abduction_distance_max_norm": safe_max(rep_peak_legspread),

        "hip_upward_displacement_mean_norm": safe_mean(rep_peak_hipup),
        "hip_upward_displacement_max_norm": safe_max(rep_peak_hipup),

        "ARM_CLOSE": float(arm_close_low) if np.isfinite(arm_close_low) else np.nan,
        "ARM_OPEN": float(arm_open_high) if np.isfinite(arm_open_high) else np.nan,
        "LEG_CLOSE": float(leg_close_low) if np.isfinite(leg_close_low) else np.nan,
        "LEG_OPEN": float(leg_open_high) if np.isfinite(leg_open_high) else np.nan,
        "JUMP_THR": float(jump_thr) if np.isfinite(jump_thr) else np.nan,
        "JUMP_MU": float(jump_mu) if np.isfinite(jump_mu) else np.nan,

        "shoulder_open_dt_mean_s": float(np.nanmean(sh_open_dt)) if len(sh_open_dt) else np.nan,
        "shoulder_close_dt_mean_s": float(np.nanmean(sh_close_dt)) if len(sh_close_dt) else np.nan,
        "hip_open_dt_mean_s": float(np.nanmean(hip_open_dt)) if len(hip_open_dt) else np.nan,
        "hip_close_dt_mean_s": float(np.nanmean(hip_close_dt)) if len(hip_close_dt) else np.nan,

        "arm_leg_open_sync_mean_s": float(np.nanmean(arm_leg_open_dt)) if len(arm_leg_open_dt) else np.nan,
        "arm_leg_close_sync_mean_s": float(np.nanmean(arm_leg_close_dt)) if len(arm_leg_close_dt) else np.nan,
    }
    out.update(strat)
    return out

# -------------------------
# Main Processing Function
# -------------------------
def process_jumping_jacks(front_video_path, side_video_path, progress_bar=None):
    """
    Main processing function for jumping jacks analysis.
    Returns dict with all computed metrics.
    """
    results = {
        "shoulder_abduction_angle_mean_deg": None,
        "hip_abduction_distance_mean_norm": None,
        "hip_upward_displacement_mean_norm": None,
        "arm_leg_open_sync_mean_s": None,
        "arm_leg_close_sync_mean_s": None,
        "valid_reps_total_jumps": 0,
        "partial_reps": 0,
        "processing_success": False
    }

    try:
        # Process front video
        if progress_bar:
            progress_bar.progress(0.1)
        
        front_df, fps_front = extract_jj_raw(front_video_path, progress_bar=None)
        
        if progress_bar:
            progress_bar.progress(0.5)
        
        # Process side video
        side_df, fps_side = extract_jj_raw(side_video_path, progress_bar=None)
        
        if progress_bar:
            progress_bar.progress(0.8)
        
        if front_df is None or len(front_df) < 20:
            st.error("❌ Could not extract enough pose data from front video.")
            return results
            
        if side_df is None or len(side_df) < 20:
            st.error("❌ Could not extract enough pose data from side video.")
            return results

        # Use front video fps as primary
        fps = fps_front if fps_front else fps_side

        # Compute metrics
        metrics = jj_metrics_from_raw(front_df, side_df, fps=fps)
        
        if progress_bar:
            progress_bar.progress(1.0)
        
        # Update results
        results.update(metrics)
        results["processing_success"] = True
        
    except Exception as e:
        st.error(f"Error in processing: {str(e)}")
    
    return results

# -------------------------
# Main Streamlit App
# -------------------------
def main():
    st.set_page_config(page_title="Jumping Jacks Scorer", layout="wide")
    
    st.title("🏃 Jumping Jacks Assessment & Scoring")
    st.markdown("Upload **Front** and **Side** view videos to get automated jumping jacks scores using age-appropriate rubrics (6-year or 7-year).")
    
    st.divider()
    
    # Mandatory Age Group Selection
    st.subheader("👶 Student Age Group (Required)")
    col_age, col_name = st.columns([1, 2])
    
    with col_age:
        age_group = st.selectbox(
            "Select Age Group *", 
            ["Select Age...", "6 Years", "7 Years"],
            help="Choose the appropriate age group for scoring rubric"
        )
    
    with col_name:
        student_name = st.text_input("Student Name/ID (Optional)")
    
    # Validate age selection
    if age_group == "Select Age...":
        st.warning("⚠️ Please select an age group to proceed with scoring.")
        age_selected = False
    else:
        age_selected = True
        age_years = 6 if "6" in age_group else 7
        
        # Display scoring information
        if age_years == 6:
            st.info("📊 **6 Years Scoring**: Max Score = 35 points (Shoulder Abduction: 6, Hip Abduction: 8, Jump Height: 6, Open Sync: 8, Close Sync: 7)")
        else:
            st.info("📊 **7 Years Scoring**: Max Score = 36 points (Shoulder Abduction: 7, Hip Abduction: 8, Jump Height: 6, Open Sync: 8, Close Sync: 7)")
    
    st.divider()
    
    # Video upload section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📹 Front View Video (Required)")
        front_video = st.file_uploader(
            "Upload Front View",
            type=["mp4", "mov", "avi", "mkv"],
            key="front",
            help="Front view video is required for arm/leg spread and jump height analysis"
        )
    
    with col2:
        st.subheader("📹 Side View Video (Required)")
        side_video = st.file_uploader(
            "Upload Side View",
            type=["mp4", "mov", "avi", "mkv"],
            key="side",
            help="Side view video is required for posture and flexibility analysis"
        )
    
    # Processing section
    st.divider()
    
    if st.button("🚀 Process Videos & Calculate Scores", type="primary", use_container_width=True, disabled=not age_selected):
        
        if not front_video:
            st.error("❌ Please upload a front view video file to process.")
            st.stop()
        
        if not side_video:
            st.error("❌ Please upload a side view video file to process.")
            st.stop()
        
        if not age_selected:
            st.error("❌ Please select an age group before processing.")
            st.stop()
        
        # Display selected scoring system
        st.success(f"✅ Using {age_group} scoring rubric for jumping jacks assessment")
        
        # Process Videos
        with st.spinner("🎥 Processing videos..."):
            # Save uploaded files temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_front:
                tmp_front.write(front_video.read())
                tmp_front_path = tmp_front.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_side:
                tmp_side.write(side_video.read())
                tmp_side_path = tmp_side.name
            
            try:
                # Add progress bar
                progress_bar = st.progress(0)
                st.text("📊 Analyzing jumping jacks movements...")
                
                # Process the videos
                results = process_jumping_jacks(
                    tmp_front_path, 
                    tmp_side_path,
                    progress_bar=progress_bar
                )
                
                progress_bar.progress(1.0)
                
                if not results["processing_success"]:
                    st.error("❌ Could not extract jumping jacks data from videos. Please ensure the videos show clear jumping jack movements.")
                    return
                
                st.success("✅ Video processing complete!")
                
                st.subheader(f"📊 {age_group} Rubric - Calculated Parameters & Scores")
                
                # Score using age-appropriate functions
                scores = score_row(results, age_years)
                
                # Display results in a clean table
                results_data = [
                    {
                        "Parameter": "Shoulder Abduction Angle",
                        "Raw Value": f"{results['shoulder_abduction_angle_mean_deg']:.2f}°" if results.get('shoulder_abduction_angle_mean_deg') is not None and np.isfinite(results.get('shoulder_abduction_angle_mean_deg', np.nan)) else "N/A",
                        "Score": scores.get("shoulder_abduction_angle_score", "N/A"),
                        "Description": "Average peak shoulder abduction during open phase"
                    },
                    {
                        "Parameter": "Hip Abduction Distance", 
                        "Raw Value": f"{results['hip_abduction_distance_mean_norm']:.2f}" if results.get('hip_abduction_distance_mean_norm') is not None and np.isfinite(results.get('hip_abduction_distance_mean_norm', np.nan)) else "N/A",
                        "Score": scores.get("hip_abduction_distance_score", "N/A"),
                        "Description": "Normalized leg spread distance during jacks"
                    },
                    {
                        "Parameter": "Jump Height (Hip Displacement)",
                        "Raw Value": f"{results['hip_upward_displacement_mean_norm']:.2f}" if results.get('hip_upward_displacement_mean_norm') is not None and np.isfinite(results.get('hip_upward_displacement_mean_norm', np.nan)) else "N/A",
                        "Score": scores.get("jump_score", "N/A"),
                        "Description": "Normalized upward hip displacement during jump"
                    },
                    {
                        "Parameter": "Arm-Leg Open Sync",
                        "Raw Value": f"{results['arm_leg_open_sync_mean_s']:.3f}s" if results.get('arm_leg_open_sync_mean_s') is not None and np.isfinite(results.get('arm_leg_open_sync_mean_s', np.nan)) else "N/A",
                        "Score": scores.get("arm_leg_open_sync_score", "N/A"),
                        "Description": "Timing difference between arms and legs opening (lower is better)"
                    },
                    {
                        "Parameter": "Arm-Leg Close Sync",
                        "Raw Value": f"{results['arm_leg_close_sync_mean_s']:.3f}s" if results.get('arm_leg_close_sync_mean_s') is not None and np.isfinite(results.get('arm_leg_close_sync_mean_s', np.nan)) else "N/A",
                        "Score": scores.get("arm_leg_close_sync_score", "N/A"),
                        "Description": "Timing difference between arms and legs closing (lower is better)"
                    }
                ]
                
                df_results = pd.DataFrame(results_data)
                
                # Style the dataframe
                st.dataframe(
                    df_results,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Total Score
                total_score = scores.get("total_score", "N/A")
                max_score = scores.get("max_total", 35 if age_years == 6 else 36)
                
                st.divider()
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.metric("🎯 Total Score", f"{total_score}/{max_score}" if total_score is not None else "N/A")
                
                with col_b:
                    percentage = (total_score/max_score)*100 if total_score is not None and max_score > 0 else 0
                    st.metric("📊 Percentage", f"{percentage:.1f}%")
                
                with col_c:
                    interpretation = scores.get("interpretation", "N/A")
                    if interpretation and interpretation != "N/A":
                        if "Above" in interpretation:
                            st.success(f"✅ {interpretation}")
                        elif "Average" == interpretation:
                            st.info(f"📊 {interpretation}")
                        elif "Below" in interpretation:
                            st.warning(f"⚠️ {interpretation}")
                        else:
                            st.write(f"📋 {interpretation}")
                    else:
                        st.write("📋 N/A")
                
                # Detailed analysis
                st.divider()
                st.subheader("📋 Detailed Analysis")
                
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.write("**Movement Performance:**")
                    st.write(f"• Valid reps (complete jumps): {results.get('valid_reps_total_jumps', 0)}")
                    st.write(f"• Partial reps: {results.get('partial_reps', 0)}")
                    
                    # Shoulder performance
                    sh_max = results.get('shoulder_abduction_angle_max_deg')
                    if sh_max is not None and np.isfinite(sh_max):
                        st.write(f"• Peak shoulder abduction: {sh_max:.1f}°")
                    
                    # Leg spread
                    leg_max = results.get('hip_abduction_distance_max_norm')
                    if leg_max is not None and np.isfinite(leg_max):
                        st.write(f"• Peak leg spread: {leg_max:.2f}")
                
                with col_right:
                    st.write("**Coordination Analysis:**")
                    
                    # Arm sync
                    sh_open_dt = results.get('shoulder_open_dt_mean_s')
                    sh_close_dt = results.get('shoulder_close_dt_mean_s')
                    if sh_open_dt is not None and np.isfinite(sh_open_dt):
                        st.write(f"• L-R shoulder open timing diff: {sh_open_dt:.3f}s")
                    if sh_close_dt is not None and np.isfinite(sh_close_dt):
                        st.write(f"• L-R shoulder close timing diff: {sh_close_dt:.3f}s")
                    
                    # Hip sync
                    hip_open_dt = results.get('hip_open_dt_mean_s')
                    hip_close_dt = results.get('hip_close_dt_mean_s')
                    if hip_open_dt is not None and np.isfinite(hip_open_dt):
                        st.write(f"• L-R hip open timing diff: {hip_open_dt:.3f}s")
                    if hip_close_dt is not None and np.isfinite(hip_close_dt):
                        st.write(f"• L-R hip close timing diff: {hip_close_dt:.3f}s")
                
                # Posture analysis from side view
                with st.expander("🔍 Posture Analysis (from Side View)"):
                    st.write("**Body Position During Exercise:**")
                    
                    side_used = results.get('side_used_for_flexion', 'N/A')
                    st.write(f"• Primary side analyzed: {side_used}")
                    
                    trunk_flex = results.get('trunk_flex_mean_deg')
                    if trunk_flex is not None and np.isfinite(trunk_flex):
                        trunk_quality = "Good (upright)" if trunk_flex < 15 else "Moderate" if trunk_flex < 25 else "Needs attention (leaning)"
                        st.write(f"• Average trunk flexion: {trunk_flex:.1f}° - {trunk_quality}")
                    
                    neck_flex = results.get('neck_flex_mean_deg')
                    if neck_flex is not None and np.isfinite(neck_flex):
                        st.write(f"• Average neck angle: {neck_flex:.1f}°")
                    
                    hip_flex = results.get('hip_flex_mean_deg')
                    if hip_flex is not None and np.isfinite(hip_flex):
                        st.write(f"• Average hip flexion: {hip_flex:.1f}°")
                    
                    knee_flex = results.get('knee_flex_mean_deg')
                    if knee_flex is not None and np.isfinite(knee_flex):
                        st.write(f"• Average knee flexion: {knee_flex:.1f}°")
                
                # Performance feedback
                with st.expander("💡 Performance Feedback"):
                    st.write("**Key Observations:**")
                    
                    # Shoulder feedback
                    sh_mean = results.get('shoulder_abduction_angle_mean_deg')
                    if sh_mean is not None and np.isfinite(sh_mean):
                        if sh_mean >= 150:
                            st.success("✅ Excellent arm extension - arms reaching overhead properly")
                        elif sh_mean >= 120:
                            st.info("📊 Good arm movement - consider reaching arms higher overhead")
                        else:
                            st.warning("⚠️ Limited arm extension - encourage full overhead reach")
                    
                    # Leg feedback
                    leg_mean = results.get('hip_abduction_distance_mean_norm')
                    if leg_mean is not None and np.isfinite(leg_mean):
                        if leg_mean >= 4.0:
                            st.success("✅ Excellent leg spread during jumping jacks")
                        elif leg_mean >= 3.0:
                            st.info("📊 Good leg movement - encourage wider stance")
                        else:
                            st.warning("⚠️ Limited leg spread - work on lateral leg movement")
                    
                    # Sync feedback
                    open_sync = results.get('arm_leg_open_sync_mean_s')
                    close_sync = results.get('arm_leg_close_sync_mean_s')
                    if open_sync is not None and np.isfinite(open_sync) and close_sync is not None and np.isfinite(close_sync):
                        avg_sync = (open_sync + close_sync) / 2
                        if avg_sync < 0.5:
                            st.success("✅ Excellent coordination - arms and legs well synchronized")
                        elif avg_sync < 1.0:
                            st.info("📊 Good coordination - minor timing differences between arms and legs")
                        else:
                            st.warning("⚠️ Coordination needs work - practice synchronizing arm and leg movements")
                    
                    # Jump feedback
                    jump_mean = results.get('hip_upward_displacement_mean_norm')
                    if jump_mean is not None and np.isfinite(jump_mean):
                        if jump_mean >= 4.0:
                            st.success("✅ Excellent jump height")
                        elif jump_mean >= 2.0:
                            st.info("📊 Good jump height - could aim higher")
                        else:
                            st.warning("⚠️ Limited jump height - focus on pushing off the ground")
                
                # Download results as CSV
                st.divider()
                
                # Combine all results for export
                export_data = {
                    "Student": student_name or "Unknown",
                    "Age Group": age_group,
                    **{k: v for k, v in results.items() if k != "processing_success"},
                    **scores,
                }
                
                export_df = pd.DataFrame([export_data])
                csv_data = export_df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Complete Results as CSV",
                    data=csv_data,
                    file_name=f"jumping_jacks_results_{student_name if student_name else 'student'}.csv",
                    mime="text/csv"
                )
            
            except Exception as e:
                st.error(f"❌ Error processing videos: {str(e)}")
            finally:
                # Clean up temporary files
                if os.path.exists(tmp_front_path):
                    os.unlink(tmp_front_path)
                if os.path.exists(tmp_side_path):
                    os.unlink(tmp_side_path)

if __name__ == "__main__":
    main()
