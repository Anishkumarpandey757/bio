import streamlit as st
import cv2
import numpy as np
import pandas as pd
import tempfile
import os

# Import scoring functions from local math.py file
import importlib.util
import os

# Load the local math.py file explicitly
math_file_path = os.path.join(os.path.dirname(__file__), 'math.py')
spec = importlib.util.spec_from_file_location("scoring_math", math_file_path)
scoring_math = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring_math)

# Extract the functions we need for both age groups
# 7-year functions
score_sway_ss_mean_7y = scoring_math.score_sway_ss_mean_7y
score_sway_ss_sd_7y = scoring_math.score_sway_ss_sd_7y
score_sway_ap_mean_7y = scoring_math.score_sway_ap_mean_7y
score_sway_ap_sd_7y = scoring_math.score_sway_ap_sd_7y
score_row_7y = scoring_math.score_row_7y

# 6-year functions
score_sway_ss_mean_6y = scoring_math.score_sway_ss_mean_6y
score_sway_ss_sd_6y = scoring_math.score_sway_ss_sd_6y
score_sway_ap_mean_6y = scoring_math.score_sway_ap_mean_6y
score_sway_ap_sd_6y = scoring_math.score_sway_ap_sd_6y
score_row_6y = scoring_math.score_row_6y

# MediaPipe setup - import with error handling
try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except ImportError as e:
    st.error(f"❌ MediaPipe not installed or incompatible. Please install: pip install mediapipe")
    st.stop()
except AttributeError as e:
    st.error(f"❌ MediaPipe version issue. Please update: pip install --upgrade mediapipe")
    st.stop()

# Landmark indices (same as OLS)
LM = dict(
    NOSE=0, L_EYE=1, R_EYE=2, L_EAR=7, R_EAR=8,
    L_SH=11, R_SH=12, L_EL=13, R_EL=14, L_WR=15, R_WR=16,
    L_HP=23, R_HP=24, L_KN=25, R_KN=26, L_AN=27, R_AN=28
)

# OLS calibration constant
OLS_PX_PER_CM = 3.2

def angle_3pt(A, B, C, eps=1e-8):
    """3-point angle at B."""
    BA, BC = A - B, C - B
    na, nc = np.linalg.norm(BA), np.linalg.norm(BC)
    if na < eps or nc < eps:
        return np.nan
    cosv = np.dot(BA, BC) / (na * nc)
    return float(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))))

def angle_to_vertical(P0, P1):
    """Unsigned angle to vertical."""
    v = (P1 - P0).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8:
        return np.nan
    v /= n
    return float(np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0, -1.0])), -1, 1))))

def angle_signed_to_vertical(P0, P1):
    """Signed trunk angle (deg) vs vertical; + = lean right, - = lean left."""
    v = (P1 - P0).astype(float)
    n = np.linalg.norm(v)
    if n < 1e-8:
        return np.nan
    v /= n
    unsigned = np.degrees(np.arccos(np.clip(np.dot(v, np.array([0.0, -1.0])), -1, 1)))
    sgn = 1.0 if v[0] >= 0 else -1.0
    return float(sgn * unsigned)

def angle_between_vecs(v1, v2, eps=1e-8):
    """Angle between two vectors."""
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < eps or n2 < eps:
        return np.nan
    c = np.dot(v1, v2) / (n1 * n2)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))

def pelvis_width_xy(P2):
    """Pelvis width in pixels."""
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan

def estimate_floor_y(P2, H=None):
    """Estimate floor Y coordinate."""
    ys = [P2[LM['L_AN'], 1], P2[LM['R_AN'], 1]]
    if P2.shape[0] >= 33:
        ys += [P2[29, 1], P2[30, 1], P2[31, 1], P2[32, 1]]
    y = np.array(ys, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H * 0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))

def rolling_med(x, k=5):
    """Rolling median filter."""
    return pd.Series(x, dtype=float).rolling(k, center=True, min_periods=1).median().to_numpy()

def count_transitions(boolean_series, min_gap_frames=6):
    """Count rising edges with debounce."""
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

def measure_ols_video(video_path, view="front", raised_leg="L", smooth_k=5, progress_bar=None):
    """
    Full OLS per-frame measurement (identical to ols_leftleg_eo.py).
    Returns DataFrame with all kinematic parameters.
    """
    cols = [
        "trunk_signed_deg", "trunk_abs_deg", "neck_goni_deg",
        "hip_R", "hip_L", "knee_R", "knee_L",
        "raised_ank_h", "raised_toe_h",
        "wristL_hipL_norm", "wristR_hipR_norm",
        "y_floor", "pelvis_px", "sh_x", "sh_y", "hp_x", "hp_y",
        "x29", "y29", "x30", "y30", "x31", "y31", "x32", "y32"
    ]
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or not (10 < fps < 120):
        fps = 30.0
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    rows = []
    frame_idx = 0
    
    with mp_pose.Pose(
        model_complexity=1,
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
                rows.append([np.nan] * len(cols))
                frame_idx += 1
                continue
            
            # 2D + 3D landmarks
            P2 = np.array([[lm.x * W, lm.y * H] for lm in res.pose_landmarks.landmark], dtype=float)
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = P2.copy()
            
            # Centers
            sh2 = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
            hp2 = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
            sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
            hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
            ear3 = (P3[LM['L_EAR']] + P3[LM['R_EAR']]) / 2.0
            
            # Trunk sway
            trunk_signed = angle_signed_to_vertical(hp2, sh2)
            trunk_abs = abs(trunk_signed)
            
            # Neck goniometer
            trunk_vec = sh3 - hp3
            head_vec = ear3 - sh3
            neck_goni_deg = angle_between_vecs(trunk_vec, head_vec)
            
            # Hip/Knee angles
            hip_R = 180.0 - angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])
            hip_L = 180.0 - angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])
            knee_R = 180.0 - angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])
            knee_L = 180.0 - angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])
            
            # Floor & scale
            y_floor = estimate_floor_y(P2, H=H)
            px_scale = pelvis_width_xy(P2) or np.nan
            
            # Raised foot heights
            ankL_y = float(P2[LM['L_AN'], 1])
            ankR_y = float(P2[LM['R_AN'], 1])
            toeL_y = float(P2[31, 1]) if P2.shape[0] >= 33 else np.nan
            toeR_y = float(P2[32, 1]) if P2.shape[0] >= 33 else np.nan
            
            def _nh(y):
                if not np.isfinite(y) or not np.isfinite(y_floor) or not np.isfinite(px_scale) or px_scale <= 0:
                    return np.nan
                return max((y_floor - y) / px_scale, 0.0)
            
            if raised_leg.upper() == "L":
                raised_ank_h = _nh(ankL_y)
                raised_toe_h = _nh(toeL_y)
            else:
                raised_ank_h = _nh(ankR_y)
                raised_toe_h = _nh(toeR_y)
            
            # Wrist-hip distances
            d_L = np.linalg.norm(P2[LM['L_WR']] - P2[LM['L_HP']]) / (px_scale if np.isfinite(px_scale) else np.nan)
            d_R = np.linalg.norm(P2[LM['R_WR']] - P2[LM['R_HP']]) / (px_scale if np.isfinite(px_scale) else np.nan)
            
            # Heel/Toe coords
            x29, y29 = (P2[29, 0], P2[29, 1]) if P2.shape[0] > 29 else (np.nan, np.nan)
            x30, y30 = (P2[30, 0], P2[30, 1]) if P2.shape[0] > 30 else (np.nan, np.nan)
            x31, y31 = (P2[31, 0], P2[31, 1]) if P2.shape[0] > 31 else (np.nan, np.nan)
            x32, y32 = (P2[32, 0], P2[32, 1]) if P2.shape[0] > 32 else (np.nan, np.nan)
            
            rows.append([
                trunk_signed, trunk_abs, neck_goni_deg,
                hip_R, hip_L, knee_R, knee_L,
                raised_ank_h, raised_toe_h,
                d_L, d_R, y_floor, px_scale,
                sh2[0], sh2[1], hp2[0], hp2[1],
                x29, y29, x30, y30, x31, y31, x32, y32
            ])
            frame_idx += 1
    
    cap.release()
    df = pd.DataFrame(rows, columns=cols)
    
    # Smooth key series
    for k in ["trunk_signed_deg", "trunk_abs_deg", "neck_goni_deg",
              "hip_R", "hip_L", "knee_R", "knee_L",
              "raised_ank_h", "raised_toe_h",
              "wristL_hipL_norm", "wristR_hipR_norm"]:
        df[k] = rolling_med(df[k].values, k=smooth_k)
    
    return df, float(fps)

def count_toe_touches(df, fps, norm_thr=0.03, min_frames=3, min_gap_s=0.30):
    """Count toe touches."""
    toe = pd.Series(df["raised_toe_h"], dtype=float)
    near = toe <= norm_thr
    run, touch_idxs = 0, []
    for i, ok in enumerate(near.fillna(False).to_numpy()):
        if ok:
            run += 1
            if run == min_frames:
                touch_idxs.append(i)
        else:
            run = 0
    if fps <= 0:
        fps = 30.0
    refr = int(fps * min_gap_s)
    cnt, last = 0, -10**9
    for i in touch_idxs:
        if i - last >= refr:
            cnt += 1
            last = i
    return int(cnt)

def ols_events_and_strategy(df, fps, raised_leg="L", age_tag="7yrs",
                            ank_up=0.15, ank_down=0.05, min_contact_gap_frames=8,
                            onhip_thr=0.35, min_off_gap_frames=6):
    """Calculate foot touches, toe touches, hands-off, and strategy."""
    # Ankle-based contact
    ank = pd.Series(df["raised_ank_h"], dtype=float)
    up = ank > ank_up
    down = ank < ank_down
    grounded = pd.Series(False, index=ank.index)
    state = True if (len(down) and bool(down.iloc[0])) else False
    grounded.iloc[0] = state
    for i in range(1, len(ank)):
        if state:
            if up.iloc[i]:
                state = False
        else:
            if down.iloc[i]:
                state = True
        grounded.iloc[i] = state
    foot_touches_ankle = count_transitions(grounded.diff().fillna(0) > 0,
                                           min_gap_frames=min_contact_gap_frames)
    
    # Toe touches
    toe_thr = 0.035 if age_tag == "6yrs" else 0.025
    toe_touches = count_toe_touches(df, fps, norm_thr=toe_thr, min_frames=3,
                                    min_gap_s=0.35 if age_tag == "6yrs" else 0.30)
    
    # Hands off hips
    onL = pd.Series(df["wristL_hipL_norm"], dtype=float) <= onhip_thr
    onR = pd.Series(df["wristR_hipR_norm"], dtype=float) <= onhip_thr
    both_on = (onL & onR)
    hands_off = ~both_on
    hands_off_cnt = count_transitions(hands_off, min_gap_frames=min_off_gap_frames)
    hands_off_pct = float(hands_off.mean()) if len(hands_off) else 0.0
    
    # Strategy
    airborne = ~grounded
    def _med(series_name):
        s = df.loc[airborne, series_name] if airborne.any() else df[series_name]
        return float(pd.Series(s, dtype=float).median())
    
    med_trunk = _med("trunk_abs_deg")
    med_hip = float(pd.concat([df["hip_L"], df["hip_R"]], axis=1).median().median())
    med_knee = float(pd.concat([df["knee_L"], df["knee_R"]], axis=1).median().median())
    
    if foot_touches_ankle > 0 or toe_touches > 0:
        strategy = "Stepping"
    elif med_knee >= 15 and med_trunk < 10:
        strategy = "Knee strategy"
    elif med_hip >= 15 and med_trunk >= 7:
        strategy = "Hip strategy"
    else:
        strategy = "Ankle/minimal"
    
    return dict(
        foot_touches_ankle=int(foot_touches_ankle),
        toe_touches=int(toe_touches),
        hands_off_cnt=int(hands_off_cnt),
        hands_off_pct=hands_off_pct,
        strategy=strategy,
        med_trunk_deg=med_trunk,
        med_hip_deg=med_hip,
        med_knee_deg=med_knee
    )

def foot_drift_metrics(df, raised_leg="L", px_per_cm=OLS_PX_PER_CM):
    """Calculate foot drift displacement."""
    def _stance_ball_xy(df, raised_leg, alpha=0.30):
        rl = raised_leg.upper()
        if rl == "L":
            need = {"x30", "y30", "x32", "y32"}
            if not need.issubset(df.columns):
                return None
            heel = df[["x30", "y30"]].to_numpy(dtype=float)
            toe = df[["x32", "y32"]].to_numpy(dtype=float)
        else:
            need = {"x29", "y29", "x31", "y31"}
            if not need.issubset(df.columns):
                return None
            heel = df[["x29", "y29"]].to_numpy(dtype=float)
            toe = df[["x31", "y31"]].to_numpy(dtype=float)
        return toe + alpha * (heel - toe)
    
    ball = _stance_ball_xy(df, raised_leg, alpha=0.30)
    if ball is None or len(ball) == 0:
        return dict(drift_max_cm=None, drift_mean_cm=None, drift_max_px=None, drift_mean_px=None,
                    drift_lat_max_cm=None, drift_lat_mean_cm=None, drift_ap_max_cm=None, drift_ap_mean_cm=None,
                    drift_pelvis_max=None, drift_pelvis_mean=None)
    
    k0 = min(10, len(ball))
    start = np.nanmedian(ball[:k0], axis=0)
    delta = ball - start
    drift_px = np.linalg.norm(delta, axis=1)
    drift_lat_px = np.abs(delta[:, 0])
    drift_ap_px = np.abs(delta[:, 1])
    
    pelvis_px = float(df["pelvis_px"].median()) if "pelvis_px" in df.columns else np.nan
    
    def _to_cm(arr_px):
        return (arr_px / px_per_cm) if (px_per_cm and px_per_cm > 0) else None
    
    return dict(
        drift_max_px=float(np.nanmax(drift_px)),
        drift_mean_px=float(np.nanmean(drift_px)),
        drift_max_cm=float(np.nanmax(_to_cm(drift_px))) if _to_cm(drift_px) is not None else None,
        drift_mean_cm=float(np.nanmean(_to_cm(drift_px))) if _to_cm(drift_px) is not None else None,
        drift_lat_max_cm=float(np.nanmax(_to_cm(drift_lat_px))) if _to_cm(drift_lat_px) is not None else None,
        drift_lat_mean_cm=float(np.nanmean(_to_cm(drift_lat_px))) if _to_cm(drift_lat_px) is not None else None,
        drift_ap_max_cm=float(np.nanmax(_to_cm(drift_ap_px))) if _to_cm(drift_ap_px) is not None else None,
        drift_ap_mean_cm=float(np.nanmean(_to_cm(drift_ap_px))) if _to_cm(drift_ap_px) is not None else None,
        drift_pelvis_max=float(np.nanmax(drift_px / pelvis_px)) if np.isfinite(pelvis_px) and pelvis_px > 0 else None,
        drift_pelvis_mean=float(np.nanmean(drift_px / pelvis_px)) if np.isfinite(pelvis_px) and pelvis_px > 0 else None,
    )

def summarize_ols_clip(df, fps, view):
    """Sway summary statistics."""
    sway_abs = pd.Series(df["trunk_abs_deg"], dtype=float)
    mean_deg = float(sway_abs.mean())
    sd_deg = float(sway_abs.std(ddof=0))
    peak_deg = float(sway_abs.max())
    duration = float(len(df) / (fps if fps else 30.0))
    return dict(view=view, sway_mean_deg=mean_deg, sway_sd_deg=sd_deg,
                sway_peak_deg=peak_deg, clip_dur_s=duration)

def joint_means(df):
    """Joint angle means."""
    return dict(
        trunk_mean_deg=float(pd.Series(df["trunk_abs_deg"], dtype=float).mean(skipna=True)),
        hip_L_mean_deg=float(pd.Series(df["hip_L"], dtype=float).mean(skipna=True)),
        hip_R_mean_deg=float(pd.Series(df["hip_R"], dtype=float).mean(skipna=True)),
        knee_L_mean_deg=float(pd.Series(df["knee_L"], dtype=float).mean(skipna=True)),
        knee_R_mean_deg=float(pd.Series(df["knee_R"], dtype=float).mean(skipna=True)),
        neck_mean_deg=float(pd.Series(df["neck_goni_deg"], dtype=float).mean(skipna=True)),
    )

def main():
    st.set_page_config(page_title="OLS Balance Scorer", layout="wide")
    
    st.title("🏃 One Leg Stand Balance Assessment & Scoring")
    st.markdown("Upload **Front** and **Side** view videos to get automated balance scores using age-appropriate rubrics (6-year or 7-year).")
    
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
        age_tag = "6yrs" if "6" in age_group else "7yrs"
        
        # Display scoring information
        if age_tag == "6yrs":
            st.info(f"📊 Using **6-Year Rubric**: Max Score = 33 points (SS_mean:7 + SS_SD:7 + AP_mean:7 + AP_SD:6 + toe_touches:6)")
        else:
            st.info(f"📊 Using **7-Year Rubric**: Max Score = 30 points (SS_mean:7 + SS_SD:6 + AP_mean:6 + AP_SD:6 + toe_touches:5)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📹 Front View Video")
        front_video = st.file_uploader(
            "Upload Front View",
            type=["mp4", "mov", "avi", "mkv"],
            key="front"
        )
    
    with col2:
        st.subheader("📹 Side View Video")
        side_video = st.file_uploader(
            "Upload Side View",
            type=["mp4", "mov", "avi", "mkv"],
            key="side"
        )
    
    st.divider()
    
    if st.button("🚀 Process Videos & Calculate Scores", type="primary", use_container_width=True, disabled=not age_selected):
        
        if not front_video and not side_video:
            st.error("⚠️ Please upload at least one video (Front or Side).")
            return
        
        if not age_selected:
            st.error("⚠️ Please select an age group first.")
            return
        
        # Display selected scoring system
        st.success(f"✅ Using {age_group} scoring rubric for assessment")
        
        df_front = None
        df_side = None
        
        # Process Front Video
        results_front = {}
        if front_video:
            with st.spinner("🔄 Processing Front view video..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp.write(front_video.read())
                    tmp_path = tmp.name
                
                try:
                    progress_front = st.progress(0)
                    df_front, fps_front = measure_ols_video(
                        tmp_path, 
                        view="front",
                        raised_leg="L",
                        progress_bar=progress_front
                    )
                    st.success(f"✅ Front view processed: {len(df_front)} frames")
                    
                    # Calculate all metrics for front
                    summ_front = summarize_ols_clip(df_front, fps_front, "front")
                    ev_front = ols_events_and_strategy(df_front, fps_front, raised_leg="L", age_tag=age_tag)
                    drift_front = foot_drift_metrics(df_front, raised_leg="L")
                    joint_front = joint_means(df_front)
                    
                    results_front = {**summ_front, **ev_front, **drift_front, **joint_front}
                finally:
                    os.unlink(tmp_path)
        
        # Process Side Video
        results_side = {}
        if side_video:
            with st.spinner("🔄 Processing Side view video..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp.write(side_video.read())
                    tmp_path = tmp.name
                
                try:
                    progress_side = st.progress(0)
                    df_side, fps_side = measure_ols_video(
                        tmp_path,
                        view="side",
                        raised_leg="L",
                        progress_bar=progress_side
                    )
                    st.success(f"✅ Side view processed: {len(df_side)} frames")
                    
                    # Calculate all metrics for side
                    summ_side = summarize_ols_clip(df_side, fps_side, "side")
                    ev_side = ols_events_and_strategy(df_side, fps_side, raised_leg="L", age_tag=age_tag)
                    drift_side = foot_drift_metrics(df_side, raised_leg="L")
                    joint_side = joint_means(df_side)
                    
                    results_side = {**summ_side, **ev_side, **drift_side, **joint_side}
                finally:
                    os.unlink(tmp_path)
        
        
        # Calculate parameters from video analysis results
        params = {}
        if df_front is not None and len(df_front) > 0:
            params["sway_SS_mean"] = results_front.get("sway_mean_deg")
            params["sway_SS_SD"] = results_front.get("sway_sd_deg")
        else:
            params["sway_SS_mean"] = None
            params["sway_SS_SD"] = None
        
        if df_side is not None and len(df_side) > 0:
            params["sway_AP_mean"] = results_side.get("sway_mean_deg")
            params["sway_AP_SD"] = results_side.get("sway_sd_deg")
            # Use side view for toe touches (more reliable)
            params["toe_touches"] = results_side.get("toe_touches")
        else:
            params["sway_AP_mean"] = None
            params["sway_AP_SD"] = None
            # Fallback to front view toe touches if available
            params["toe_touches"] = results_front.get("toe_touches") if results_front else None
        
        # Score using age-appropriate math.py functions
        st.subheader(f"📊 {age_group} Rubric - Calculated Parameters & Scores")
        
        if age_tag == "6yrs":
            # 6-year scoring system (max 33 points)
            scores = score_row_6y(params, use_toe_touch=True)
            max_score = 33
            score_ranges = {
                "ss_mean": "(1-7)",
                "ss_sd": "(1-7)", 
                "ap_mean": "(1-7)",
                "ap_sd": "(1-6)",
                "toe": "(1-6)"
            }
            st.caption("Using 6-year rubric: Higher scores available for most parameters")
        else:
            # 7-year scoring system (max 30 points) 
            scores = score_row_7y(params, use_toe_touch=True)
            max_score = 30
            score_ranges = {
                "ss_mean": "(1-7)",
                "ss_sd": "(1-6)",
                "ap_mean": "(1-6)", 
                "ap_sd": "(1-6)",
                "toe": "(1-5)"
            }
            st.caption("Using 7-year rubric: More stringent scoring thresholds")
        
        # Display results in a clean table
        results_data = [
            {
                "Parameter": "Sway SS Mean (Front)",
                "Raw Value": f"{params['sway_SS_mean']:.2f}°" if params['sway_SS_mean'] is not None else "N/A",
                "Score " + score_ranges["ss_mean"]: scores.get("sway_SS_mean_score", "N/A"),
                "Description": "Average side-to-side sway"
            },
            {
                "Parameter": "Sway SS SD (Front)",
                "Raw Value": f"{params['sway_SS_SD']:.2f}°" if params['sway_SS_SD'] is not None else "N/A",
                "Score " + score_ranges["ss_sd"]: scores.get("sway_SS_SD_score", "N/A"),
                "Description": "Variability of side-to-side sway"
            },
            {
                "Parameter": "Sway AP Mean (Side)",
                "Raw Value": f"{params['sway_AP_mean']:.2f}°" if params['sway_AP_mean'] is not None else "N/A",
                "Score " + score_ranges["ap_mean"]: scores.get("sway_AP_mean_score", "N/A"),
                "Description": "Average forward-backward sway"
            },
            {
                "Parameter": "Sway AP SD (Side)",
                "Raw Value": f"{params['sway_AP_SD']:.2f}°" if params['sway_AP_SD'] is not None else "N/A",
                "Score " + score_ranges["ap_sd"]: scores.get("sway_AP_SD_score", "N/A"),
                "Description": "Variability of forward-backward sway"
            },
            {
                "Parameter": "Toe Touches",
                "Raw Value": f"{int(params['toe_touches'])}" if params['toe_touches'] is not None else "N/A",
                "Score " + score_ranges["toe"]: scores.get("toe_touches_score", "N/A"),
                "Description": "Number of toe touches during balance"
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
        # max_score already set above based on age group
        
        st.divider()
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.metric("Total Score", f"{total_score}/{max_score}" if total_score != "N/A" else "N/A")
        
        with col_b:
            if isinstance(total_score, (int, float)):
                percentage = (total_score / max_score) * 100
                st.metric("Percentage", f"{percentage:.1f}%")
        
        with col_c:
            interpretation = scores.get("interpretation", f"{age_group} scoring")
            if interpretation and "parameter" not in str(interpretation):
                # Use the age-appropriate interpretation from math.py
                st.metric("Interpretation", interpretation)
            elif isinstance(total_score, (int, float)):
                # Fallback interpretation based on age group
                if age_tag == "6yrs":
                    # 6-year interpretation (max 33)
                    if total_score < 10:
                        interp = "Extremely Below Average"
                    elif total_score < 14:
                        interp = "Well-Below Average"
                    elif total_score < 18:
                        interp = "Below Average"
                    elif total_score < 26:
                        interp = "Average"
                    elif total_score < 30:
                        interp = "Above Average"
                    else:
                        interp = "Well-Above Average"
                else:
                    # 7-year interpretation (max 30)
                    if total_score < 13:
                        interp = "Extremely Below Average"
                    elif total_score < 16:
                        interp = "Well-Below Average"
                    elif total_score < 19:
                        interp = "Below Average"
                    elif total_score <= 25:
                        interp = "Average"
                    elif total_score <= 28:
                        interp = "Above Average"
                    else:
                        interp = "Well-Above Average"
                st.metric("Interpretation", interp)
        
        # All calculated parameters (non-scored)
        st.divider()
        st.subheader("📋 All Calculated Parameters")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            if results_front:
                st.markdown("**Front View Metrics:**")
                st.write(f"• Strategy: {results_front.get('strategy', 'N/A')}")
                st.write(f"• Foot touches (ankle): {results_front.get('foot_touches_ankle', 'N/A')}")
                st.write(f"• Toe touches: {results_front.get('toe_touches', 'N/A')}")
                st.write(f"• Hands off count: {results_front.get('hands_off_cnt', 'N/A')}")
                st.write(f"• Trunk mean: {results_front.get('trunk_mean_deg', 0):.2f}°")
                st.write(f"• Neck mean: {results_front.get('neck_mean_deg', 0):.2f}°")
                st.write(f"• Hip L/R mean: {results_front.get('hip_L_mean_deg', 0):.1f}° / {results_front.get('hip_R_mean_deg', 0):.1f}°")
                st.write(f"• Knee L/R mean: {results_front.get('knee_L_mean_deg', 0):.1f}° / {results_front.get('knee_R_mean_deg', 0):.1f}°")
        
        with col_right:
            if results_side:
                st.markdown("**Side View Metrics:**")
                st.write(f"• Strategy: {results_side.get('strategy', 'N/A')}")
                st.write(f"• Foot touches (ankle): {results_side.get('foot_touches_ankle', 'N/A')}")
                st.write(f"• Toe touches: {results_side.get('toe_touches', 'N/A')}")
                st.write(f"• Hands off count: {results_side.get('hands_off_cnt', 'N/A')}")
                st.write(f"• Trunk mean: {results_side.get('trunk_mean_deg', 0):.2f}°")
                st.write(f"• Neck mean: {results_side.get('neck_mean_deg', 0):.2f}°")
                st.write(f"• Hip L/R mean: {results_side.get('hip_L_mean_deg', 0):.1f}° / {results_side.get('hip_R_mean_deg', 0):.1f}°")
                st.write(f"• Knee L/R mean: {results_side.get('knee_L_mean_deg', 0):.1f}° / {results_side.get('knee_R_mean_deg', 0):.1f}°")
        
        # Drift metrics
        with st.expander("🦶 Foot Drift Displacement Metrics"):
            tab_drift1, tab_drift2 = st.tabs(["Front View", "Side View"])
            
            with tab_drift1:
                if results_front and "drift_max_cm" in results_front:
                    st.write(f"Max drift: {results_front.get('drift_max_cm', 'N/A')} cm")
                    st.write(f"Mean drift: {results_front.get('drift_mean_cm', 'N/A')} cm")
                    st.write(f"Lateral max: {results_front.get('drift_lat_max_cm', 'N/A')} cm")
                    st.write(f"AP max: {results_front.get('drift_ap_max_cm', 'N/A')} cm")
            
            with tab_drift2:
                if results_side and "drift_max_cm" in results_side:
                    st.write(f"Max drift: {results_side.get('drift_max_cm', 'N/A')} cm")
                    st.write(f"Mean drift: {results_side.get('drift_mean_cm', 'N/A')} cm")
                    st.write(f"Lateral max: {results_side.get('drift_lat_max_cm', 'N/A')} cm")
                    st.write(f"AP max: {results_side.get('drift_ap_max_cm', 'N/A')} cm")
        
        # Download results as Excel
        st.divider()
        
        # Combine all results for Excel export
        export_data = {
            "Student": student_name or "Unknown",
            "Age Group": age_group,
            **params,
            **scores,
        }
        if results_front:
            for k, v in results_front.items():
                export_data[f"Front_{k}"] = v
        if results_side:
            for k, v in results_side.items():
                export_data[f"Side_{k}"] = v
        
        export_df = pd.DataFrame([export_data])
        csv_data = export_df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download Complete Results as CSV",
            data=csv_data,
            file_name=f"ols_complete_{student_name if student_name else 'student'}.csv",
            mime="text/csv"
        )
        
        # Show frame-by-frame data
        with st.expander("📈 View Frame-by-Frame Data"):
            tab1, tab2 = st.tabs(["Front View", "Side View"])
            
            with tab1:
                if df_front is not None:
                    st.line_chart(df_front["trunk_abs_deg"], use_container_width=True)
                    st.caption("Trunk sway angle over time (Front view)")
                else:
                    st.info("No front view data available")
            
            with tab2:
                if df_side is not None:
                    st.line_chart(df_side["trunk_abs_deg"], use_container_width=True)
                    st.caption("Trunk sway angle over time (Side view)")
                else:
                    st.info("No side view data available")

if __name__ == "__main__":
    main()
