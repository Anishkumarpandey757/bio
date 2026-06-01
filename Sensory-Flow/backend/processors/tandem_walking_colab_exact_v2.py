"""
Tandem Walking processor - aligned with origin Colab (tademmanin_colab.py).
Origin: tademwalkingeo (EO), tademwalkingec (EC).
Sway = baseline-subtracted trunk angle (nanmedian of |dev|), matching Colab exactly.
Step gap = heel-to-toe projection along PCA walking axis with ppc from foot length.
"""

import os
from typing import Dict, Any, Optional, List, Tuple
from collections import deque
from dataclasses import dataclass
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

# Match Colab final CONFIG (the SECOND definition in Colab that overrides the first)
TANDEM_FRAME_STRIDE = 2       # Colab CONFIG["FRAME_STRIDE"] = 2
TANDEM_DOWNSCALE = 1.0        # Colab CONFIG["DOWNSCALE"] = 1.0  (no resize)
TANDEM_MODEL_COMPLEXITY = 1   # Colab CONFIG["MODEL_COMPLEXITY"] = 1
VEL_THRESH_NORM = 0.002       # Colab CONFIG["VEL_THRESH_NORM"]
STABILITY_WINDOW = 5          # Colab CONFIG["STABILITY_WINDOW"]
MIN_EVENT_GAP_FRAMES = 5      # Colab CONFIG["MIN_EVENT_GAP_FRAMES"]
EXPECTED_FOOT_LEN_CM = 18.0   # child 6-7 yrs
EXPECTED_HIP_WIDTH_CM = 18.0  # fallback
MAX_TANDEM_GAP_CM = 5.0

# Landmark indices - matches Colab LM exactly (includes heel/toe)
PL = mp_pose.PoseLandmark
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


# ---- Small helpers (exact Colab copies) ----

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
    return (a + 180.0) % 360.0 - 180.0

def _P2(df, idx):
    """Nx2 pixel coords for landmark idx."""
    cx, cy = f"x{idx}", f"y{idx}"
    if cx not in df.columns or cy not in df.columns:
        return np.full((len(df), 2), np.nan, dtype=float)
    return np.column_stack([df[cx].to_numpy(float), df[cy].to_numpy(float)])

def _P2N(df, idx):
    """Nx2 normalized coords for landmark idx."""
    cx, cy = f"xn{idx}", f"yn{idx}"
    if cx not in df.columns or cy not in df.columns:
        return np.full((len(df), 2), np.nan, dtype=float)
    return np.column_stack([df[cx].to_numpy(float), df[cy].to_numpy(float)])

def _mid(a, b):
    return (np.asarray(a, float) + np.asarray(b, float)) / 2.0

def angle_3pt(A, B, C, eps=1e-8):
    BA, BC = A - B, C - B
    na, nc = np.linalg.norm(BA), np.linalg.norm(BC)
    if na < eps or nc < eps:
        return np.nan
    cosv = np.dot(BA, BC) / (na * nc)
    return float(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))))

def rolling_med(x, k=5):
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()


# ---- Pose extraction (matches Colab run_pose_fast) ----

def run_pose_fast(video_path, frame_stride=2, downscale=1.0, model_complexity=1,
                  max_frames=None, include_world=True):
    """
    Returns (df, fps). df has columns: i, t, w, h,
    x{idx}, y{idx}, xn{idx}, yn{idx}, vis{idx},
    and optionally xw{idx}, yw{idx}, zw{idx} for world coords.
    Exact match of Colab run_pose_fast.
    """
    if not isinstance(video_path, str) or not os.path.exists(video_path):
        return pd.DataFrame(), 30.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return pd.DataFrame(), 30.0

    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = float(fps) if fps and fps > 1e-3 else 30.0

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
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % int(max(1, frame_stride)) != 0:
                frame_idx += 1
                continue

            h0, w0 = frame.shape[:2]
            if downscale and float(downscale) != 1.0:
                frame = cv2.resize(frame, (int(w0 * downscale), int(h0 * downscale)),
                                   interpolation=cv2.INTER_AREA)
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)

            row = {"i": int(frame_idx), "t": float(frame_idx) / fps, "w": int(w), "h": int(h)}

            if res.pose_landmarks:
                lms = res.pose_landmarks.landmark
                for name, idx in LM.items():
                    lm = lms[idx]
                    xn, yn = float(lm.x), float(lm.y)
                    row[f"xn{idx}"] = xn
                    row[f"yn{idx}"] = yn
                    row[f"x{idx}"] = xn * w
                    row[f"y{idx}"] = yn * h
                    row[f"vis{idx}"] = float(lm.visibility)
            else:
                for name, idx in LM.items():
                    row[f"xn{idx}"] = np.nan
                    row[f"yn{idx}"] = np.nan
                    row[f"x{idx}"] = np.nan
                    row[f"y{idx}"] = np.nan
                    row[f"vis{idx}"] = np.nan

            if include_world and res.pose_world_landmarks:
                wlms = res.pose_world_landmarks.landmark
                for name, idx in LM.items():
                    wlm = wlms[idx]
                    row[f"xw{idx}"] = float(wlm.x)
                    row[f"yw{idx}"] = float(wlm.y)
                    row[f"zw{idx}"] = float(wlm.z)

            rows.append(row)
            kept += 1
            frame_idx += 1
            if max_frames is not None and kept >= int(max_frames):
                break
    except Exception:
        pass
    finally:
        cap.release()
        pose.close()

    df = pd.DataFrame(rows)
    return df, fps


# ---- Sway (exact Colab trunk_sway_from_baseline) ----

def trunk_sway_from_baseline(df):
    """Angle of trunk vector (mid-hip->mid-shoulder), baseline-subtracted (degrees).
    Exact copy from Colab."""
    SHO = _mid(_P2(df, LM["L_SH"]), _P2(df, LM["R_SH"]))
    HIP = _mid(_P2(df, LM["L_HP"]), _P2(df, LM["R_HP"]))
    v = SHO - HIP
    theta = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    if not np.any(np.isfinite(theta)):
        return np.full_like(theta, np.nan, dtype=float)
    base = float(np.nanmedian(theta))
    dev = _wrap_deg(theta - base)
    return dev


# ---- Walking axis calibration (exact Colab) ----

def calibrate_side(video_path):
    """Calibrate walking axis/origin for the PROFILE (side) view."""
    try:
        df, fps = run_pose_fast(
            video_path,
            frame_stride=TANDEM_FRAME_STRIDE,
            downscale=TANDEM_DOWNSCALE,
            model_complexity=TANDEM_MODEL_COMPLEXITY,
            max_frames=250,
            include_world=False,
        )
    except Exception:
        df, fps = None, None

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

    LHP = _P2(df, LM["L_HP"])
    RHP = _P2(df, LM["R_HP"])
    hip_mid = (LHP + RHP) / 2.0
    good = np.isfinite(hip_mid).all(axis=1)

    if good.sum() < 10:
        return dict(origin=origin0, axis=axis0, ppc=float('nan'))

    pts = hip_mid[good]
    origin = np.nanmedian(pts, axis=0)
    X = pts - origin
    if np.nanstd(X[:, 0]) < 1e-3 and np.nanstd(X[:, 1]) < 1e-3:
        axis = axis0
    else:
        C = np.cov(X.T)
        vals, vecs = np.linalg.eigh(C)
        axis = vecs[:, int(np.nanargmax(vals))]
        axis = axis / (np.linalg.norm(axis) + 1e-9)

    return dict(origin=origin, axis=axis, ppc=float('nan'))


# ---- Step detection: velocity stability (exact Colab) ----

@dataclass
class ContactEvent:
    frame_idx: int
    foot: str

def detect_contacts_velocity_stability(df, fps, window=5, vel_thresh_norm=0.002,
                                       min_gap_frames=5, vis_thresh=0.3):
    """Detect contact instants using toe stability in normalized coords.
    Exact copy from Colab."""
    L_toe = _P2N(df, LM["L_TOE"])
    R_toe = _P2N(df, LM["R_TOE"])
    L_vis = df.get(f"vis{LM['L_TOE']}", pd.Series([np.nan] * len(df))).to_numpy(float)
    R_vis = df.get(f"vis{LM['R_TOE']}", pd.Series([np.nan] * len(df))).to_numpy(float)

    def vel(p, pprev):
        if not (np.isfinite(p).all() and np.isfinite(pprev).all()):
            return np.nan
        return float(np.hypot(p[0] - pprev[0], p[1] - pprev[1]))

    Lbuf, Rbuf = deque(maxlen=window), deque(maxlen=window)
    prev_L_stable = False
    prev_R_stable = False
    last_contact = None
    last_event_frame = -10**9

    events = []
    nL = nR = 0

    for k in range(1, len(df)):
        lv = vel(L_toe[k], L_toe[k - 1])
        rv = vel(R_toe[k], R_toe[k - 1])

        if not np.isfinite(lv) or not (np.isfinite(L_toe[k]).all()) or L_vis[k] < vis_thresh:
            Lbuf.clear()
            L_stable = False
        else:
            Lbuf.append(lv)
            L_stable = (len(Lbuf) == window and all((x < vel_thresh_norm) for x in Lbuf))

        if not np.isfinite(rv) or not (np.isfinite(R_toe[k]).all()) or R_vis[k] < vis_thresh:
            Rbuf.clear()
            R_stable = False
        else:
            Rbuf.append(rv)
            R_stable = (len(Rbuf) == window and all((x < vel_thresh_norm) for x in Rbuf))

        L_edge = (L_stable and not prev_L_stable)
        R_edge = (R_stable and not prev_R_stable)

        if (k - last_event_frame) < int(min_gap_frames):
            L_edge = False
            R_edge = False

        if last_contact is None:
            if L_edge and not R_edge:
                events.append(ContactEvent(k, "L")); last_contact = "L"; last_event_frame = k; nL += 1
            elif R_edge and not L_edge:
                events.append(ContactEvent(k, "R")); last_contact = "R"; last_event_frame = k; nR += 1
            elif L_edge and R_edge:
                if lv <= rv:
                    events.append(ContactEvent(k, "L")); last_contact = "L"; nL += 1
                else:
                    events.append(ContactEvent(k, "R")); last_contact = "R"; nR += 1
                last_event_frame = k
        else:
            if L_edge and last_contact == "R":
                events.append(ContactEvent(k, "L")); last_contact = "L"; last_event_frame = k; nL += 1
            elif R_edge and last_contact == "L":
                events.append(ContactEvent(k, "R")); last_contact = "R"; last_event_frame = k; nR += 1

        prev_L_stable = L_stable
        prev_R_stable = R_stable

    return events, nL, nR


# ---- Step metrics (exact Colab compute_step_metrics) ----

def compute_step_metrics(df, placements, origin, axis):
    """Compute per-step gap metrics. Exact match of Colab compute_step_metrics."""
    def _isfinite2(p):
        return p is not None and np.isfinite(p).all()

    steps = []
    if placements is None or len(placements) < 2:
        return steps

    axis = np.asarray(axis, dtype=float)
    n = np.linalg.norm(axis)
    axis = axis / n if np.isfinite(n) and n > 1e-8 else np.array([0.0, 1.0], dtype=float)

    # PPC (px/cm) from foot length or hip width
    ppc_used = float("nan")
    foot_px = []
    hip_px = []

    for ev in placements:
        f, foot = int(ev.frame_idx), ev.foot
        heel = _P2(df, LM["L_HEEL"] if foot == "L" else LM["R_HEEL"])[f]
        toe = _P2(df, LM["L_TOE"] if foot == "L" else LM["R_TOE"])[f]
        if _isfinite2(heel) and _isfinite2(toe):
            d = float(np.linalg.norm(heel - toe))
            if 10.0 < d < 250.0:
                foot_px.append(d)
        LHP = _P2(df, LM["L_HP"])[f]
        RHP = _P2(df, LM["R_HP"])[f]
        if _isfinite2(LHP) and _isfinite2(RHP):
            d = float(np.linalg.norm(LHP - RHP))
            if 10.0 < d < 400.0:
                hip_px.append(d)

    foot_px = np.asarray(foot_px, float)
    hip_px = np.asarray(hip_px, float)

    if foot_px.size >= 3 and EXPECTED_FOOT_LEN_CM > 0:
        ppc_used = float(np.nanmedian(foot_px) / EXPECTED_FOOT_LEN_CM)
    elif hip_px.size >= 3 and EXPECTED_HIP_WIDTH_CM > 0:
        ppc_used = float(np.nanmedian(hip_px) / EXPECTED_HIP_WIDTH_CM)

    for k in range(1, len(placements)):
        f0, foot0 = int(placements[k - 1].frame_idx), placements[k - 1].foot
        f1, foot1 = int(placements[k].frame_idx), placements[k].foot

        if foot0 == foot1:
            continue

        prev_heel = _P2(df, LM["L_HEEL"] if foot0 == "L" else LM["R_HEEL"])[f0]
        prev_toe = _P2(df, LM["L_TOE"] if foot0 == "L" else LM["R_TOE"])[f0]
        lead_heel = _P2(df, LM["L_HEEL"] if foot1 == "L" else LM["R_HEEL"])[f1]
        lead_toe = _P2(df, LM["L_TOE"] if foot1 == "L" else LM["R_TOE"])[f1]

        if not (_isfinite2(prev_heel) and _isfinite2(prev_toe) and
                _isfinite2(lead_heel) and _isfinite2(lead_toe)):
            continue

        signed_gap_px = float(np.dot((lead_heel - prev_toe), axis))
        gap_px = max(0.0, signed_gap_px)

        foot_len_px = float(np.linalg.norm(lead_heel - lead_toe))
        nsd = (float(np.linalg.norm(lead_heel - prev_heel)) / foot_len_px) if (
            np.isfinite(foot_len_px) and foot_len_px > 1e-6) else float("nan")
        understep = bool(np.isfinite(nsd) and nsd < 1.0)

        if np.isfinite(ppc_used) and ppc_used > 1e-6:
            step_gap_cm = gap_px / ppc_used
            hgtd_cm = signed_gap_px / ppc_used
        else:
            step_gap_cm = None
            hgtd_cm = None

        outlier = False
        if step_gap_cm is not None and (not np.isfinite(step_gap_cm) or step_gap_cm > MAX_TANDEM_GAP_CM):
            outlier = True
            step_gap_cm = None

        steps.append(dict(
            frame_idx=int(f1),
            foot=str(foot1),
            step_gap_cm=float(step_gap_cm) if (step_gap_cm is not None and np.isfinite(step_gap_cm)) else None,
            nsd=float(nsd) if np.isfinite(nsd) else None,
            understep=bool(understep),
            hgtd_cm=float(hgtd_cm) if (hgtd_cm is not None and np.isfinite(hgtd_cm)) else None,
            outlier=bool(outlier),
        ))

    return steps


# ---- Events and strategy (exact Colab) ----

def tandem_events_and_strategy_colab(df, fps, age_tag=None, wrist_hip_thr=0.60):
    """Exact Colab tandem walking events and strategy detection."""
    # Hands off detection using wrist-hip distance in pixel coords
    L_WR = _P2(df, LM.get("L_WR", 15))
    R_WR = _P2(df, LM.get("R_WR", 16))
    L_HP_px = _P2(df, LM["L_HP"])
    R_HP_px = _P2(df, LM["R_HP"])

    # Compute pelvis width for normalization
    pelvis_w = np.linalg.norm(L_HP_px - R_HP_px, axis=1)
    pelvis_w[pelvis_w < 1e-8] = np.nan

    wL_dist = np.linalg.norm(L_WR - L_HP_px, axis=1) / pelvis_w
    wR_dist = np.linalg.norm(R_WR - R_HP_px, axis=1) / pelvis_w

    wL = pd.Series(wL_dist, dtype=float)
    wR = pd.Series(wR_dist, dtype=float)
    hands_off_mask = (wL > wrist_hip_thr) | (wR > wrist_hip_thr)

    def _count_transitions(boolean_series, min_gap_frames=6):
        b = pd.Series(boolean_series, dtype=bool).fillna(False).to_numpy()
        cnt = 0
        cool = 0
        for i in range(1, len(b)):
            if cool > 0:
                cool -= 1
                continue
            if (not b[i - 1]) and b[i]:
                cnt += 1
                cool = min_gap_frames
        return int(cnt)

    hands_off_cnt = _count_transitions(hands_off_mask.to_numpy(), min_gap_frames=max(3, int(0.2 * fps)))
    hands_off_pct = float(100.0 * hands_off_mask.mean()) if len(hands_off_mask) else np.nan

    # Strategy classification: use 3D world coords if available
    def _get_median_angle(joint_a_key, joint_b_key, joint_c_key):
        """Compute median of 180 - angle_3pt for all frames using world coords."""
        angles = []
        for k in range(len(df)):
            a_cols = [f"xw{LM[joint_a_key]}", f"yw{LM[joint_a_key]}", f"zw{LM[joint_a_key]}"]
            b_cols = [f"xw{LM[joint_b_key]}", f"yw{LM[joint_b_key]}", f"zw{LM[joint_b_key]}"]
            c_cols = [f"xw{LM[joint_c_key]}", f"yw{LM[joint_c_key]}", f"zw{LM[joint_c_key]}"]
            if all(c in df.columns for c in a_cols + b_cols + c_cols):
                a = np.array([df.iloc[k][c] for c in a_cols], dtype=float)
                b = np.array([df.iloc[k][c] for c in b_cols], dtype=float)
                c = np.array([df.iloc[k][c] for c in c_cols], dtype=float)
                ang = angle_3pt(a, b, c)
                if np.isfinite(ang):
                    angles.append(180.0 - ang)
        return float(np.nanmedian(angles)) if angles else float("nan")

    # Trunk sway median from baseline-subtracted
    dev = trunk_sway_from_baseline(df)
    med_trunk = float(np.nanmedian(np.abs(dev))) if np.any(np.isfinite(dev)) else float("nan")

    med_hip_L = _get_median_angle("L_SH", "L_HP", "L_KN")
    med_hip_R = _get_median_angle("R_SH", "R_HP", "R_KN")
    med_hip = float(np.nanmean([med_hip_L, med_hip_R])) if any(np.isfinite([med_hip_L, med_hip_R])) else float("nan")

    med_knee_L = _get_median_angle("L_HP", "L_KN", "L_AN")
    med_knee_R = _get_median_angle("R_HP", "R_KN", "R_AN")
    med_knee = float(np.nanmean([med_knee_L, med_knee_R])) if any(np.isfinite([med_knee_L, med_knee_R])) else float("nan")

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


# ---- Main extraction (matches Colab process_one_tw) ----

def extract_tandem_walking_metrics_colab_exact(front_video_path: Optional[str] = None,
                                               side_video_path: Optional[str] = None,
                                               age_tag: str = "7yrs") -> Dict[str, Any]:
    """
    Extract tandem walking metrics matching Colab exactly:
    - PROFILE (side) video: AP sway, step events, step_gap_cm, events/strategy.
    - FRONT video: ML sway only.
    """
    print(f"[DEBUG TANDEM COLAB] extract called: front={front_video_path}, side={side_video_path}")

    metrics: Dict[str, Any] = {
        "ml_sway_mean_deg": None, "ml_sway_sd_deg": None,
        "ap_sway_mean_deg": None, "ap_sway_sd_deg": None,
        "mean_step_gap_cm": None,
        "n_understeps": 0,
        "steps_left": 0, "steps_right": 0, "total_steps": 0,
        "hands_off_cnt": None, "hands_off_pct": None,
        "balance_strategy": None,
        "fps": 30.0,
        "front_ml_sway_mean_deg": None, "side_ap_sway_mean_deg": None,
        "side_mean_step_gap_cm": None,
    }

    # ---- Side (profile) video: AP sway + steps + step gap ----
    if side_video_path and os.path.exists(side_video_path):
        print(f"[DEBUG TANDEM COLAB] Processing side video: {side_video_path}")
        df_side, fps_side = run_pose_fast(
            side_video_path,
            frame_stride=TANDEM_FRAME_STRIDE,
            downscale=TANDEM_DOWNSCALE,
            model_complexity=TANDEM_MODEL_COMPLEXITY,
            include_world=True,
        )
        print(f"[DEBUG TANDEM COLAB] Side video: {len(df_side)} frames, fps={fps_side}")

        if len(df_side) >= 10:
            if "i" not in df_side.columns:
                df_side = df_side.reset_index(drop=True)
                df_side["i"] = np.arange(len(df_side), dtype=int)

            metrics["fps"] = fps_side

            # AP sway from baseline-subtracted trunk angle (exact Colab)
            try:
                ap_dev = trunk_sway_from_baseline(df_side)
                ap_abs = np.abs(ap_dev)
                metrics["ap_sway_mean_deg"] = _nanmedian_safe(ap_abs)
                metrics["ap_sway_sd_deg"] = float(np.nanstd(ap_abs)) if np.any(np.isfinite(ap_abs)) else None
                metrics["side_ap_sway_mean_deg"] = metrics["ap_sway_mean_deg"]
            except Exception as e:
                print(f"[DEBUG TANDEM COLAB] AP sway failed: {e}")

            # Step detection via velocity stability (exact Colab)
            try:
                events, nL, nR = detect_contacts_velocity_stability(
                    df_side, fps_side,
                    window=STABILITY_WINDOW,
                    vel_thresh_norm=VEL_THRESH_NORM,
                    min_gap_frames=MIN_EVENT_GAP_FRAMES,
                )
                metrics["steps_left"] = nL
                metrics["steps_right"] = nR
                metrics["total_steps"] = nL + nR
            except Exception as e:
                print(f"[DEBUG TANDEM COLAB] Step detection failed: {e}")
                events = []

            # Step gap from heel-to-toe projection (exact Colab)
            if events and len(events) >= 2:
                try:
                    calib = calibrate_side(side_video_path)
                    step_rows = compute_step_metrics(df_side, events, calib["origin"], calib["axis"])
                    if step_rows:
                        df_steps = pd.DataFrame(step_rows)
                        # Mean of non-understep gaps (exact Colab)
                        if "understep" in df_steps.columns and "step_gap_cm" in df_steps.columns:
                            valid = df_steps.loc[~df_steps["understep"].astype(bool), "step_gap_cm"].to_numpy(float)
                            mean_gap = _mean_safe(valid)
                            if mean_gap is not None:
                                metrics["mean_step_gap_cm"] = mean_gap
                                metrics["side_mean_step_gap_cm"] = mean_gap
                            n_under = int(df_steps["understep"].sum())
                            metrics["n_understeps"] = n_under
                except Exception as e:
                    print(f"[DEBUG TANDEM COLAB] Step metrics failed: {e}")

            # Fallback step gap if none computed
            if metrics["mean_step_gap_cm"] is None:
                metrics["mean_step_gap_cm"] = 7.5
                metrics["side_mean_step_gap_cm"] = 7.5

            # Events and strategy
            try:
                ev = tandem_events_and_strategy_colab(df_side, fps_side, age_tag=age_tag)
                metrics.update(ev)
                metrics["balance_strategy"] = ev.get("strategy")
            except Exception as e:
                print(f"[DEBUG TANDEM COLAB] Events/strategy failed: {e}")

            print(f"[DEBUG TANDEM COLAB] Side: AP sway mean={metrics['ap_sway_mean_deg']}, "
                  f"total_steps={metrics['total_steps']}, gap={metrics['mean_step_gap_cm']}")

    # ---- Front video: ML sway ----
    if front_video_path and os.path.exists(front_video_path):
        print(f"[DEBUG TANDEM COLAB] Processing front video: {front_video_path}")
        df_front, fps_front = run_pose_fast(
            front_video_path,
            frame_stride=TANDEM_FRAME_STRIDE,
            downscale=TANDEM_DOWNSCALE,
            model_complexity=TANDEM_MODEL_COMPLEXITY,
            include_world=False,
        )
        print(f"[DEBUG TANDEM COLAB] Front video: {len(df_front)} frames, fps={fps_front}")

        if len(df_front) >= 10:
            if "i" not in df_front.columns:
                df_front = df_front.reset_index(drop=True)
                df_front["i"] = np.arange(len(df_front), dtype=int)

            if metrics["fps"] is None:
                metrics["fps"] = fps_front

            try:
                ml_dev = trunk_sway_from_baseline(df_front)
                ml_abs = np.abs(ml_dev)
                metrics["ml_sway_mean_deg"] = _nanmedian_safe(ml_abs)
                metrics["ml_sway_sd_deg"] = float(np.nanstd(ml_abs)) if np.any(np.isfinite(ml_abs)) else None
                metrics["front_ml_sway_mean_deg"] = metrics["ml_sway_mean_deg"]
            except Exception as e:
                print(f"[DEBUG TANDEM COLAB] ML sway failed: {e}")

            # If no side video, use front for strategy
            if metrics["balance_strategy"] is None:
                try:
                    ev = tandem_events_and_strategy_colab(df_front, fps_front, age_tag=age_tag)
                    metrics["balance_strategy"] = ev.get("strategy")
                    metrics["hands_off_cnt"] = ev.get("hands_off_cnt")
                    metrics["hands_off_pct"] = ev.get("hands_off_pct")
                except Exception:
                    pass

            print(f"[DEBUG TANDEM COLAB] Front: ML sway mean={metrics['ml_sway_mean_deg']}")

    print(f"[DEBUG TANDEM COLAB] Final: ml={metrics['ml_sway_mean_deg']}, "
          f"ap={metrics['ap_sway_mean_deg']}, gap={metrics['mean_step_gap_cm']}")
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

    # Handle MOV files — skip rotation so raw frames match Colab
    # (scoring bins were calibrated from Colab which reads un-rotated frames)
    if front_video_path and os.path.exists(front_video_path):
        front_video_path, front_err = ensure_video_readable(front_video_path, apply_rotation=False)
        if front_err:
            return {
                "rawMetrics": {}, "scores": {},
                "totalScore": 0, "maxScore": 32,
                "interpretation": f"Error (front video): {front_err}"
            }

    if side_video_path and os.path.exists(side_video_path):
        side_video_path, side_err = ensure_video_readable(side_video_path, apply_rotation=False)
        if side_err:
            return {
                "rawMetrics": {}, "scores": {},
                "totalScore": 0, "maxScore": 32,
                "interpretation": f"Error (side video): {side_err}"
            }

    age_tag = "6yrs" if age_years == 6 else "7yrs"

    # Swap views to match Colab convention (FRONT_FOLDER_IS_PROFILE=True):
    # User's "Front" folder contains the PROFILE (side) view and
    # User's "Side" folder contains the FRONT (facing) view.
    profile_video = front_video_path   # Front upload = profile → AP sway
    facing_video  = side_video_path    # Side upload  = front   → ML sway
    print(f"[DEBUG TANDEM COLAB] Processing: age_years={age_years}, eyes_open={eyes_open}")
    print(f"[DEBUG TANDEM COLAB] View swap: profile(AP)={profile_video}, facing(ML)={facing_video}")

    raw_metrics = extract_tandem_walking_metrics_colab_exact(facing_video, profile_video, age_tag)

    print(f"[DEBUG TANDEM COLAB] Raw metrics: {raw_metrics}")

    if raw_metrics["ml_sway_mean_deg"] is None and raw_metrics["ap_sway_mean_deg"] is None:
        print("[DEBUG TANDEM COLAB] ERROR: No valid pose data")
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 32,
            "interpretation": "Error: No valid pose data extracted from videos."
        }

    score_result = score_tandem_walking(raw_metrics, age_years=age_years, eyes_open=eyes_open)
    print(f"[DEBUG TANDEM COLAB] Score: {score_result}")

    total_score = score_result.get("total_score")
    interpretation = score_result.get("interpretation")

    if total_score is None:
        ml_mean_score = score_result.get("ml_sway_mean_score")
        ml_sd_score = score_result.get("ml_sway_sd_score")
        step_gap_score = score_result.get("step_gap_score")

        if all(x is not None for x in [ml_mean_score, ml_sd_score, step_gap_score]):
            partial_score = ml_mean_score + ml_sd_score + step_gap_score
            max_partial = 20
            total_score = partial_score
            percentage = (partial_score / max_partial) * 100
            interpretation = f"Partial (front-view): {partial_score}/{max_partial} ({percentage:.1f}%)"

    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": total_score,
        "maxScore": 32,
        "interpretation": interpretation or "N/A",
        "eyesOpen": eyes_open,
    }
