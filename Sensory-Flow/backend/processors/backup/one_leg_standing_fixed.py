
"""
Fixed One Leg Standing backend for Colab/backend use.

What is fixed:
- No duplicate notebook cells/functions.
- Consistent column names: uses neck_goni_deg everywhere.
- Clear raised_leg meaning: pass the ACTUAL lifted leg ("L" or "R").
- Works with front + side videos without notebook-only code.
- Keeps event logic aligned with your Colab OLS notebooks.
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
    # Fallback if common not available
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


def pelvis_width_xy(P2):
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan


def estimate_floor_y(P2, H=None):
    ys = [P2[LM['L_AN'], 1], P2[LM['R_AN'], 1]]
    if P2.shape[0] >= 33:
        ys += [P2[29, 1], P2[30, 1], P2[31, 1], P2[32, 1]]
    y = np.asarray(ys, float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H * 0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))


def _angle_signed_to_vertical(p0, p1):
    v = (np.asarray(p1, float) - np.asarray(p0, float))
    n = np.linalg.norm(v)
    if n < 1e-8:
        return np.nan
    v = v / n
    unsigned = np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0, -1.0])), -1.0, 1.0)))
    sgn = 1.0 if v[0] >= 0 else -1.0
    return float(sgn * unsigned)


def _count_transitions(boolean_series, min_gap_frames=6):
    b = pd.Series(boolean_series, dtype=bool).fillna(False).to_numpy()
    cnt, cool = 0, 0
    for i in range(1, len(b)):
        if cool > 0:
            cool -= 1
            continue
        if (not b[i-1]) and b[i]:
            cnt += 1
            cool = min_gap_frames
    return int(cnt)


def _count_toe_touches(toe_h, fps, norm_thr=0.03, min_frames=3, min_gap_s=0.30):
    near = pd.Series(toe_h, dtype=float).to_numpy() <= norm_thr
    run, touch_idxs = 0, []
    for i, ok in enumerate(near):
        v = toe_h[i] if i < len(toe_h) else np.nan
        if ok and np.isfinite(v):
            run += 1
            if run == min_frames:
                touch_idxs.append(i)
        else:
            run = 0
    refr = int(max(1, fps * min_gap_s)) if fps > 0 else 9
    cnt, last = 0, -10**9
    for i in touch_idxs:
        if i - last >= refr:
            cnt += 1
            last = i
    return int(cnt)


def measure_ols_video(video_path: str, view: str = "front", raised_leg: str = "L", smooth_k: int = 5,
                      model_complexity: int = 1) -> Tuple[pd.DataFrame, float]:
    if not isinstance(video_path, str) or not os.path.exists(video_path):
        print(f"[DEBUG OLS] Video file does not exist: {video_path}")
        return pd.DataFrame(), 30.0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[DEBUG OLS] ERROR: Cannot open video file (MOV/HEVC not supported): {video_path}")
        print(f"[DEBUG OLS] Please convert MOV files to MP4 format before uploading")
        return pd.DataFrame(), 30.0

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[DEBUG OLS] Video opened successfully: {frame_count} frames at {fps} fps")
    if not fps or not (10 < fps < 120):
        fps = 30.0
    fps = float(fps)

    cols = [
        "trunk_signed_deg", "trunk_abs_deg", "neck_goni_deg",
        "hip_R", "hip_L", "knee_R", "knee_L",
        "raised_ank_h", "raised_toe_h",
        "wristL_hipL_norm", "wristR_hipR_norm",
        "y_floor", "pelvis_px", "sh_x", "sh_y", "hp_x", "hp_y",
        "x29", "y29", "x30", "y30", "x31", "y31", "x32", "y32",
        "x23", "y23", "x24", "y24"
    ]
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
                rows.append([np.nan] * len(cols))
                continue

            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.concatenate([P2, np.zeros((P2.shape[0], 1))], axis=1)

            sh2 = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
            hp2 = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
            sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
            hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
            ear3 = (P3[LM['L_EAR']] + P3[LM['R_EAR']]) / 2.0

            trunk_signed = _angle_signed_to_vertical(hp2, sh2)
            trunk_abs = abs(trunk_signed) if np.isfinite(trunk_signed) else np.nan
            neck_goni_deg = angle_between_vecs(sh3 - hp3, ear3 - sh3)

            hip_R = 180.0 - angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])
            hip_L = 180.0 - angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])
            knee_R = 180.0 - angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])
            knee_L = 180.0 - angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])

            y_floor = estimate_floor_y(P2, H=H)
            px_scale = pelvis_width_xy(P2)

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

            wristL_norm = np.linalg.norm(P2[LM['L_WR']] - P2[LM['L_HP']]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan
            wristR_norm = np.linalg.norm(P2[LM['R_WR']] - P2[LM['R_HP']]) / px_scale if np.isfinite(px_scale) and px_scale > 0 else np.nan

            rows.append([
                trunk_signed, trunk_abs, neck_goni_deg,
                hip_R, hip_L, knee_R, knee_L,
                raised_ank_h, raised_toe_h,
                wristL_norm, wristR_norm,
                y_floor, px_scale, sh2[0], sh2[1], hp2[0], hp2[1],
                P2[29,0] if P2.shape[0] > 29 else np.nan, P2[29,1] if P2.shape[0] > 29 else np.nan,
                P2[30,0] if P2.shape[0] > 30 else np.nan, P2[30,1] if P2.shape[0] > 30 else np.nan,
                P2[31,0] if P2.shape[0] > 31 else np.nan, P2[31,1] if P2.shape[0] > 31 else np.nan,
                P2[32,0] if P2.shape[0] > 32 else np.nan, P2[32,1] if P2.shape[0] > 32 else np.nan,
                P2[LM['L_HP'],0], P2[LM['L_HP'],1], P2[LM['R_HP'],0], P2[LM['R_HP'],1],
            ])

    cap.release()
    df = pd.DataFrame(rows, columns=cols)
    for k in ["trunk_signed_deg", "trunk_abs_deg", "neck_goni_deg", "hip_R", "hip_L", "knee_R", "knee_L",
              "raised_ank_h", "raised_toe_h", "wristL_hipL_norm", "wristR_hipR_norm"]:
        df[k] = rolling_med(df[k].to_numpy(), k=smooth_k)
    return df, fps


def summarize_ols_clip(df: pd.DataFrame, fps: float) -> Dict[str, Any]:
    sway_abs = pd.Series(df.get("trunk_abs_deg", []), dtype=float).dropna()
    return {
        "sway_mean_deg": float(sway_abs.mean()) if len(sway_abs) else np.nan,
        "sway_sd_deg": float(sway_abs.std(ddof=0)) if len(sway_abs) else np.nan,
    }


def _stance_ball_xy(df: pd.DataFrame, raised_leg: str = "L", alpha: float = 0.30):
    rl = (raised_leg or "L").upper()
    if rl == "L":
        need = {"x30", "y30", "x32", "y32"}
        if not need.issubset(df.columns):
            return None
        heel = df[["x30", "y30"]].to_numpy(float)
        toe = df[["x32", "y32"]].to_numpy(float)
    else:
        need = {"x29", "y29", "x31", "y31"}
        if not need.issubset(df.columns):
            return None
        heel = df[["x29", "y29"]].to_numpy(float)
        toe = df[["x31", "y31"]].to_numpy(float)
    return toe + alpha * (heel - toe)


def _foot_drift_metrics(df: pd.DataFrame, raised_leg: str = "L", px_per_cm: Optional[float] = 3.2) -> Dict[str, Any]:
    ball = _stance_ball_xy(df, raised_leg=raised_leg)
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


def _summarize_neck(df: pd.DataFrame) -> Dict[str, float]:
    s = pd.Series(df.get("neck_goni_deg", []), dtype=float).dropna()
    return {
        "neck_mean_deg": float(s.mean()) if len(s) else np.nan,
        "neck_sd_deg": float(s.std(ddof=0)) if len(s) else np.nan,
        "neck_peak_deg": float(s.max()) if len(s) else np.nan,
    }


def _ols_events_and_strategy(df: pd.DataFrame, fps: float, raised_leg: str = "L", age_tag: str = "7yrs",
                             toe_norm_thr: float = 0.03, ank_norm_thr: float = 0.05,
                             wrist_hip_thr: float = 0.60) -> Dict[str, Any]:
    toe_h = pd.Series(df.get("raised_toe_h", []), dtype=float).to_numpy()
    ank_h = pd.Series(df.get("raised_ank_h", []), dtype=float).to_numpy()

    toe_touches = _count_toe_touches(toe_h, fps=fps, norm_thr=toe_norm_thr)
    foot_touches_ankle = _count_transitions(ank_h <= ank_norm_thr, min_gap_frames=max(3, int(0.2 * fps))) if len(ank_h) else 0

    wL = pd.Series(df.get("wristL_hipL_norm", []), dtype=float)
    wR = pd.Series(df.get("wristR_hipR_norm", []), dtype=float)
    hands_off_mask = (wL > wrist_hip_thr) | (wR > wrist_hip_thr)
    hands_off_cnt = _count_transitions(hands_off_mask.to_numpy(), min_gap_frames=max(3, int(0.2 * fps)))
    hands_off_pct = float(100.0 * hands_off_mask.mean()) if len(hands_off_mask) else np.nan

    med_trunk = float(pd.Series(df.get("trunk_abs_deg", []), dtype=float).median(skipna=True))
    med_hip = float(pd.Series(df[["hip_L", "hip_R"]].median(axis=1) if {"hip_L","hip_R"}.issubset(df.columns) else [], dtype=float).median(skipna=True))
    med_knee = float(pd.Series(df[["knee_L", "knee_R"]].median(axis=1) if {"knee_L","knee_R"}.issubset(df.columns) else [], dtype=float).median(skipna=True))

    if foot_touches_ankle >= 1:
        strategy = "stepping"
    elif np.isfinite(med_hip) and med_hip >= 20:
        strategy = "hip"
    elif np.isfinite(med_knee) and med_knee >= 20:
        strategy = "knee"
    else:
        strategy = "ankle"

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


def extract_ols_metrics(front_video_path: Optional[str] = None, side_video_path: Optional[str] = None,
                        raised_leg: str = "L", age_tag: str = "7yrs", px_per_cm: Optional[float] = 3.2) -> Dict[str, Any]:
    print(f"[DEBUG OLS] extract_ols_metrics called: front={front_video_path}, side={side_video_path}, raised_leg={raised_leg}")
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
    }

    if front_video_path and os.path.exists(front_video_path):
        print(f"[DEBUG OLS] Processing front video: {front_video_path}")
        df_front, fps_front = measure_ols_video(front_video_path, view="front", raised_leg=raised_leg)
        print(f"[DEBUG OLS] Front video: {len(df_front)} frames, fps={fps_front}")
        if len(df_front) > 10:
            summ = summarize_ols_clip(df_front, fps_front)
            print(f"[DEBUG OLS] Front sway summary: {summ}")
            metrics["sway_SS_mean"] = summ["sway_mean_deg"]
            metrics["sway_SS_SD"] = summ["sway_sd_deg"]
            metrics["fps"] = fps_front
            metrics.update(_summarize_neck(df_front))
            ev = _ols_events_and_strategy(df_front, fps_front, raised_leg=raised_leg, age_tag=age_tag)
            metrics["toe_touches"] = ev["toe_touches"]
            metrics["foot_touches"] = ev["foot_touches_ankle"]
            metrics["hands_off_cnt"] = ev["hands_off_cnt"]
            metrics["hands_off_pct"] = ev["hands_off_pct"]
            metrics["balance_strategy"] = ev["strategy"]
            metrics["med_trunk_deg"] = ev["med_trunk_deg"]
            metrics["med_hip_deg"] = ev["med_hip_deg"]
            metrics["med_knee_deg"] = ev["med_knee_deg"]
            metrics.update(_foot_drift_metrics(df_front, raised_leg=raised_leg, px_per_cm=px_per_cm))

    if side_video_path and os.path.exists(side_video_path):
        print(f"[DEBUG OLS] Processing side video: {side_video_path}")
        df_side, fps_side = measure_ols_video(side_video_path, view="side", raised_leg=raised_leg)
        print(f"[DEBUG OLS] Side video: {len(df_side)} frames, fps={fps_side}")
        if len(df_side) > 10:
            summ = summarize_ols_clip(df_side, fps_side)
            print(f"[DEBUG OLS] Side sway summary: {summ}")
            metrics["sway_AP_mean"] = summ["sway_mean_deg"]
            metrics["sway_AP_SD"] = summ["sway_sd_deg"]
            if metrics["fps"] is None:
                metrics["fps"] = fps_side
    print(f"[DEBUG OLS] Final metrics: sway_SS_mean={metrics['sway_SS_mean']}, sway_AP_mean={metrics['sway_AP_mean']}")
    return metrics


def process_one_leg_standing(
    front_video_path: Optional[str],
    side_video_path: Optional[str],
    age_years: int,
    eyes_open: bool = True,
    raised_leg: str = "L"
) -> Dict[str, Any]:
    """Process OLS videos and return scores - API wrapper for extract_ols_metrics."""
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
    raw_metrics = extract_ols_metrics(front_video_path, side_video_path, raised_leg, age_tag)
    
    print(f"[DEBUG OLS] process_one_leg_standing: sway_SS_mean={raw_metrics['sway_SS_mean']}, sway_AP_mean={raw_metrics['sway_AP_mean']}")
    
    if raw_metrics["sway_SS_mean"] is None and raw_metrics["sway_AP_mean"] is None:
        print("[DEBUG OLS] ERROR: No valid pose data extracted")
        return {
            "rawMetrics": raw_metrics, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": "Error: No valid pose data extracted from videos."
        }
    
    score_result = score_ols(raw_metrics, age_years=age_years, eyes_open=eyes_open, raised_leg=raised_leg)
    print(f"[DEBUG OLS] score_result: {score_result}")
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": score_result.get("total_score", 0),
        "maxScore": 34,
        "interpretation": score_result.get("interpretation", "N/A"),
        "eyesOpen": eyes_open,
        "raisedLeg": raised_leg,
    }
