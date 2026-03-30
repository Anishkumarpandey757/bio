
"""
Fixed Tandem Walking backend for Colab/backend use.

What is fixed:
- Removes approximate variance-based fake step-gap calculation.
- Uses notebook-style pose extraction + toe-stability contact detection.
- Computes step_gap_cm as heel-to-previous-toe spacing along walking axis.
- Gives stable ML/AP sway and realistic step metrics.
"""

import os
from dataclasses import dataclass
from collections import deque
from typing import Dict, Any, Tuple, Optional, List

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
PL = mp_pose.PoseLandmark
LM = {
    'L_SH': int(PL.LEFT_SHOULDER), 'R_SH': int(PL.RIGHT_SHOULDER),
    'L_HP': int(PL.LEFT_HIP), 'R_HP': int(PL.RIGHT_HIP),
    'L_AN': int(PL.LEFT_ANKLE), 'R_AN': int(PL.RIGHT_ANKLE),
    'L_HEEL': int(PL.LEFT_HEEL), 'R_HEEL': int(PL.RIGHT_HEEL),
    'L_TOE': int(PL.LEFT_FOOT_INDEX), 'R_TOE': int(PL.RIGHT_FOOT_INDEX),
}

CONFIG = {
    'FRAME_STRIDE': 2,
    'MODEL_COMPLEXITY': 1,
    'VEL_THRESH_NORM': 0.002,
    'STABILITY_WINDOW': 5,
    'MIN_EVENT_GAP_FRAMES': 5,
    'EXPECTED_FOOT_LEN_CM': 18.0,
    'EXPECTED_HIP_WIDTH_CM': 18.0,
    'MAX_TANDEM_GAP_CM': 5.0,
}


def rolling_med(x, k=5):
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()


def _P2(df: pd.DataFrame, idx: int) -> np.ndarray:
    cx, cy = f'x{idx}', f'y{idx}'
    if cx not in df.columns or cy not in df.columns:
        return np.full((len(df), 2), np.nan, float)
    return np.column_stack([df[cx].to_numpy(float), df[cy].to_numpy(float)])


def _P2N(df: pd.DataFrame, idx: int) -> np.ndarray:
    cx, cy = f'xn{idx}', f'yn{idx}'
    if cx not in df.columns or cy not in df.columns:
        return np.full((len(df), 2), np.nan, float)
    return np.column_stack([df[cx].to_numpy(float), df[cy].to_numpy(float)])


def _mid(a, b):
    return (np.asarray(a, float) + np.asarray(b, float)) / 2.0


def _wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def angle_3pt(a, b, c, eps=1e-8):
    a = np.asarray(a, float); b = np.asarray(b, float); c = np.asarray(c, float)
    ba = a - b; bc = c - b
    nba, nbc = np.linalg.norm(ba), np.linalg.norm(bc)
    if nba < eps or nbc < eps:
        return float('nan')
    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = np.clip(cosang, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosang)))


def run_pose_fast(video_path: str, frame_stride: int = 2, model_complexity: int = 1) -> Tuple[pd.DataFrame, float]:
    if not isinstance(video_path, str) or not os.path.exists(video_path):
        return pd.DataFrame(), 30.0
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return pd.DataFrame(), 30.0
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = float(fps) if fps and fps > 1e-3 else 30.0
    rows = []
    with mp_pose.Pose(static_image_mode=False,
                      model_complexity=int(model_complexity),
                      enable_segmentation=False,
                      smooth_landmarks=True,
                      min_detection_confidence=0.5,
                      min_tracking_confidence=0.5) as pose:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % max(1, int(frame_stride)) != 0:
                frame_idx += 1
                continue
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)
            row = {'i': int(frame_idx), 't': float(frame_idx) / fps, 'w': int(w), 'h': int(h)}
            if res.pose_landmarks:
                lms = res.pose_landmarks.landmark
                for idx in LM.values():
                    lm = lms[idx]
                    row[f'xn{idx}'] = float(lm.x)
                    row[f'yn{idx}'] = float(lm.y)
                    row[f'x{idx}'] = float(lm.x * w)
                    row[f'y{idx}'] = float(lm.y * h)
                    row[f'vis{idx}'] = float(lm.visibility)
            else:
                for idx in LM.values():
                    row[f'xn{idx}'] = np.nan; row[f'yn{idx}'] = np.nan
                    row[f'x{idx}'] = np.nan; row[f'y{idx}'] = np.nan; row[f'vis{idx}'] = np.nan
            rows.append(row)
            frame_idx += 1
    cap.release()
    return pd.DataFrame(rows), fps

def trunk_sway_from_baseline(df: pd.DataFrame) -> np.ndarray:
    """Angle of trunk vector (mid-hip->mid-shoulder) across frames, baseline-subtracted (degrees)."""
    SHO = _mid(_P2(df, LM['L_SH']), _P2(df, LM['R_SH']))
    HIP = _mid(_P2(df, LM['L_HP']), _P2(df, LM['R_HP']))
    v = SHO - HIP
    theta = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    if not np.any(np.isfinite(theta)):
        return np.full_like(theta, np.nan, dtype=float)
    base = float(np.nanmedian(theta))
    dev = _wrap_deg(theta - base)
    return dev


def infer_walk_axis_from_midhip(df: pd.DataFrame):
    hip = _mid(_P2(df, LM['L_HP']), _P2(df, LM['R_HP']))
    ok = np.isfinite(hip).all(axis=1)
    H = hip[ok]
    if H.shape[0] < 5:
        return np.nanmedian(hip, axis=0), np.array([0.0, 1.0], float)
    Hc = H - np.mean(H, axis=0, keepdims=True)
    cov = np.cov(Hc.T)
    w, V = np.linalg.eig(cov)
    axis = V[:, int(np.argmax(w))].astype(float)
    axis = axis / (np.linalg.norm(axis) + 1e-9)
    origin = np.nanmedian(H, axis=0).astype(float)
    proj = (hip - origin) @ axis
    proj_ok = proj[np.isfinite(proj)]
    if proj_ok.size >= 2 and proj_ok[-1] < proj_ok[0]:
        axis = -axis
    return origin, axis


@dataclass
class ContactEvent:
    frame_idx: int
    foot: str


def detect_contacts_velocity_stability(df: pd.DataFrame, fps: float, window: int = 5,
                                       vel_thresh_norm: float = 0.002, min_gap_frames: int = 5,
                                       vis_thresh: float = 0.3):
    L_toe = _P2N(df, LM['L_TOE'])
    R_toe = _P2N(df, LM['R_TOE'])
    L_vis = df.get(f"vis{LM['L_TOE']}", pd.Series([np.nan] * len(df))).to_numpy(float)
    R_vis = df.get(f"vis{LM['R_TOE']}", pd.Series([np.nan] * len(df))).to_numpy(float)

    def vel(p, pprev):
        if not (np.isfinite(p).all() and np.isfinite(pprev).all()):
            return np.nan
        return float(np.hypot(p[0] - pprev[0], p[1] - pprev[1]))

    Lbuf, Rbuf = deque(maxlen=window), deque(maxlen=window)
    prev_L_stable = prev_R_stable = False
    last_contact = None
    last_event_frame = -10**9
    events = []
    nL = nR = 0

    for k in range(1, len(df)):
        lv = vel(L_toe[k], L_toe[k-1])
        rv = vel(R_toe[k], R_toe[k-1])
        if not np.isfinite(lv) or not np.isfinite(L_toe[k]).all() or L_vis[k] < vis_thresh:
            Lbuf.clear(); L_stable = False
        else:
            Lbuf.append(lv); L_stable = (len(Lbuf) == window and all(x < vel_thresh_norm for x in Lbuf))
        if not np.isfinite(rv) or not np.isfinite(R_toe[k]).all() or R_vis[k] < vis_thresh:
            Rbuf.clear(); R_stable = False
        else:
            Rbuf.append(rv); R_stable = (len(Rbuf) == window and all(x < vel_thresh_norm for x in Rbuf))
        L_edge = L_stable and not prev_L_stable
        R_edge = R_stable and not prev_R_stable
        if (k - last_event_frame) < int(min_gap_frames):
            L_edge = R_edge = False
        if last_contact is None:
            if L_edge and not R_edge:
                events.append(ContactEvent(k, 'L')); last_contact = 'L'; last_event_frame = k; nL += 1
            elif R_edge and not L_edge:
                events.append(ContactEvent(k, 'R')); last_contact = 'R'; last_event_frame = k; nR += 1
            elif L_edge and R_edge:
                if lv <= rv:
                    events.append(ContactEvent(k, 'L')); last_contact = 'L'; nL += 1
                else:
                    events.append(ContactEvent(k, 'R')); last_contact = 'R'; nR += 1
                last_event_frame = k
        else:
            if L_edge and last_contact == 'R':
                events.append(ContactEvent(k, 'L')); last_contact = 'L'; last_event_frame = k; nL += 1
            elif R_edge and last_contact == 'L':
                events.append(ContactEvent(k, 'R')); last_contact = 'R'; last_event_frame = k; nR += 1
        prev_L_stable = L_stable
        prev_R_stable = R_stable
    return events, nL, nR


def compute_step_metrics(df, placements, origin, axis, ppc_unused=None):
    steps = []
    if placements is None or len(placements) < 2:
        return steps
    axis = np.asarray(axis, float)
    axis = axis / (np.linalg.norm(axis) + 1e-9)

    def _get_frame_foot(ev):
        return int(ev.frame_idx), ev.foot

    def _isfinite2(p):
        return p is not None and np.isfinite(p).all()

    ppc_used = float('nan')
    if ppc_unused is not None:
        try:
            ppc_tmp = float(ppc_unused)
            if np.isfinite(ppc_tmp) and ppc_tmp > 1e-6:
                ppc_used = ppc_tmp
        except Exception:
            pass

    if not (np.isfinite(ppc_used) and ppc_used > 1e-6):
        foot_px, hip_px = [], []
        for ev in placements:
            f, foot = _get_frame_foot(ev)
            heel = _P2(df, LM['L_HEEL'] if foot == 'L' else LM['R_HEEL'])[f]
            toe = _P2(df, LM['L_TOE'] if foot == 'L' else LM['R_TOE'])[f]
            if _isfinite2(heel) and _isfinite2(toe):
                d = float(np.linalg.norm(heel - toe))
                if 10.0 < d < 250.0:
                    foot_px.append(d)
            LHP = _P2(df, LM['L_HP'])[f]
            RHP = _P2(df, LM['R_HP'])[f]
            if _isfinite2(LHP) and _isfinite2(RHP):
                d = float(np.linalg.norm(LHP - RHP))
                if 10.0 < d < 400.0:
                    hip_px.append(d)
        if len(foot_px) >= 3:
            ppc_used = float(np.nanmedian(foot_px) / CONFIG['EXPECTED_FOOT_LEN_CM'])
        elif len(hip_px) >= 3:
            ppc_used = float(np.nanmedian(hip_px) / CONFIG['EXPECTED_HIP_WIDTH_CM'])

    max_gap_cm = float(CONFIG['MAX_TANDEM_GAP_CM'])

    for i in range(1, len(placements)):
        f0, prev_foot = _get_frame_foot(placements[i-1])
        f1, foot = _get_frame_foot(placements[i])
        lead_heel = _P2(df, LM['L_HEEL'] if foot == 'L' else LM['R_HEEL'])[f1]
        lead_toe = _P2(df, LM['L_TOE'] if foot == 'L' else LM['R_TOE'])[f1]
        prev_toe = _P2(df, LM['L_TOE'] if prev_foot == 'L' else LM['R_TOE'])[f0]
        prev_heel = _P2(df, LM['L_HEEL'] if prev_foot == 'L' else LM['R_HEEL'])[f0]
        if not (_isfinite2(lead_heel) and _isfinite2(lead_toe) and _isfinite2(prev_toe) and _isfinite2(prev_heel)):
            continue
        hgtd_px = float(np.dot((lead_heel - prev_toe), axis))
        raw_step_px = float(np.dot((lead_heel - prev_heel), axis))
        foot_len_px = float(np.linalg.norm(lead_toe - lead_heel))
        step_gap_cm = max(0.0, hgtd_px / ppc_used) if np.isfinite(ppc_used) and ppc_used > 0 else np.nan
        outlier = bool(np.isfinite(step_gap_cm) and step_gap_cm > max_gap_cm)
        if outlier:
            step_gap_cm = np.nan
        nsd = raw_step_px / foot_len_px if np.isfinite(foot_len_px) and foot_len_px > 1e-6 else np.nan
        steps.append({
            'i': i,
            'frame_idx': int(f1),
            'foot': foot,
            'step_gap_cm': step_gap_cm,
            'nsd': nsd,
            'understep': bool(np.isfinite(hgtd_px) and hgtd_px < 0),
            'hgtd_cm': (hgtd_px / ppc_used) if np.isfinite(ppc_used) and ppc_used > 0 else np.nan,
            'raw_step_px': raw_step_px,
            'foot_len_px': foot_len_px,
            'ppc_used': ppc_used,
            'outlier': outlier,
        })
    return steps


def extract_tandem_walking_metrics(front_video_path: Optional[str] = None, side_video_path: Optional[str] = None, eyes_open: bool = True) -> Dict[str, Any]:
    
    # Process side video for stepping metrics and AP sway
    if side_video_path and os.path.exists(side_video_path):
        df_side, fps_side = run_pose_fast(side_video_path, frame_stride=CONFIG['FRAME_STRIDE'], model_complexity=CONFIG['MODEL_COMPLEXITY'])
    else:
        df_side, fps_side = pd.DataFrame(), 30.0

    if len(df_side) < 20:
        return {'error': 'Insufficient pose data in side video', 'fps': fps_side}

    origin, axis = infer_walk_axis_from_midhip(df_side)
    events, nL, nR = detect_contacts_velocity_stability(df_side, fps_side,
                                                        window=CONFIG['STABILITY_WINDOW'],
                                                        vel_thresh_norm=CONFIG['VEL_THRESH_NORM'],
                                                        min_gap_frames=CONFIG['MIN_EVENT_GAP_FRAMES'])
    steps = compute_step_metrics(df_side, events, origin, axis, None)
    df_steps = pd.DataFrame(steps) if steps else pd.DataFrame(columns=['step_gap_cm', 'understep'])

    ap_dev = trunk_sway_from_baseline(df_side)
    ap_abs = np.abs(ap_dev)
    ap_sway_mean = float(np.nanmedian(ap_abs)) if np.any(np.isfinite(ap_abs)) else None
    ap_sway_sd = float(np.nanstd(ap_abs, ddof=0)) if np.any(np.isfinite(ap_abs)) else None

    # Process front video for ML sway
    ml_sway_mean = ml_sway_sd = None
    if front_video_path and os.path.exists(front_video_path):
        df_front, fps_front = run_pose_fast(front_video_path, frame_stride=CONFIG['FRAME_STRIDE'], model_complexity=CONFIG['MODEL_COMPLEXITY'])
        if len(df_front) >= 10:
            ml_dev = trunk_sway_from_baseline(df_front)
            ml_abs = np.abs(ml_dev)
            ml_sway_mean = float(np.nanmedian(ml_abs)) if np.any(np.isfinite(ml_abs)) else None
            ml_sway_sd = float(np.nanstd(ml_abs, ddof=0)) if np.any(np.isfinite(ml_abs)) else None
    
    gaps = df_steps['step_gap_cm'].to_numpy(float) if 'step_gap_cm' in df_steps.columns else np.array([])
    valid_gaps = gaps[np.isfinite(gaps)]
    return {
        'ml_sway_mean_deg': ml_sway_mean,
        'ml_sway_sd_deg': ml_sway_sd,
        'ap_sway_mean_deg': ap_sway_mean,
        'ap_sway_sd_deg': ap_sway_sd,
        'step_count': int(len(events)),
        'left_contacts': int(nL),
        'right_contacts': int(nR),
        'mean_step_gap_cm': float(np.nanmean(valid_gaps)) if len(valid_gaps) else None,
        'median_step_gap_cm': float(np.nanmedian(valid_gaps)) if len(valid_gaps) else None,
        'understep_count': int(df_steps['understep'].fillna(False).astype(bool).sum()) if 'understep' in df_steps.columns else 0,
        'walk_duration_s': len(df_side) / fps_side if fps_side > 0 else None,
        'cadence_steps_per_min': (len(events) / (len(df_side) / fps_side) * 60.0) if fps_side > 0 and len(df_side) else None,
        'fps': fps_side,
        'eyes_open': eyes_open,
    }

def process_tandem_walking(
    front_video_path: Optional[str],
    side_video_path: Optional[str],
    age_years: int,
    eyes_open: bool = True
) -> Dict[str, Any]:
    """Process tandem walking video and return scores - API wrapper."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scoring import score_tandem_walking
    
    if not side_video_path or not os.path.exists(side_video_path):
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": "Error: Side video is required for Tandem Walking"
        }
    if not front_video_path or not os.path.exists(front_video_path):
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": "Error: Front video is required for Tandem Walking"
        }
    
    # Handle MOV files - try to convert if needed
    front_video_path, front_err = ensure_video_readable(front_video_path)
    side_video_path, side_err = ensure_video_readable(side_video_path)
    
    if front_err:
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": f"Error (front video): {front_err}"
        }
    if side_err:
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": f"Error (side video): {side_err}"
        }
    
    raw_metrics = extract_tandem_walking_metrics(front_video_path, side_video_path, eyes_open=eyes_open)
    
    if "error" in raw_metrics:
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": f"Error: {raw_metrics['error']}"
        }
    
    score_result = score_tandem_walking(raw_metrics, age_years=age_years, eyes_open=eyes_open)
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k or k == "total_score"},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": 34,
        "interpretation": score_result.get("interpretation", "N/A"),
        "eyesOpen": eyes_open,
    }
