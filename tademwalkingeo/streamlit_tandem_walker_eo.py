#!/usr/bin/env python3
"""
Streamlit Tandem Walking Eyes Open Assessment & Scoring App
Based on tademmanin (3).py preprocessing and math_tandem_walking_eo.py scoring
"""

import streamlit as st
import pandas as pd
import numpy as np
import cv2
import os
import tempfile
import importlib.util
from io import BytesIO
from collections import deque
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional
import warnings

# Import scoring functions from local math_tandem_walking_eo.py file
import sys
import os

# Load the local math_tandem_walking_eo.py file explicitly
math_file_path = os.path.join(os.path.dirname(__file__), 'math_tandem_walking_eo.py')
spec = importlib.util.spec_from_file_location("tandem_eo_scoring_math", math_file_path)
tandem_eo_scoring_math = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tandem_eo_scoring_math)

# Extract the functions we need for both age groups
# 6-year functions
score_ml_mean_eo_6y = tandem_eo_scoring_math.score_ml_mean_eo_6y
score_ml_sd_eo_6y = tandem_eo_scoring_math.score_ml_sd_eo_6y
score_ap_mean_eo_6y = tandem_eo_scoring_math.score_ap_mean_eo_6y
score_ap_sd_eo_6y = tandem_eo_scoring_math.score_ap_sd_eo_6y
score_step_gap_eo_6y = tandem_eo_scoring_math.score_step_gap_eo_6y
score_row_tandem_eo_6y = tandem_eo_scoring_math.score_row_tandem_eo_6y

# 7-year functions
score_ml_mean_eo_7y = tandem_eo_scoring_math.score_ml_mean_eo_7y
score_ml_sd_eo_7y = tandem_eo_scoring_math.score_ml_sd_eo_7y
score_ap_mean_eo_7y = tandem_eo_scoring_math.score_ap_mean_eo_7y
score_ap_sd_eo_7y = tandem_eo_scoring_math.score_ap_sd_eo_7y
score_step_gap_eo_7y = tandem_eo_scoring_math.score_step_gap_eo_7y
score_row_tandem_eo_7y = tandem_eo_scoring_math.score_row_tandem_eo_7y

# Unified scoring function
score_row_tandem_eo = tandem_eo_scoring_math.score_row_tandem_eo

# MediaPipe setup - import with error handling
try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    PL = mp_pose.PoseLandmark
except ImportError as e:
    st.error(f"❌ MediaPipe not installed or incompatible. Please install: pip install mediapipe")
    st.stop()
except AttributeError as e:
    st.error(f"❌ MediaPipe version issue. Please update: pip install --upgrade mediapipe")
    st.stop()

# Configuration
CONFIG = {
    "FRAME_STRIDE": 2,
    "DOWNSCALE": 1.0,              # 1.0 = no resize
    "MODEL_COMPLEXITY": 1,
    "MAX_FRAMES": None,            # or int
    "MAT_LENGTH_CM": 250.0,
    "VEL_THRESH_NORM": 0.002,      # MediaPipe normalized coords
    "STABILITY_WINDOW": 5,         # frames
    "MIN_EVENT_GAP_FRAMES": 5,     # debounce contacts
    "ANGLE_WINDOW_SEC": 0.25,
    "EXPECTED_FOOT_LEN_CM": 18.0,    # child (6–7 yrs)
    "EXPECTED_HIP_WIDTH_CM": 18.0,   # fallback
    "MAX_TANDEM_GAP_CM": 5.0,
    "PELVIS_WIDTH_CM": 18.0,       # used to estimate px/cm if no mat scale present
}

# Landmark indices
LM = {
    "NOSE": int(PL.NOSE),
    "L_EYE": int(PL.LEFT_EYE_INNER),
    "R_EYE": int(PL.RIGHT_EYE_INNER),
    "L_EAR": int(PL.LEFT_EAR),
    "R_EAR": int(PL.RIGHT_EAR),

    "L_SH": int(PL.LEFT_SHOULDER),
    "R_SH": int(PL.RIGHT_SHOULDER),
    "L_HP": int(PL.LEFT_HIP),
    "R_HP": int(PL.RIGHT_HIP),
    "L_KN": int(PL.LEFT_KNEE),
    "R_KN": int(PL.RIGHT_KNEE),
    "L_AN": int(PL.LEFT_ANKLE),
    "R_AN": int(PL.RIGHT_ANKLE),

    "L_HEEL": int(PL.LEFT_HEEL),
    "R_HEEL": int(PL.RIGHT_HEEL),
    "L_TOE": int(PL.LEFT_FOOT_INDEX),
    "R_TOE": int(PL.RIGHT_FOOT_INDEX),
}

@dataclass
class ContactEvent:
    frame_idx: int   # row index in df
    foot: str        # "L" or "R"

# Helper functions
def _finite(a):
    a = np.asarray(a, dtype=float)
    return a[np.isfinite(a)]

def _nanmedian_safe(x):
    x = _finite(x)
    return float(np.nanmedian(x)) if x.size else None

def _mean_safe(x):
    x = _finite(x)
    return float(np.nanmean(x)) if x.size else None

def _wrap_deg(a):
    a = (a + 180.0) % 360.0 - 180.0
    return a

def _P2(df: pd.DataFrame, idx: int) -> np.ndarray:
    """Nx2 pixel coords for landmark idx."""
    cx, cy = f"x{idx}", f"y{idx}"
    if cx not in df.columns or cy not in df.columns:
        return np.full((len(df), 2), np.nan, dtype=float)
    return np.column_stack([df[cx].to_numpy(float), df[cy].to_numpy(float)])

def _P2N(df: pd.DataFrame, idx: int) -> np.ndarray:
    """Nx2 normalized coords for landmark idx."""
    cx, cy = f"xn{idx}", f"yn{idx}"
    if cx not in df.columns or cy not in df.columns:
        return np.full((len(df), 2), np.nan, dtype=float)
    return np.column_stack([df[cx].to_numpy(float), df[cy].to_numpy(float)])

def _mid(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (np.asarray(a, float) + np.asarray(b, float)) / 2.0

def angle_3pt(a, b, c, eps=1e-8) -> float:
    """Angle ABC (in degrees). Works for 2D or 3D."""
    a = np.asarray(a, float); b = np.asarray(b, float); c = np.asarray(c, float)
    if not (np.isfinite(a).all() and np.isfinite(b).all() and np.isfinite(c).all()):
        return float("nan")
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < eps or nbc < eps:
        return float("nan")
    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = np.clip(cosang, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosang)))

def run_pose_fast(
    video_path: str,
    frame_stride: int = 2,
    downscale: float = 1.0,
    model_complexity: int = 1,
    max_frames: Optional[int] = None,
    include_world: bool = True,
    progress_bar=None
) -> Tuple[pd.DataFrame, float]:
    """
    Returns (df, fps). df has columns:
      i, t, w, h,
      x{idx}, y{idx}, xn{idx}, yn{idx}, vis{idx},
      and optionally xw{idx}, yw{idx}, zw{idx} for world coords.
    """
    if not isinstance(video_path, str) or not os.path.exists(video_path):
        return pd.DataFrame(), 30.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return pd.DataFrame(), 30.0

    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = float(fps) if fps and fps > 1e-3 else 30.0
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=int(model_complexity),
        enable_segmentation=False,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    rows = []
    frame_idx = 0
    kept = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if progress_bar and total_frames > 0:
                progress_bar.progress(min(frame_idx / total_frames, 1.0))

            if frame_idx % frame_stride == 0:
                h, w = frame.shape[:2]
                if downscale != 1.0 and downscale > 0:
                    nw, nh = int(w * downscale), int(h * downscale)
                    if nw > 0 and nh > 0:
                        frame = cv2.resize(frame, (nw, nh))
                        h, w = nh, nw

                # Process with MediaPipe
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)

                row = {
                    "i": kept,
                    "t": frame_idx / fps if fps > 0 else frame_idx / 30.0,
                    "w": w,
                    "h": h
                }

                if result.pose_landmarks:
                    for i, lm in enumerate(result.pose_landmarks.landmark):
                        row[f"x{i}"] = lm.x * w
                        row[f"y{i}"] = lm.y * h
                        row[f"xn{i}"] = lm.x
                        row[f"yn{i}"] = lm.y
                        row[f"vis{i}"] = lm.visibility

                        if include_world and result.pose_world_landmarks:
                            wlm = result.pose_world_landmarks.landmark[i]
                            row[f"xw{i}"] = wlm.x
                            row[f"yw{i}"] = wlm.y
                            row[f"zw{i}"] = wlm.z

                rows.append(row)
                kept += 1

                if max_frames and kept >= max_frames:
                    break

            frame_idx += 1
    except Exception:
        pass
    finally:
        cap.release()
        pose.close()

    df = pd.DataFrame(rows)
    return df, fps

def infer_walk_axis_from_midhip(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """PCA on mid-hip pixel trajectory -> (origin, unit axis)."""
    hip = _mid(_P2(df, LM["L_HP"]), _P2(df, LM["R_HP"]))
    ok = np.isfinite(hip).all(axis=1)
    H = hip[ok]
    if H.shape[0] < 5:
        # fallback: vertical axis
        origin = np.nanmedian(hip, axis=0)
        axis = np.array([0.0, 1.0], float)
        return origin, axis

    Hc = H - np.mean(H, axis=0, keepdims=True)
    cov = np.cov(Hc.T)
    w, V = np.linalg.eig(cov)
    axis = V[:, int(np.argmax(w))].astype(float)
    axis = axis / (np.linalg.norm(axis) + 1e-9)

    origin = np.nanmedian(H, axis=0).astype(float)

    # choose sign: projection should increase over time
    proj = (hip - origin) @ axis
    proj_ok = proj[np.isfinite(proj)]
    if proj_ok.size >= 2 and proj_ok[-1] < proj_ok[0]:
        axis = -axis

    return origin, axis

def calibrate_side(video_path: str, progress_bar=None):
    """Calibrate walking axis/origin for the PROFILE (side) view."""
    try:
        df, fps = run_pose_fast(
            video_path,
            frame_stride=max(1, CONFIG.get("FRAME_STRIDE", 1)),
            downscale=float(CONFIG.get("DOWNSCALE", 1.0)),
            model_complexity=int(CONFIG.get("MODEL_COMPLEXITY", 1)),
            max_frames=250,
            include_world=False,
            progress_bar=progress_bar
        )
    except Exception:
        df, fps = pd.DataFrame(), 30.0

    # Default origin/axis from first frame if pose fails
    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read()
    cap.release()
    if ok and frame is not None:
        h, w = frame.shape[:2]
        origin0 = np.array([w / 2.0, h / 2.0], dtype=float)
    else:
        origin0 = np.array([0.0, 0.0], dtype=float)

    axis0 = np.array([0.0, 1.0], dtype=float)

    if df is None or len(df) < 10:
        return dict(origin=origin0, axis=axis0, ppc=float('nan'))

    origin, axis = infer_walk_axis_from_midhip(df)
    return dict(origin=origin, axis=axis, ppc=float('nan'))

def trunk_sway_from_baseline(df: pd.DataFrame) -> np.ndarray:
    """Angle of trunk vector (mid-hip->mid-shoulder) across frames, baseline-subtracted (degrees)."""
    SHO = _mid(_P2(df, LM["L_SH"]), _P2(df, LM["R_SH"]))
    HIP = _mid(_P2(df, LM["L_HP"]), _P2(df, LM["R_HP"]))
    v = SHO - HIP
    theta = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    if not np.any(np.isfinite(theta)):
        return np.full_like(theta, np.nan, dtype=float)
    base = float(np.nanmedian(theta))
    dev = _wrap_deg(theta - base)
    return dev

def detect_contacts_velocity_stability(
    df: pd.DataFrame,
    fps: float,
    window: int = 5,
    vel_thresh_norm: float = 0.002,
    min_gap_frames: int = 5,
    vis_thresh: float = 0.3
) -> Tuple[List[ContactEvent], int, int]:
    """
    Detect contact instants using toe (FOOT_INDEX) stability in normalized coords.
    """
    L_toe = _P2N(df, LM["L_TOE"])
    R_toe = _P2N(df, LM["R_TOE"])
    L_vis = df.get(f"vis{LM['L_TOE']}", pd.Series([np.nan]*len(df))).to_numpy(float)
    R_vis = df.get(f"vis{LM['R_TOE']}", pd.Series([np.nan]*len(df))).to_numpy(float)

    def vel(p, pprev):
        if not (np.isfinite(p).all() and np.isfinite(pprev).all()):
            return float('inf')
        return float(np.hypot(p[0] - pprev[0], p[1] - pprev[1]))

    Lbuf, Rbuf = deque(maxlen=window), deque(maxlen=window)
    prev_L_stable = False
    prev_R_stable = False
    last_contact: Optional[str] = None
    last_event_frame = -10**9

    events: List[ContactEvent] = []
    nL = nR = 0

    for k in range(1, len(df)):
        lv = vel(L_toe[k], L_toe[k-1])
        rv = vel(R_toe[k], R_toe[k-1])

        # if visibility low or invalid -> reset buffers
        if not np.isfinite(lv) or not (np.isfinite(L_toe[k]).all()) or L_vis[k] < vis_thresh:
            Lbuf.clear()
            L_stable = False
        else:
            Lbuf.append(lv < vel_thresh_norm)
            L_stable = len(Lbuf) == window and all(Lbuf)

        if not np.isfinite(rv) or not (np.isfinite(R_toe[k]).all()) or R_vis[k] < vis_thresh:
            Rbuf.clear()
            R_stable = False
        else:
            Rbuf.append(rv < vel_thresh_norm)
            R_stable = len(Rbuf) == window and all(Rbuf)

        # rising edges only
        L_edge = (L_stable and not prev_L_stable)
        R_edge = (R_stable and not prev_R_stable)

        if (k - last_event_frame) < int(min_gap_frames):
            L_edge = R_edge = False

        # First contact: choose whichever stabilizes first
        if last_contact is None:
            if L_edge and not R_edge:
                events.append(ContactEvent(k, "L"))
                last_contact, last_event_frame = "L", k
                nL += 1
            elif R_edge and not L_edge:
                events.append(ContactEvent(k, "R"))
                last_contact, last_event_frame = "R", k
                nR += 1
            elif L_edge and R_edge:
                # both: pick left arbitrarily
                events.append(ContactEvent(k, "L"))
                last_contact, last_event_frame = "L", k
                nL += 1
        else:
            # alternating logic
            if last_contact == "L" and R_edge:
                events.append(ContactEvent(k, "R"))
                last_contact, last_event_frame = "R", k
                nR += 1
            elif last_contact == "R" and L_edge:
                events.append(ContactEvent(k, "L"))
                last_contact, last_event_frame = "L", k
                nL += 1

        prev_L_stable = L_stable
        prev_R_stable = R_stable

    return events, nL, nR

def compute_step_metrics(df, placements, origin, axis, ppc_unused):
    """
    Tandem Walking step metrics computation.
    """
    def _get_frame_foot(ev):
        if isinstance(ev, dict):
            return ev["frame_idx"], ev["foot"]
        if isinstance(ev, (list, tuple)) and len(ev) >= 2:
            return ev[0], ev[1]
        if hasattr(ev, "frame_idx") and hasattr(ev, "foot"):
            return ev.frame_idx, ev.foot
        raise TypeError(f"Unknown placement type: {type(ev)}")

    def _isfinite2(p):
        return p is not None and np.isfinite(p).all()

    steps = []
    if placements is None or len(placements) < 2:
        return steps

    # Normalize walking axis
    axis = np.asarray(axis, dtype=float)
    n = np.linalg.norm(axis)
    axis = axis / n if np.isfinite(n) and n > 1e-8 else np.array([0.0, 1.0], dtype=float)

    # PPC (px/cm): use foot-length estimation
    ppc_used = float("nan")
    EXPECTED_FOOT_CM = float(CONFIG.get("EXPECTED_FOOT_LEN_CM", 18.0))

    foot_px = []
    for ev in placements:
        f, foot = _get_frame_foot(ev)
        if f >= len(df):
            continue
        heel = _P2(df, LM["L_HEEL"] if foot == "L" else LM["R_HEEL"])[f]
        toe = _P2(df, LM["L_TOE"] if foot == "L" else LM["R_TOE"])[f]
        if _isfinite2(heel) and _isfinite2(toe):
            foot_px.append(float(np.linalg.norm(heel - toe)))

    foot_px = np.asarray(foot_px, float)
    if foot_px.size >= 3 and EXPECTED_FOOT_CM > 0:
        ppc_used = float(np.nanmedian(foot_px)) / EXPECTED_FOOT_CM

    if not (np.isfinite(ppc_used) and ppc_used > 1e-6):
        ppc_used = 3.0  # fallback

    MAX_TANDEM_GAP_CM = float(CONFIG.get("MAX_TANDEM_GAP_CM", 5.0))

    # Iterate consecutive placements
    for k in range(1, len(placements)):
        f0, foot0 = _get_frame_foot(placements[k - 1])  # previous contact (trailing)
        f1, foot1 = _get_frame_foot(placements[k])      # current contact (leading)

        # enforce alternation
        if foot0 == foot1:
            continue

        # points we need
        prev_heel = _P2(df, LM["L_HEEL"] if foot0 == "L" else LM["R_HEEL"])[f0]
        prev_toe = _P2(df, LM["L_TOE"] if foot0 == "L" else LM["R_TOE"])[f0]
        lead_heel = _P2(df, LM["L_HEEL"] if foot1 == "L" else LM["R_HEEL"])[f1]
        lead_toe = _P2(df, LM["L_TOE"] if foot1 == "L" else LM["R_TOE"])[f1]

        if not (_isfinite2(prev_heel) and _isfinite2(prev_toe) and _isfinite2(lead_heel) and _isfinite2(lead_toe)):
            continue

        # stride (heel->heel) along axis
        stride_px = abs(float(np.dot((lead_heel - prev_heel), axis)))

        # tandem signed gap (lead heel vs prev toe) along axis
        signed_gap_px = float(np.dot((lead_heel - prev_toe), axis))
        gap_px = max(0.0, signed_gap_px)

        # leading foot length
        foot_len_px = float(np.linalg.norm(lead_heel - lead_toe))

        # convert to cm
        step_gap_cm = gap_px / ppc_used if np.isfinite(ppc_used) and ppc_used > 0 else None
        if step_gap_cm is not None and step_gap_cm > MAX_TANDEM_GAP_CM:
            step_gap_cm = None  # outlier

        # NSD (normalized step distance)
        nsd = stride_px / foot_len_px if np.isfinite(foot_len_px) and foot_len_px > 1e-6 else None

        # understep (boolean)
        understep = bool(signed_gap_px < 0) if np.isfinite(signed_gap_px) else False

        steps.append({
            "i": k-1,
            "frame_idx": f1,
            "foot": foot1,
            "step_gap_cm": step_gap_cm,
            "nsd": nsd,
            "hgtd_cm": signed_gap_px / ppc_used if np.isfinite(ppc_used) and ppc_used > 0 else None,
            "understep": understep,
            "raw_step_px": stride_px,
            "foot_len_px": foot_len_px,
            "ppc_used": ppc_used,
            "outlier": step_gap_cm is None
        })

    return steps

def process_tandem_walking(side_video_path, front_video_path=None, progress_bar=None):
    """
    Main processing function for tandem walking analysis.
    Returns dict with all computed metrics.
    """
    results = {
        "ml_sway_mean_deg": None,
        "ml_sway_sd_deg": None,
        "ap_sway_mean_deg": None,
        "ap_sway_sd_deg": None,
        "mean_step_gap_cm": None,
        "n_understeps": 0,
        "n_L_contacts": 0,
        "n_R_contacts": 0,
        "n_steps_used": 0,
        "processing_success": False
    }

    try:
        # Calibrate side view
        calib = calibrate_side(side_video_path, progress_bar)
        
        # Process side video for AP sway and step detection
        df_side, fps = run_pose_fast(
            side_video_path,
            frame_stride=CONFIG["FRAME_STRIDE"],
            downscale=CONFIG["DOWNSCALE"],
            model_complexity=CONFIG["MODEL_COMPLEXITY"],
            max_frames=CONFIG.get("MAX_FRAMES", None),
            include_world=True,
            progress_bar=progress_bar
        )
        
        if df_side is None or len(df_side) < 10:
            return results

        # Ensure frame index column
        if "i" not in df_side.columns:
            df_side["i"] = range(len(df_side))

        # AP sway from side view
        try:
            ap_sway_deg = trunk_sway_from_baseline(df_side)
            results["ap_sway_mean_deg"] = float(np.nanmean(np.abs(ap_sway_deg))) if np.any(np.isfinite(ap_sway_deg)) else None
            results["ap_sway_sd_deg"] = float(np.nanstd(ap_sway_deg, ddof=0)) if np.any(np.isfinite(ap_sway_deg)) else None
        except Exception:
            pass

        # Step detection
        events, nL, nR = detect_contacts_velocity_stability(
            df_side, fps,
            window=CONFIG["STABILITY_WINDOW"],
            vel_thresh_norm=CONFIG["VEL_THRESH_NORM"],
            min_gap_frames=CONFIG["MIN_EVENT_GAP_FRAMES"]
        )
        
        results["n_L_contacts"] = nL
        results["n_R_contacts"] = nR

        # Step metrics
        if events and len(events) >= 2:
            steps = compute_step_metrics(df_side, events, calib["origin"], calib["axis"], calib["ppc"])
            
            if steps:
                df_steps = pd.DataFrame(steps)
                results["n_steps_used"] = len(df_steps)
                
                # Mean step gap
                gaps = df_steps["step_gap_cm"].to_numpy(float)
                gaps = gaps[np.isfinite(gaps)]
                if gaps.size > 0:
                    results["mean_step_gap_cm"] = float(np.nanmean(gaps))
                
                # Understeps
                results["n_understeps"] = int(df_steps["understep"].astype(bool).sum())

        # Process front video for ML sway if available
        if front_video_path and os.path.exists(front_video_path):
            try:
                df_front, fps_front = run_pose_fast(
                    front_video_path,
                    frame_stride=CONFIG["FRAME_STRIDE"],
                    downscale=CONFIG["DOWNSCALE"],
                    model_complexity=CONFIG["MODEL_COMPLEXITY"],
                    max_frames=CONFIG.get("MAX_FRAMES", None),
                    include_world=False,
                    progress_bar=progress_bar
                )
                
                if df_front is not None and len(df_front) >= 10:
                    # ML sway from front view
                    ml_sway_deg = trunk_sway_from_baseline(df_front)
                    if np.any(np.isfinite(ml_sway_deg)):
                        results["ml_sway_mean_deg"] = float(np.nanmean(np.abs(ml_sway_deg)))
                        results["ml_sway_sd_deg"] = float(np.nanstd(ml_sway_deg, ddof=0))
            except Exception:
                pass

        results["processing_success"] = True
        
    except Exception as e:
        st.error(f"Error in processing: {str(e)}")
    
    return results

def main():
    st.set_page_config(page_title="Tandem Walking EO Scorer", layout="wide")
    
    st.title("👣 Tandem Walking Eyes Open Assessment & Scoring")
    st.markdown("Upload **Side** and **Front** view videos to get automated tandem walking scores using age-appropriate rubrics (6-year or 7-year).")
    
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
            st.info("📊 **6 Years EO Scoring**: Max Score = 34 points (ML Mean: 6, ML SD: 7, AP Mean: 7, AP SD: 8, Step Gap: 6)")
        else:
            st.info("📊 **7 Years EO Scoring**: Max Score = 35 points (ML Mean: 6, ML SD: 7, AP Mean: 8, AP SD: 8, Step Gap: 6)")
    
    st.divider()
    
    # Video upload section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📹 Side View Video (Required)")
        side_video = st.file_uploader(
            "Upload Side/Profile View",
            type=["mp4", "mov", "avi", "mkv"],
            key="side",
            help="Side view video is required for step detection and AP sway analysis"
        )
    
    with col2:
        st.subheader("📹 Front View Video (Optional)")
        front_video = st.file_uploader(
            "Upload Front View",
            type=["mp4", "mov", "avi", "mkv"],
            key="front",
            help="Front view video provides ML sway analysis for complete scoring"
        )
    
    # Processing section
    st.divider()
    
    if st.button("🚀 Process Videos & Calculate Scores", type="primary", use_container_width=True, disabled=not age_selected):
        
        if not side_video:
            st.error("❌ Please upload a side view video file to process.")
            st.stop()
        
        if not age_selected:
            st.error("❌ Please select an age group before processing.")
            st.stop()
        
        # Display selected scoring system
        st.success(f"✅ Using {age_group} scoring rubric for tandem walking eyes open assessment")
        
        # Process Videos
        with st.spinner("🎥 Processing videos..."):
            # Save uploaded files temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_side:
                tmp_side.write(side_video.read())
                tmp_side_path = tmp_side.name
            
            tmp_front_path = None
            if front_video:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_front:
                    tmp_front.write(front_video.read())
                    tmp_front_path = tmp_front.name
            
            try:
                # Add progress bar
                progress_bar = st.progress(0)
                st.text("📊 Analyzing gait patterns and calculating metrics...")
                
                # Process the videos
                results = process_tandem_walking(
                    tmp_side_path, 
                    tmp_front_path,
                    progress_bar=progress_bar
                )
                
                progress_bar.progress(1.0)
                
                if not results["processing_success"]:
                    st.error("❌ Could not extract gait data from videos. Please ensure the videos show clear walking motion.")
                    return
                
                st.success("✅ Video processing complete!")
                
                st.subheader(f"📊 {age_group} Rubric - Calculated Parameters & Scores")
                
                # Score using age-appropriate functions
                scores = score_row_tandem_eo(results, age_years)
                
                # Display results in a clean table
                results_data = [
                    {
                        "Parameter": "ML Sway Mean",
                        "Raw Value": f"{results['ml_sway_mean_deg']:.2f}°" if results['ml_sway_mean_deg'] is not None else "N/A",
                        "Score": scores.get("ml_sway_mean_score", "N/A"),
                        "Description": "Average mediolateral trunk sway (front view)"
                    },
                    {
                        "Parameter": "ML Sway SD", 
                        "Raw Value": f"{results['ml_sway_sd_deg']:.2f}°" if results['ml_sway_sd_deg'] is not None else "N/A",
                        "Score": scores.get("ml_sway_sd_score", "N/A"),
                        "Description": "Variability of mediolateral trunk sway (front view)"
                    },
                    {
                        "Parameter": "AP Sway Mean",
                        "Raw Value": f"{results['ap_sway_mean_deg']:.2f}°" if results['ap_sway_mean_deg'] is not None else "N/A",
                        "Score": scores.get("ap_sway_mean_score", "N/A"),
                        "Description": "Average anteroposterior trunk sway (side view)"
                    },
                    {
                        "Parameter": "AP Sway SD",
                        "Raw Value": f"{results['ap_sway_sd_deg']:.2f}°" if results['ap_sway_sd_deg'] is not None else "N/A",
                        "Score": scores.get("ap_sway_sd_score", "N/A"),
                        "Description": "Variability of anteroposterior trunk sway (side view)"
                    },
                    {
                        "Parameter": "Mean Step Gap",
                        "Raw Value": f"{results['mean_step_gap_cm']:.2f} cm" if results['mean_step_gap_cm'] is not None else "N/A",
                        "Score": scores.get("step_gap_score", "N/A"),
                        "Description": "Average heel-to-toe distance between steps"
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
                max_score = scores.get("max_score", 34 if age_years == 6 else 35)
                
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
                    st.write("**Gait Performance:**")
                    st.write(f"• Total steps detected: {results['n_steps_used']}")
                    st.write(f"• Left foot contacts: {results['n_L_contacts']}")
                    st.write(f"• Right foot contacts: {results['n_R_contacts']}")
                    st.write(f"• Understeps (overlaps): {results['n_understeps']}")
                
                with col_right:
                    st.write("**Video Analysis:**")
                    st.write(f"• Side view processed: ✅")
                    st.write(f"• Front view processed: {'✅' if front_video else '❌ Not provided'}")
                    if not front_video:
                        st.warning("⚠️ Upload front view video for complete ML sway analysis")
                
                # Comparison with eyes closed performance
                with st.expander("🔍 Eyes Open vs Eyes Closed Comparison"):
                    st.write("**Expected Differences (Eyes Open vs Closed):**")
                    st.write("• **Better balance control** - Lower sway values expected with eyes open")
                    st.write("• **More precise stepping** - Smaller step gaps and fewer understeps")
                    st.write("• **Visual feedback advantage** - Better spatial awareness for tandem placement")
                    
                    if results['mean_step_gap_cm'] is not None:
                        if results['mean_step_gap_cm'] <= 1.5:
                            st.success("✅ Excellent step precision - typical of eyes open performance")
                        elif results['mean_step_gap_cm'] <= 3.0:
                            st.info("📊 Good step control with visual input")
                        else:
                            st.warning("⚠️ Consider vision or balance assessment")
                
                # Advanced metrics
                with st.expander("🔍 Advanced Gait Analysis"):
                    st.write("**Step Quality Metrics:**")
                    if results['mean_step_gap_cm'] is not None:
                        gap_quality = "Excellent" if results['mean_step_gap_cm'] <= 1.0 else \
                                     "Good" if results['mean_step_gap_cm'] <= 2.0 else \
                                     "Fair" if results['mean_step_gap_cm'] <= 3.0 else "Needs improvement"
                        st.write(f"• Step gap quality: {gap_quality}")
                    
                    st.write(f"• Understep rate: {results['n_understeps']}/{results['n_steps_used']} steps" if results['n_steps_used'] > 0 else "• No steps detected")
                    
                    st.write("**Sway Analysis:**")
                    if results['ap_sway_mean_deg'] is not None:
                        st.write(f"• AP sway magnitude: {results['ap_sway_mean_deg']:.2f}° (avg), {results['ap_sway_sd_deg']:.2f}° (SD)")
                    if results['ml_sway_mean_deg'] is not None:
                        st.write(f"• ML sway magnitude: {results['ml_sway_mean_deg']:.2f}° (avg), {results['ml_sway_sd_deg']:.2f}° (SD)")
                
                # Download results as CSV
                st.divider()
                
                # Combine all results for export
                export_data = {
                    "Student": student_name or "Unknown",
                    "Age Group": age_group,
                    **results,
                    **scores,
                }
                
                export_df = pd.DataFrame([export_data])
                csv_data = export_df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Complete Results as CSV",
                    data=csv_data,
                    file_name=f"tandem_walking_eo_results_{student_name if student_name else 'student'}.csv",
                    mime="text/csv"
                )
            
            except Exception as e:
                st.error(f"❌ Error processing videos: {str(e)}")
            finally:
                # Clean up temporary files
                if os.path.exists(tmp_side_path):
                    os.unlink(tmp_side_path)
                if tmp_front_path and os.path.exists(tmp_front_path):
                    os.unlink(tmp_front_path)

if __name__ == "__main__":
    main()