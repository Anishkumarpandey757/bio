"""
Jumping Jacks processor - aligned with origin Colab (jumping_jacks/jumping_jacks colab.py).
Same metrics: shoulder/hip abduction, trunk, reps. MOV handled via common.ensure_video_readable.
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
    L_HP=23, R_HP=24, L_KN=25, R_KN=26, L_AN=27, R_AN=28,
    L_HEEL=29, R_HEEL=30, L_TOE=31, R_TOE=32,
)

def angle_3pt(A, B, C, eps=1e-8):
    """EXACT copy from Colab jumping_jacks (4).py"""
    BA, BC = A-B, C-B
    na, nc = np.linalg.norm(BA), np.linalg.norm(BC)
    if na < eps or nc < eps: 
        return np.nan
    cosv = np.dot(BA, BC) / (na*nc)
    return float(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))))

def angle_signed_to_vertical(P0, P1):
    """EXACT copy from Colab jumping_jacks (4).py - fixed for 2D coordinates"""
    # Ensure we work with 2D coordinates only
    if P0.shape[0] > 2:
        P0 = P0[:2]
    if P1.shape[0] > 2:
        P1 = P1[:2]
        
    v = (P1 - P0).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8: 
        return np.nan
    v /= n
    unsigned = np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0,-1.0])), -1, 1)))
    sgn = 1.0 if v[0] >= 0 else -1.0
    return float(sgn * unsigned)

def angle_between_vecs(v1, v2, eps=1e-8):
    """EXACT copy from Colab jumping_jacks (4).py"""
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < eps or n2 < eps: 
        return np.nan
    c = np.dot(v1, v2) / (n1*n2)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))

def pelvis_width_xy(P2):
    """EXACT copy from Colab jumping_jacks (4).py"""
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan


def estimate_floor_y(P2, H=None):
    """EXACT copy from Colab jumping_jacks colab.py"""
    ys = [P2[LM["L_AN"], 1], P2[LM["R_AN"], 1]]
    if P2.shape[0] >= 33:
        ys += [
            P2[LM["L_HEEL"], 1], P2[LM["R_HEEL"], 1],
            P2[LM["L_TOE"], 1], P2[LM["R_TOE"], 1],
        ]
    y = np.array(ys, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H * 0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))


def rolling_med(x, k=5):
    """EXACT copy from Colab jumping_jacks (4).py"""
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()

def angle_to_vertical(P0, P1):
    """EXACT copy from Colab jumping_jacks (4).py - fixed for coordinate dimensions"""
    # Handle both 2D and 3D coordinates - for arm angles we might use 3D, but project to 2D for vertical comparison
    if len(P0.shape) > 0 and P0.shape[0] >= 2 and len(P1.shape) > 0 and P1.shape[0] >= 2:
        # Take first 2 coordinates for vertical angle calculation  
        v = (P1[:2] - P0[:2]).astype(float)
    else:
        v = (P1 - P0).astype(float)
        
    n = np.linalg.norm(v)
    if n < 1e-8: 
        return np.nan
    v /= n
    return float(np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0,-1.0])), -1, 1))))

def measure_jumping_jacks_video_colab_exact(video_path, view="front", smooth_k=5, model_complexity=1):
    """EXACT copy of pose measurement from Colab jumping_jacks colab.py extract_jj_raw."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or not (10 < fps < 120):
        fps = 30.0
    fps = float(fps)

    rows = []
    with mp_pose.Pose(
        model_complexity=model_complexity,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    ) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            H, W = frame.shape[:2]
            res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if not res.pose_landmarks:
                rows.append([np.nan] * 22)
                continue
            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            vis = np.array([lm.visibility for lm in res.pose_landmarks.landmark], dtype=float)
            vis_L = float(np.nanmean([vis[LM["L_SH"]], vis[LM["L_HP"]], vis[LM["L_KN"]], vis[LM["L_AN"]]]))
            vis_R = float(np.nanmean([vis[LM["R_SH"]], vis[LM["R_HP"]], vis[LM["R_KN"]], vis[LM["R_AN"]]]))
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.concatenate([P2, np.zeros((P2.shape[0], 1))], axis=1)

            px_scale = pelvis_width_xy(P2) or np.nan
            y_floor = estimate_floor_y(P2, H=H)
            ankle_dist = np.linalg.norm(P2[LM["L_AN"]] - P2[LM["R_AN"]])
            leg_spread_norm = (ankle_dist / px_scale) if np.isfinite(px_scale) and px_scale > 0 else np.nan
            L_ank_h = (y_floor - P2[LM["L_AN"], 1]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan
            R_ank_h = (y_floor - P2[LM["R_AN"], 1]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan

            trunk_vec = (P3[LM["L_SH"]] + P3[LM["R_SH"]]) / 2.0 - (P3[LM["L_HP"]] + P3[LM["R_HP"]]) / 2.0
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
            sh3 = (P3[LM["L_SH"]] + P3[LM["R_SH"]]) / 2.0
            head_vec = ear3 - sh3
            neck_goni_deg = angle_between_vecs(trunk_vec, head_vec)

            hip_L = 180.0 - angle_3pt(P3[LM["L_SH"]], P3[LM["L_HP"]], P3[LM["L_KN"]])
            hip_R = 180.0 - angle_3pt(P3[LM["R_SH"]], P3[LM["R_HP"]], P3[LM["R_KN"]])
            knee_L = 180.0 - angle_3pt(P3[LM["L_HP"]], P3[LM["L_KN"]], P3[LM["L_AN"]])
            knee_R = 180.0 - angle_3pt(P3[LM["R_HP"]], P3[LM["R_KN"]], P3[LM["R_AN"]])

            sh2 = (P2[LM["L_SH"]] + P2[LM["R_SH"]]) / 2.0
            hp2 = (P2[LM["L_HP"]] + P2[LM["R_HP"]]) / 2.0
            hip_y_px = float(hp2[1])
            hip_y_norm = (hip_y_px / (px_scale + 1e-6)) if np.isfinite(px_scale) and px_scale > 0 else np.nan
            trunk2 = sh2 - hp2
            vertical_up = np.array([0.0, -1.0], dtype=float)
            trunk_flex_deg = angle_between_vecs(trunk2, vertical_up)

            rows.append([
                leg_spread_norm, L_ank_h, R_ank_h,
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

    cap.release()
    cols = [
        "leg_spread_norm", "L_ank_h", "R_ank_h",
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
    n0 = int(max(15, min(30, len(df))))
    hip_base = float(np.nanmean(df["hip_y_norm"].iloc[:n0])) if len(df) else np.nan
    df["hip_up_disp_norm"] = hip_base - df["hip_y_norm"]
    smooth_cols = [
        "leg_spread_norm", "L_ank_h", "R_ank_h",
        "L_sh_open_deg", "R_sh_open_deg",
        "L_hip_open_deg", "R_hip_open_deg",
        "neck_goni_deg", "trunk_flex_deg",
        "hip_L_deg", "hip_R_deg", "knee_L_deg", "knee_R_deg",
        "hip_y_norm", "hip_up_disp_norm",
        "vis_L_chain", "vis_R_chain",
    ]
    for c in smooth_cols:
        if c in df.columns:
            df[c] = rolling_med(df[c].to_numpy(), k=smooth_k)
    return df, fps

def detect_jumping_jacks_state_colab(df: pd.DataFrame, fps: float, age_years: int = 7):
    """EXACT copy of state detection from Colab"""
    
    # Age-dependent thresholds (exact Colab values)
    if age_years == 6:
        arm_open_thr, arm_closed_thr = 70.0, 50.0
        foot_open_thr, foot_closed_thr = 1.8, 1.2
    else:
        arm_open_thr, arm_closed_thr = 75.0, 55.0
        foot_open_thr, foot_closed_thr = 2.0, 1.5

    hysteresis_frames = max(3, int(0.15 * fps))

    # Arm and foot position detection
    arm_signal = ((df.get("arm_L_deg", pd.Series([np.nan])) < arm_open_thr) &
                  (df.get("arm_R_deg", pd.Series([np.nan])) < arm_open_thr)).astype(int)
    foot_signal = (df.get("foot_sep", pd.Series([np.nan])) > foot_open_thr).astype(int)

    # Apply hysteresis exactly as Colab
    def apply_hysteresis(signal, min_frames):
        state = np.zeros(len(signal), dtype=int)
        current_state = 0
        counter = 0
        
        for i, val in enumerate(signal):
            if np.isnan(val):
                state[i] = current_state
                continue
                
            val = int(val)
            if val != current_state:
                counter = 1
            else:
                counter += 1
                
            if counter >= min_frames:
                current_state = val
            state[i] = current_state
        return state

    arm_state = apply_hysteresis(arm_signal, hysteresis_frames)
    foot_state = apply_hysteresis(foot_signal, hysteresis_frames)
    
    # Combined state: 0=closed, 1=arms_only, 2=feet_only, 3=full_open
    combined_state = arm_state + 2 * foot_state

    return {
        "arm_state": arm_state,
        "foot_state": foot_state, 
        "combined_state": combined_state
    }

def count_jumping_jacks_reps_colab(states: Dict, fps: float, min_rep_duration: float = 0.8):
    """EXACT copy of rep counting from Colab"""
    
    combined = states["combined_state"]
    min_frames = max(3, int(min_rep_duration * fps))
    
    # Count full cycles: closed(0) -> open(3) -> closed(0)
    rep_count = 0
    last_state = None
    in_rep = False
    rep_frames = 0
    
    for state in combined:
        if state == 3:  # Full open
            if not in_rep:
                in_rep = True
                rep_frames = 1
            else:
                rep_frames += 1
        elif state == 0:  # Closed
            if in_rep and rep_frames >= min_frames:
                rep_count += 1
            in_rep = False
            rep_frames = 0

    return rep_count

def summarize_jumping_jacks_colab(df, fps, view):
    """EXACT copy from Colab jumping_jacks (4).py"""
    sway_abs = pd.Series(df.get("trunk_abs_deg", []), dtype=float).dropna()
    return {
        "sway_mean_deg": float(sway_abs.mean()) if len(sway_abs) else np.nan,
        "sway_sd_deg": float(sway_abs.std(ddof=0)) if len(sway_abs) else np.nan,
    }

def extract_jumping_jacks_metrics_colab_exact(front_video_path: Optional[str] = None, 
                                             side_video_path: Optional[str] = None,
                                             age_years: int = 7) -> Dict[str, Any]:
    """Extract jumping jacks metrics using exact Colab calculations - FIXED FOR SCORING"""
    print(f"[DEBUG JJ COLAB] extract_jumping_jacks_metrics called: front={front_video_path}, side={side_video_path}")
    
    # Colab: one row per student; main metrics from front_df, strategy from side_df (summarize_strategy).
    metrics = {
        "shoulder_abduction_angle_mean_deg": None,
        "hip_abduction_distance_mean_norm": None, 
        "hip_upward_displacement_mean_norm": None,
        "arm_leg_open_sync_mean_s": None,
        "arm_leg_close_sync_mean_s": None,
        "total_reps": 0,
        "fps": 30.0,
        "source_view": "front",
        "side_used_for_flexion": None,
        "neck_flex_mean_deg": None,
        "trunk_flex_mean_deg": None,
        "hip_flex_mean_deg": None,
        "knee_flex_mean_deg": None,
    }

    if front_video_path and os.path.exists(front_video_path):
        print(f"[DEBUG JJ COLAB] Processing front video: {front_video_path}")
        df_front, fps_front = measure_jumping_jacks_video_colab_exact(front_video_path, view="front")
        print(f"[DEBUG JJ COLAB] Front video: {len(df_front)} frames, fps={fps_front}")
        
        if len(df_front) > 10:
            metrics["fps"] = fps_front
            # EXACT copy from Colab jj_metrics_from_raw: same column names and logic
            spread = df_front["leg_spread_norm"].to_numpy()
            hip_y = df_front["hip_y_norm"].to_numpy()
            hip_up = df_front["hip_up_disp_norm"].to_numpy()
            Lsh = df_front["L_sh_open_deg"].to_numpy()
            Rsh = df_front["R_sh_open_deg"].to_numpy()
            arm_sig = np.nanmean(np.vstack([Lsh, Rsh]), axis=0)

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

            def safe_mean_arr(arr):
                s = pd.Series(arr, dtype=float).dropna()
                return float(s.mean()) if len(s) else np.nan

            def safe_max_arr(arr):
                s = pd.Series(arr, dtype=float).dropna()
                return float(s.max()) if len(s) else np.nan

            arm_close_low, arm_open_high = adaptive_arm_levels(arm_sig)
            leg_close_low, leg_open_high = adaptive_leg_levels(spread)
            jump_pack = adaptive_jump_mask(hip_y)
            if jump_pack is None:
                jump_thr, jump_mu = np.nan, np.nan
                jump_now = np.zeros(len(spread), dtype=bool)
            else:
                jump_thr, jump_mu = jump_pack
                jump_now = hip_y < (jump_mu - jump_thr)

            arm_open_state = hysteresis_state_from_levels(arm_sig, arm_close_low, arm_open_high)
            leg_open_state = hysteresis_state_from_levels(spread, leg_close_low, leg_open_high)

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
                leg_open_now = bool(leg_open_state[i])
                jump_now_i = bool(jump_now[i]) if i < len(jump_now) else False
                if state == "CLOSED":
                    if arm_open_now:
                        seen_arm_open = True
                    if leg_open_now:
                        seen_leg_open = True
                    if jump_now_i:
                        seen_jump = True
                    if seen_arm_open and seen_leg_open and seen_jump:
                        state = "OPENED"
                        open_start = i
                        seen_arm_close = False
                        seen_leg_close = False
                else:
                    if not arm_open_now:
                        seen_arm_close = True
                    if not leg_open_now:
                        seen_leg_close = True
                    if seen_arm_close and seen_leg_close:
                        reps += 1
                        if open_start is not None:
                            rep_windows.append((int(open_start), int(i)))
                            s0, s1 = open_start, i
                            rep_peak_shoulder.append(safe_max_arr(arm_sig[s0 : s1 + 1]))
                            rep_peak_legspread.append(safe_max_arr(spread[s0 : s1 + 1]))
                            rep_peak_hipup.append(safe_max_arr(hip_up[s0 : s1 + 1]))
                        state = "CLOSED"
                        seen_arm_open = False
                        seen_leg_open = False
                        seen_jump = False
                        open_start = None

            if state == "OPENED":
                partial_reps = 1

            # Arm-leg sync inside rep windows (EXACT Colab logic)
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

            L_arm_state = hysteresis_state_from_levels(Lsh, *adaptive_arm_levels(Lsh))
            R_arm_state = hysteresis_state_from_levels(Rsh, *adaptive_arm_levels(Rsh))
            arms_both_open = L_arm_state & R_arm_state
            A_open_idx = rising_edges(arms_both_open)
            A_close_idx = falling_edges(arms_both_open)
            G_open_idx = rising_edges(leg_open_state)
            G_close_idx = falling_edges(leg_open_state)
            arm_leg_open_dt = []
            arm_leg_close_dt = []
            fps = float(fps_front) if fps_front and fps_front > 0 else 30.0
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

            metrics["shoulder_abduction_angle_mean_deg"] = safe_mean_arr(rep_peak_shoulder)
            metrics["hip_abduction_distance_mean_norm"] = safe_mean_arr(rep_peak_legspread)
            metrics["hip_upward_displacement_mean_norm"] = safe_mean_arr(rep_peak_hipup)
            metrics["total_reps"] = reps
            metrics["arm_leg_open_sync_mean_s"] = float(np.nanmean(arm_leg_open_dt)) if len(arm_leg_open_dt) else np.nan
            metrics["arm_leg_close_sync_mean_s"] = float(np.nanmean(arm_leg_close_dt)) if len(arm_leg_close_dt) else np.nan

    if side_video_path and os.path.exists(side_video_path):
        df_side, fps_side = measure_jumping_jacks_video_colab_exact(side_video_path, view="side")
        if len(df_side) > 10:
            if metrics["hip_abduction_distance_mean_norm"] is None and "leg_spread_norm" in df_side.columns:
                s = pd.Series(df_side["leg_spread_norm"], dtype=float).dropna()
                if len(s) > 0:
                    metrics["hip_abduction_distance_mean_norm"] = float(s.mean())
            if metrics["fps"] is None and fps_side:
                metrics["fps"] = fps_side
            # Colab: summarize_strategy(side_df) adds strategy fields to the single output row
            def mean_or_nan(x):
                t = pd.Series(x, dtype=float).dropna()
                return float(t.mean()) if len(t) else np.nan
            if "vis_L_chain" in df_side.columns and "vis_R_chain" in df_side.columns:
                vL = mean_or_nan(df_side["vis_L_chain"].to_numpy())
                vR = mean_or_nan(df_side["vis_R_chain"].to_numpy())
                side_used = "L" if (np.isfinite(vL) and np.isfinite(vR) and vL >= vR) else "R"
                metrics["side_used_for_flexion"] = side_used
                if "neck_goni_deg" in df_side.columns:
                    metrics["neck_flex_mean_deg"] = mean_or_nan(df_side["neck_goni_deg"].to_numpy())
                if "trunk_flex_deg" in df_side.columns:
                    metrics["trunk_flex_mean_deg"] = mean_or_nan(df_side["trunk_flex_deg"].to_numpy())
                if side_used == "L" and "hip_L_deg" in df_side.columns:
                    metrics["hip_flex_mean_deg"] = mean_or_nan(df_side["hip_L_deg"].to_numpy())
                elif side_used == "R" and "hip_R_deg" in df_side.columns:
                    metrics["hip_flex_mean_deg"] = mean_or_nan(df_side["hip_R_deg"].to_numpy())
                if side_used == "L" and "knee_L_deg" in df_side.columns:
                    metrics["knee_flex_mean_deg"] = mean_or_nan(df_side["knee_L_deg"].to_numpy())
                elif side_used == "R" and "knee_R_deg" in df_side.columns:
                    metrics["knee_flex_mean_deg"] = mean_or_nan(df_side["knee_R_deg"].to_numpy())
    return metrics

def process_jumping_jacks(
    front_video_path: Optional[str],
    side_video_path: Optional[str], 
    age_years: int
) -> Dict[str, Any]:
    """Process jumping jacks videos using exact Colab calculations"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_jumping_jacks
    
    # Handle MOV files - try to convert if needed
    if front_video_path and os.path.exists(front_video_path):
        front_video_path, front_err = ensure_video_readable(front_video_path)
        if front_err:
            return {
                "rawMetrics": {}, "scores": {},
                "totalScore": 0, "maxScore": 36,
                "interpretation": f"Error (front video): {front_err}"
            }
    
    if side_video_path and os.path.exists(side_video_path):
        side_video_path, side_err = ensure_video_readable(side_video_path)
        if side_err:
            return {
                "rawMetrics": {}, "scores": {},
                "totalScore": 0, "maxScore": 36,
                "interpretation": f"Error (side video): {side_err}"
            }
    
    print(f"[DEBUG JJ COLAB] Processing: age_years={age_years}")
    
    raw_metrics = extract_jumping_jacks_metrics_colab_exact(front_video_path, side_video_path, age_years)
    
    print(f"[DEBUG JJ COLAB] Raw metrics extracted: {raw_metrics}")
    
    if raw_metrics["shoulder_abduction_angle_mean_deg"] is None and raw_metrics["hip_abduction_distance_mean_norm"] is None:
        print("[DEBUG JJ COLAB] ERROR: No valid pose data extracted")
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 36,
            "interpretation": "Error: No valid pose data extracted from videos."
        }
    
    score_result = score_jumping_jacks(raw_metrics, age_years=age_years)
    print(f"[DEBUG JJ COLAB] Score result: {score_result}")
    max_score = score_result.get("max_total") or 36

    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": max_score,
        "interpretation": score_result.get("interpretation", "N/A"),
    }