"""
Common utilities for video processing with MediaPipe
"""

import os
import shutil
import subprocess
import tempfile
import cv2
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any
from collections import deque


# ─────────────────────────────────────────────────────────────────
# MOV▶MP4 AUTO-CONVERSION (if ffmpeg is available)
# ─────────────────────────────────────────────────────────────────

def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in PATH."""
    return shutil.which("ffmpeg") is not None


def convert_mov_to_mp4(mov_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert MOV file to MP4 using ffmpeg.
    
    Args:
        mov_path: Path to the MOV file
        
    Returns:
        Tuple of (mp4_path, error_message)
        - If successful: (path_to_mp4, None)
        - If failed: (None, error_message)
    """
    if not os.path.exists(mov_path):
        return None, f"File not found: {mov_path}"
    
    if not is_ffmpeg_available():
        return None, "ffmpeg not installed. Please convert MOV to MP4 manually or install ffmpeg."
    
    # Create output path in same directory
    base_dir = os.path.dirname(mov_path)
    base_name = os.path.splitext(os.path.basename(mov_path))[0]
    mp4_path = os.path.join(base_dir, f"{base_name}_converted.mp4")
    
    try:
        # Run ffmpeg conversion
        cmd = [
            "ffmpeg", "-y", "-i", mov_path,
            "-c:v", "libx264", "-preset", "fast",
            "-crf", "23", "-an", mp4_path
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            return None, f"ffmpeg conversion failed: {result.stderr[:200]}"
        
        if os.path.exists(mp4_path):
            return mp4_path, None
        else:
            return None, "ffmpeg ran but output file not found"
            
    except subprocess.TimeoutExpired:
        return None, "Video conversion timed out (>5 min)"
    except Exception as e:
        return None, f"Conversion error: {str(e)}"


def ensure_video_readable(video_path: str) -> Tuple[str, Optional[str]]:
    """
    Ensure video is readable by OpenCV. If MOV, try to convert to MP4.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Tuple of (usable_path, error_message)
        - If readable: (video_path, None)
        - If converted: (mp4_path, None)
        - If failed: (original_path, error_message)
    """
    if not video_path or not os.path.exists(video_path):
        return video_path, "File not found"
    
    # First, try to open directly
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if frames > 0:
            return video_path, None
    cap.release()
    
    # If MOV/QuickTime file couldn't be opened, try ffmpeg conversion
    ext = os.path.splitext(video_path)[1].lower()
    if ext == ".mov":
        print(f"[VIDEO] MOV file not readable by OpenCV, attempting ffmpeg conversion...")
        mp4_path, err = convert_mov_to_mp4(video_path)
        if mp4_path:
            print(f"[VIDEO] Successfully converted to: {mp4_path}")
            return mp4_path, None
        else:
            print(f"[VIDEO] Conversion failed: {err}")
            return video_path, f"MOV file cannot be read. {err}"
    
    return video_path, f"Video file cannot be opened by OpenCV: {video_path}"

# MediaPipe setup
import mediapipe as mp
mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

# Landmark indices
LM = {
    "NOSE": int(PL.NOSE),
    "L_EYE": int(PL.LEFT_EYE_INNER),
    "R_EYE": int(PL.RIGHT_EYE_INNER),
    "L_EAR": int(PL.LEFT_EAR),
    "R_EAR": int(PL.RIGHT_EAR),
    "L_SH": int(PL.LEFT_SHOULDER),
    "R_SH": int(PL.RIGHT_SHOULDER),
    "L_EL": int(PL.LEFT_ELBOW),
    "R_EL": int(PL.RIGHT_ELBOW),
    "L_WR": int(PL.LEFT_WRIST),
    "R_WR": int(PL.RIGHT_WRIST),
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


def _finite(a):
    """Filter to finite values only"""
    a = np.asarray(a, dtype=float)
    return a[np.isfinite(a)]


def _nanmedian_safe(x):
    """Safe median computation"""
    x = _finite(x)
    return float(np.nanmedian(x)) if x.size else None


def _mean_safe(x):
    """Safe mean computation"""
    x = _finite(x)
    return float(np.nanmean(x)) if x.size else None


def _wrap_deg(a):
    """Wrap angle to [-180, 180]"""
    a = (a + 180.0) % 360.0 - 180.0
    return a


def angle_3pt(a, b, c, eps=1e-8) -> float:
    """Compute angle ABC in degrees"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    c = np.asarray(c, float)
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


def angle_between_vecs(v1, v2, eps=1e-8) -> float:
    """Angle between two vectors in degrees"""
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < eps or n2 < eps:
        return np.nan
    c = float(np.dot(v1, v2) / (n1 * n2))
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def _P2(df: pd.DataFrame, idx: int) -> np.ndarray:
    """Get Nx2 pixel coords for landmark idx"""
    cx, cy = f"x{idx}", f"y{idx}"
    if cx not in df.columns or cy not in df.columns:
        return np.full((len(df), 2), np.nan, dtype=float)
    return np.column_stack([df[cx].to_numpy(float), df[cy].to_numpy(float)])


def _P2N(df: pd.DataFrame, idx: int) -> np.ndarray:
    """Get Nx2 normalized coords for landmark idx"""
    cx, cy = f"xn{idx}", f"yn{idx}"
    if cx not in df.columns or cy not in df.columns:
        return np.full((len(df), 2), np.nan, dtype=float)
    return np.column_stack([df[cx].to_numpy(float), df[cy].to_numpy(float)])


def _P3(df: pd.DataFrame, idx: int) -> np.ndarray:
    """Get Nx3 world coords for landmark idx"""
    cx, cy, cz = f"xw{idx}", f"yw{idx}", f"zw{idx}"
    if cx not in df.columns:
        return np.full((len(df), 3), np.nan, dtype=float)
    return np.column_stack([
        df[cx].to_numpy(float),
        df[cy].to_numpy(float),
        df[cz].to_numpy(float)
    ])


def _mid(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Midpoint of two arrays"""
    return (np.asarray(a, float) + np.asarray(b, float)) / 2.0


def rolling_med(x, k=5):
    """Rolling median filter"""
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()


def run_pose_extraction(
    video_path: str,
    frame_stride: int = 2,
    downscale: float = 1.0,
    model_complexity: int = 1,
    max_frames: Optional[int] = None,
    include_world: bool = True
) -> Tuple[pd.DataFrame, float]:
    """
    Extract pose landmarks from video using MediaPipe.
    Returns (dataframe, fps).
    """
    import os
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
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_stride == 0:
                h, w = frame.shape[:2]
                if downscale != 1.0 and downscale > 0:
                    nw, nh = int(w * downscale), int(h * downscale)
                    if nw > 0 and nh > 0:
                        frame = cv2.resize(frame, (nw, nh))
                        h, w = nh, nw

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


def pelvis_width_xy(P2):
    """Get pelvis width from 2D landmarks"""
    d = np.linalg.norm(P2[LM["L_HP"]] - P2[LM["R_HP"]])
    return float(d) if d > 1e-8 else np.nan


def estimate_floor_y(P2, H=None):
    """Estimate floor Y position from ankle landmarks"""
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


def rising_edges(st_bool):
    """Find rising edges in boolean signal"""
    st = np.asarray(st_bool, dtype=bool)
    return np.where((~st[:-1]) & (st[1:]))[0] + 1


def falling_edges(st_bool):
    """Find falling edges in boolean signal"""
    st = np.asarray(st_bool, dtype=bool)
    return np.where((st[:-1]) & (~st[1:]))[0] + 1


def safe_mean(arr):
    """Safe mean of array"""
    s = pd.Series(arr, dtype=float).dropna()
    return float(s.mean()) if len(s) else np.nan


def safe_max(arr):
    """Safe max of array"""
    s = pd.Series(arr, dtype=float).dropna()
    return float(s.max()) if len(s) else np.nan


def detect_view_from_video(video_path: str, sample_frames: int = 30) -> Dict[str, Any]:
    """
    Auto-detect if video is front or side view based on pose landmark analysis.
    
    Returns dict with:
        - detected_view: "front" or "side"
        - confidence: 0.0-1.0
        - shoulder_x_diff_mean: avg X distance between L/R shoulders (high = front view)
        - shoulder_z_diff_mean: avg Z distance between L/R shoulders (high = side view)
        - details: explanation string
    """
    import os
    if not video_path or not os.path.exists(video_path):
        return {"detected_view": "unknown", "confidence": 0.0, "details": "Video not found"}
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"detected_view": "unknown", "confidence": 0.0, "details": "Cannot open video"}
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Sample from first 2 seconds
    frames_to_sample = min(sample_frames, total_frames, int(fps * 2))
    
    x_diffs = []  # shoulder X difference (high = front view)
    z_diffs = []  # shoulder Z difference (high = side view)
    pelvis_x_diffs = []
    pelvis_z_diffs = []
    
    with mp_pose.Pose(model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        frame_idx = 0
        sampled = 0
        
        while sampled < frames_to_sample:
            ok, frame = cap.read()
            if not ok:
                break
            
            # Sample every few frames
            if frame_idx % max(1, total_frames // frames_to_sample) != 0:
                frame_idx += 1
                continue
            
            H, W = frame.shape[:2]
            res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if res.pose_landmarks and res.pose_world_landmarks:
                P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
                
                # Shoulder analysis
                L_sh = P3[LM['L_SH']]
                R_sh = P3[LM['R_SH']]
                L_hp = P3[LM['L_HP']]
                R_hp = P3[LM['R_HP']]
                
                # X difference (pixel space normalized) - high for front view
                x_diff = abs(P2[LM['L_SH'], 0] - P2[LM['R_SH'], 0]) / W
                x_diffs.append(x_diff)
                
                # Z difference (3D world coords) - high for side view
                z_diff = abs(L_sh[2] - R_sh[2])
                z_diffs.append(z_diff)
                
                # Same for pelvis
                px_diff = abs(P2[LM['L_HP'], 0] - P2[LM['R_HP'], 0]) / W
                pz_diff = abs(L_hp[2] - R_hp[2])
                pelvis_x_diffs.append(px_diff)
                pelvis_z_diffs.append(pz_diff)
                
                sampled += 1
            
            frame_idx += 1
    
    cap.release()
    
    if len(x_diffs) < 5:
        return {"detected_view": "unknown", "confidence": 0.0, "details": "Insufficient pose detections"}
    
    # Compute averages
    mean_x_diff = float(np.mean(x_diffs))
    mean_z_diff = float(np.mean(z_diffs))
    mean_px_diff = float(np.mean(pelvis_x_diffs))
    mean_pz_diff = float(np.mean(pelvis_z_diffs))
    
    # Decision logic:
    # Front view: shoulders are spread horizontally (high X diff), low Z diff
    # Side view: shoulders are aligned (low X diff), high Z diff
    
    x_ratio = (mean_x_diff + mean_px_diff) / 2  # Combined shoulder+pelvis X spread
    z_ratio = (mean_z_diff + mean_pz_diff) / 2  # Combined Z depth difference
    
    # Front view threshold: X spread > 0.1 and Z diff < 0.15
    # Side view threshold: X spread < 0.1 and Z diff > 0.1
    
    if x_ratio > 0.12 and z_ratio < 0.18:
        detected = "front"
        confidence = min(1.0, (x_ratio / 0.15) * 0.5 + (0.18 - z_ratio) / 0.18 * 0.5)
    elif x_ratio < 0.10 and z_ratio > 0.08:
        detected = "side"
        confidence = min(1.0, (0.12 - x_ratio) / 0.12 * 0.5 + (z_ratio / 0.15) * 0.5)
    else:
        # Ambiguous - use ratio comparison
        if x_ratio > z_ratio * 1.2:
            detected = "front"
            confidence = 0.5
        else:
            detected = "side"
            confidence = 0.5
    
    details = f"X-spread={x_ratio:.3f}, Z-depth={z_ratio:.3f}"
    
    return {
        "detected_view": detected,
        "confidence": round(confidence, 2),
        "shoulder_x_diff_mean": round(mean_x_diff, 4),
        "shoulder_z_diff_mean": round(mean_z_diff, 4),
        "details": details
    }
