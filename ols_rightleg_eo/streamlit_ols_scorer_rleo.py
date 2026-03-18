# Import scoring functions from local mathrreo.py file
import streamlit as st
import pandas as pd
import numpy as np
import cv2
import os
import tempfile
import importlib.util
from io import BytesIO

# Load the local mathrreo.py file explicitly
math_file_path = os.path.join(os.path.dirname(__file__), 'mathrreo.py')
spec = importlib.util.spec_from_file_location("scoring_math_rleo", math_file_path)
scoring_math_rleo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring_math_rleo)

# Extract the functions we need for both age groups (Right Leg Eyes Open)
# 7-year functions (RL EO)
score_sway_ss_mean_7y_rl_eo = scoring_math_rleo.score_sway_ss_mean_7y_rl_eo
score_sway_ss_sd_7y_rl_eo = scoring_math_rleo.score_sway_ss_sd_7y_rl_eo
score_sway_ap_mean_7y_rl_eo = scoring_math_rleo.score_sway_ap_mean_7y_rl_eo
score_sway_ap_sd_7y_rl_eo = scoring_math_rleo.score_sway_ap_sd_7y_rl_eo
score_row_7y_rl_eo = scoring_math_rleo.score_row_7y_rl_eo

# 6-year functions (RL EO)
score_sway_ss_mean_6y_rl_eo = scoring_math_rleo.score_sway_ss_mean_6y_rl_eo
score_sway_ss_sd_6y_rl_eo = scoring_math_rleo.score_sway_ss_sd_6y_rl_eo
score_sway_ap_mean_6y_rl_eo = scoring_math_rleo.score_sway_ap_mean_6y_rl_eo
score_sway_ap_sd_6y_rl_eo = scoring_math_rleo.score_sway_ap_sd_6y_rl_eo
score_row_6y_rl_eo = scoring_math_rleo.score_row_6y_rl_eo

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
        if (not b[i-1]) and b[i]:
            cnt += 1
            cool = min_gap_frames
    return int(cnt)

def measure_ols_video(video_path, view="front", raised_leg="R", smooth_k=5, progress_bar=None):
    """
    Full OLS per-frame measurement for Right Leg Eyes Open.
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
            ret, frame = cap.read()
            if not ret:
                break
                
            H, W = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)
            
            # Initialize row with NaN values
            row = [np.nan] * len(cols)
            
            if results.pose_landmarks:
                lms = results.pose_landmarks.landmark
                P3 = np.array([[lm.x * W, lm.y * H, lm.z * W] for lm in lms])
                P2 = P3[:, :2]
                
                if P2.shape[0] >= 29:
                    # Basic measurements
                    sh_mid = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
                    hp_mid = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
                    
                    # Trunk angle (signed and absolute)
                    trunk_signed = angle_signed_to_vertical(hp_mid, sh_mid)
                    trunk_abs = abs(trunk_signed) if not np.isnan(trunk_signed) else np.nan
                    
                    # Joint angles
                    hip_R = angle_3pt(P2[LM['R_SH']], P2[LM['R_HP']], P2[LM['R_KN']])
                    hip_L = angle_3pt(P2[LM['L_SH']], P2[LM['L_HP']], P2[LM['L_KN']])
                    knee_R = angle_3pt(P2[LM['R_HP']], P2[LM['R_KN']], P2[LM['R_AN']])
                    knee_L = angle_3pt(P2[LM['L_HP']], P2[LM['L_KN']], P2[LM['L_AN']])
                    
                    # Neck angle using 3D points for view-agnostic measurement
                    sh3_mid = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
                    hp3_mid = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
                    ear3_mid = (P3[LM['L_EAR']] + P3[LM['R_EAR']]) / 2.0
                    trunk_vec = sh3_mid - hp3_mid
                    head_vec = ear3_mid - sh3_mid
                    neck_goni = angle_between_vecs(trunk_vec, head_vec)
                    
                    # Floor and pelvis measurements
                    y_floor = estimate_floor_y(P2, H)
                    pelvis_px = pelvis_width_xy(P2)
                    
                    # Raised leg measurements (Right leg for RLEO)
                    raised_ank_h = np.nan
                    raised_toe_h = np.nan
                    if not np.isnan(y_floor) and pelvis_px > 0:
                        # Right ankle height (normalized by pelvis width)
                        r_ank_y = P2[LM['R_AN'], 1]
                        if not np.isnan(r_ank_y):
                            raised_ank_h = (y_floor - r_ank_y) / pelvis_px
                        
                        # Right toe height (if available)
                        if P2.shape[0] >= 33:
                            r_toe_y = P2[32, 1]  # Right big toe
                            if not np.isnan(r_toe_y):
                                raised_toe_h = (y_floor - r_toe_y) / pelvis_px
                    
                    # Wrist-hip distances (normalized)
                    wristL_hipL_norm = np.nan
                    wristR_hipR_norm = np.nan
                    if pelvis_px > 0:
                        wl_hl_dist = np.linalg.norm(P2[LM['L_WR']] - P2[LM['L_HP']])
                        wr_hr_dist = np.linalg.norm(P2[LM['R_WR']] - P2[LM['R_HP']])
                        wristL_hipL_norm = wl_hl_dist / pelvis_px
                        wristR_hipR_norm = wr_hr_dist / pelvis_px
                    
                    # Fill row data
                    row[cols.index("trunk_signed_deg")] = trunk_signed
                    row[cols.index("trunk_abs_deg")] = trunk_abs
                    row[cols.index("neck_goni_deg")] = neck_goni
                    row[cols.index("hip_R")] = hip_R
                    row[cols.index("hip_L")] = hip_L
                    row[cols.index("knee_R")] = knee_R
                    row[cols.index("knee_L")] = knee_L
                    row[cols.index("raised_ank_h")] = raised_ank_h
                    row[cols.index("raised_toe_h")] = raised_toe_h
                    row[cols.index("wristL_hipL_norm")] = wristL_hipL_norm
                    row[cols.index("wristR_hipR_norm")] = wristR_hipR_norm
                    row[cols.index("y_floor")] = y_floor
                    row[cols.index("pelvis_px")] = pelvis_px
                    row[cols.index("sh_x")] = sh_mid[0]
                    row[cols.index("sh_y")] = sh_mid[1]
                    row[cols.index("hp_x")] = hp_mid[0]
                    row[cols.index("hp_y")] = hp_mid[1]
                    
                    # Add heel/toe coordinates if available
                    if P2.shape[0] >= 33:
                        row[cols.index("x29")] = P2[29, 0]  # Left heel
                        row[cols.index("y29")] = P2[29, 1]
                        row[cols.index("x30")] = P2[30, 0]  # Right heel
                        row[cols.index("y30")] = P2[30, 1]
                        row[cols.index("x31")] = P2[31, 0]  # Left toe
                        row[cols.index("y31")] = P2[31, 1]
                        row[cols.index("x32")] = P2[32, 0]  # Right toe
                        row[cols.index("y32")] = P2[32, 1]
            
            rows.append(row)
            frame_idx += 1
            
            if progress_bar and total_frames > 0:
                progress_bar.progress(frame_idx / total_frames)
    
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
        else:
            if run >= min_frames:
                touch_idxs.append(i - run // 2)
            run = 0
    if run >= min_frames:
        touch_idxs.append(len(near) - run // 2)
    
    if fps <= 0:
        fps = 30.0
    refr = int(fps * min_gap_s)
    cnt, last = 0, -10**9
    for i in touch_idxs:
        if i - last >= refr:
            cnt += 1
            last = i
    return int(cnt)

def ols_events_and_strategy(df, fps, raised_leg="R", age_tag="7yrs",
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
    
    # Toe touches (Eyes Open thresholds)
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

def foot_drift_metrics(df, raised_leg="R", px_per_cm=OLS_PX_PER_CM):
    """Calculate foot drift displacement for Right Leg Eyes Open."""
    def _stance_ball_xy(df, raised_leg, alpha=0.30):
        rl = raised_leg.upper()
        if rl == "R":
            # Left foot is stance foot when right leg is raised
            heel = df[["x29", "y29"]].values  # Left heel
            toe = df[["x31", "y31"]].values   # Left toe
        else:
            # Right foot is stance foot when left leg is raised
            heel = df[["x30", "y30"]].values  # Right heel
            toe = df[["x32", "y32"]].values   # Right toe
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
    st.set_page_config(page_title="OLS Right Leg Eyes Open Scorer", layout="wide")
    
    st.title("🦵👁️ Right Leg Eyes Open Balance Assessment & Scoring")
    st.markdown("Upload **Front** and **Side** view videos to get automated balance scores using age-appropriate rubrics for **Right Leg Eyes Open** stance (6-year or 7-year).")
    
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
        
        # Display scoring information for Right Leg Eyes Open
        if age_tag == "6yrs":
            st.info("📋 **6-Year Right Leg Eyes Open Scoring:** Maximum total score = **31 points** (4 sway parameters + toe touches)")
        else:
            st.info("📋 **7-Year Right Leg Eyes Open Scoring:** Maximum total score = **29 points** (4 sway parameters + toe touches)")
    
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
    
    if st.button("🚀 Process Videos & Calculate RLEO Scores", type="primary", use_container_width=True, disabled=not age_selected):
        
        if not front_video and not side_video:
            st.error("⚠️ Please upload at least one video file to proceed.")
            return
        
        if not age_selected:
            st.error("⚠️ Please select an age group before processing.")
            return
        
        # Display selected scoring system
        st.success(f"✅ Using {age_group} Right Leg Eyes Open scoring rubric for assessment")
        
        df_front = None
        df_side = None
        
        # Process Front Video
        results_front = {}
        if front_video:
            with st.expander("🎬 Processing Front View Video...", expanded=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                    tmp_file.write(front_video.read())
                    tmp_path = tmp_file.name
                
                progress_bar = st.progress(0)
                st.text("Analyzing front view video for Right Leg Eyes Open stance...")
                
                try:
                    df_front, fps_front = measure_ols_video(tmp_path, view="front", raised_leg="R", progress_bar=progress_bar)
                    
                    if df_front is not None and len(df_front) > 0:
                        sway_front = summarize_ols_clip(df_front, fps_front, "front")
                        events_front = ols_events_and_strategy(df_front, fps_front, raised_leg="R", age_tag=age_tag)
                        drift_front = foot_drift_metrics(df_front, raised_leg="R")
                        joints_front = joint_means(df_front)
                        
                        results_front = {**sway_front, **events_front, **drift_front, **joints_front}
                        st.success(f"✅ Front view processed: {len(df_front)} frames, {sway_front['clip_dur_s']:.1f}s")
                    
                except Exception as e:
                    st.error(f"❌ Error processing front video: {str(e)}")
                finally:
                    os.unlink(tmp_path)
        
        # Process Side Video
        results_side = {}
        if side_video:
            with st.expander("🎬 Processing Side View Video...", expanded=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                    tmp_file.write(side_video.read())
                    tmp_path = tmp_file.name
                
                progress_bar = st.progress(0)
                st.text("Analyzing side view video for Right Leg Eyes Open stance...")
                
                try:
                    df_side, fps_side = measure_ols_video(tmp_path, view="side", raised_leg="R", progress_bar=progress_bar)
                    
                    if df_side is not None and len(df_side) > 0:
                        sway_side = summarize_ols_clip(df_side, fps_side, "side")
                        events_side = ols_events_and_strategy(df_side, fps_side, raised_leg="R", age_tag=age_tag)
                        drift_side = foot_drift_metrics(df_side, raised_leg="R")
                        joints_side = joint_means(df_side)
                        
                        results_side = {**sway_side, **events_side, **drift_side, **joints_side}
                        st.success(f"✅ Side view processed: {len(df_side)} frames, {sway_side['clip_dur_s']:.1f}s")
                    
                except Exception as e:
                    st.error(f"❌ Error processing side video: {str(e)}")
                finally:
                    os.unlink(tmp_path)
        
        
        # Calculate parameters from video analysis results
        params = {}
        if df_front is not None and len(df_front) > 0:
            params["sway_SS_mean"] = results_front.get("sway_mean_deg", 0)
            params["sway_SS_SD"] = results_front.get("sway_sd_deg", 0)
        else:
            params["sway_SS_mean"] = 0
            params["sway_SS_SD"] = 0
        
        if df_side is not None and len(df_side) > 0:
            params["sway_AP_mean"] = results_side.get("sway_mean_deg", 0)
            params["sway_AP_SD"] = results_side.get("sway_sd_deg", 0)
            params["toe_touches"] = results_side.get("toe_touches", 0)
        else:
            params["sway_AP_mean"] = 0
            params["sway_AP_SD"] = 0
            params["toe_touches"] = 0
        
        # Score using age-appropriate mathrreo.py functions
        st.subheader(f"📊 {age_group} Right Leg Eyes Open Rubric - Calculated Parameters & Scores")
        
        if age_tag == "6yrs":
            # Use 6-year Right Leg Eyes Open scoring
            scores = score_row_6y_rl_eo(params, use_toe_touch=True)
            max_score_text = "**Maximum Score: 31 points**"
        else:
            # Use 7-year Right Leg Eyes Open scoring  
            scores = score_row_7y_rl_eo(params, use_toe_touch=True)
            max_score_text = "**Maximum Score: 29 points**"
        
        # Display results in a clean table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Parameter table
            param_data = {
                "Parameter": [
                    "Sway SS Mean (deg)",
                    "Sway SS SD (deg)", 
                    "Sway AP Mean (deg)",
                    "Sway AP SD (deg)",
                    "Toe Touches (#)"
                ],
                "Value": [
                    f"{params['sway_SS_mean']:.2f}",
                    f"{params['sway_SS_SD']:.2f}",
                    f"{params['sway_AP_mean']:.2f}",
                    f"{params['sway_AP_SD']:.2f}",
                    f"{params['toe_touches']}"
                ],
                "Score": [
                    scores.get('sway_SS_mean_score', 'N/A'),
                    scores.get('sway_SS_SD_score', 'N/A'),
                    scores.get('sway_AP_mean_score', 'N/A'),
                    scores.get('sway_AP_SD_score', 'N/A'),
                    scores.get('toe_touches_score', 'N/A')
                ]
            }
            
            df_results = pd.DataFrame(param_data)
            st.dataframe(df_results, use_container_width=True, hide_index=True)
        
        with col2:
            # Score summary
            total_score = scores.get('total_score', 0)
            interpretation = scores.get('interpretation', 'Unable to calculate')
            
            st.metric("🎯 Total Score", f"{total_score}/31" if age_tag == "6yrs" else f"{total_score}/29")
            st.write(max_score_text)
            st.write(f"**Interpretation:** {interpretation}")
            
            # Additional details
            if student_name:
                st.write(f"**Student:** {student_name}")
            st.write(f"**Age Group:** {age_group}")
            st.write(f"**Test:** Right Leg Eyes Open")
        
        # Additional analysis section
        if df_front is not None or df_side is not None:
            st.divider()
            st.subheader("📈 Additional Analysis")
            
            tab1, tab2, tab3 = st.tabs(["Strategy & Events", "Joint Angles", "Foot Drift"])
            
            with tab1:
                col1, col2 = st.columns(2)
                
                if results_front:
                    with col1:
                        st.write("**Front View Events:**")
                        st.write(f"- Strategy: {results_front.get('strategy', 'N/A')}")
                        st.write(f"- Foot Touches: {results_front.get('foot_touches_ankle', 0)}")
                        st.write(f"- Toe Touches: {results_front.get('toe_touches', 0)}")
                        st.write(f"- Hands Off: {results_front.get('hands_off_cnt', 0)} ({results_front.get('hands_off_pct', 0)*100:.1f}%)")
                
                if results_side:
                    with col2:
                        st.write("**Side View Events:**")
                        st.write(f"- Strategy: {results_side.get('strategy', 'N/A')}")
                        st.write(f"- Foot Touches: {results_side.get('foot_touches_ankle', 0)}")
                        st.write(f"- Toe Touches: {results_side.get('toe_touches', 0)}")
                        st.write(f"- Hands Off: {results_side.get('hands_off_cnt', 0)} ({results_side.get('hands_off_pct', 0)*100:.1f}%)")
            
            with tab2:
                col1, col2 = st.columns(2)
                
                if results_front:
                    with col1:
                        st.write("**Front View Joint Angles (deg):**")
                        st.write(f"- Trunk: {results_front.get('trunk_mean_deg', 0):.1f}")
                        st.write(f"- Left Hip: {results_front.get('hip_L_mean_deg', 0):.1f}")
                        st.write(f"- Right Hip: {results_front.get('hip_R_mean_deg', 0):.1f}")
                        st.write(f"- Left Knee: {results_front.get('knee_L_mean_deg', 0):.1f}")
                        st.write(f"- Right Knee: {results_front.get('knee_R_mean_deg', 0):.1f}")
                
                if results_side:
                    with col2:
                        st.write("**Side View Joint Angles (deg):**")
                        st.write(f"- Trunk: {results_side.get('trunk_mean_deg', 0):.1f}")
                        st.write(f"- Left Hip: {results_side.get('hip_L_mean_deg', 0):.1f}")
                        st.write(f"- Right Hip: {results_side.get('hip_R_mean_deg', 0):.1f}")
                        st.write(f"- Left Knee: {results_side.get('knee_L_mean_deg', 0):.1f}")
                        st.write(f"- Right Knee: {results_side.get('knee_R_mean_deg', 0):.1f}")
            
            with tab3:
                col1, col2 = st.columns(2)
                
                if results_front:
                    with col1:
                        st.write("**Front View Foot Drift:**")
                        if results_front.get('drift_max_cm') is not None:
                            st.write(f"- Max Drift: {results_front.get('drift_max_cm', 0):.1f} cm")
                            st.write(f"- Mean Drift: {results_front.get('drift_mean_cm', 0):.1f} cm")
                        st.write(f"- Max (pelvis-norm): {results_front.get('drift_pelvis_max', 0):.2f}")
                
                if results_side:
                    with col2:
                        st.write("**Side View Foot Drift:**")
                        if results_side.get('drift_max_cm') is not None:
                            st.write(f"- Max Drift: {results_side.get('drift_max_cm', 0):.1f} cm")
                            st.write(f"- Mean Drift: {results_side.get('drift_mean_cm', 0):.1f} cm")
                        st.write(f"- Max (pelvis-norm): {results_side.get('drift_pelvis_max', 0):.2f}")
        
        st.success("🎉 Right Leg Eyes Open balance assessment completed!")

if __name__ == "__main__":
    main()
