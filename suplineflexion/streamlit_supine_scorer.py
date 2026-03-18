#!/usr/bin/env python3
"""
Streamlit Supine Flexion Assessment & Scoring App
Based on supine.py preprocessing and math_supine_flexion.py scoring
"""

import streamlit as st
import pandas as pd
import numpy as np
import cv2
import os
import tempfile
import importlib.util
from io import BytesIO

# Import scoring functions from local math_supine_flexion.py file
import sys
import os

# Load the local math_supine_flexion.py file explicitly
math_file_path = os.path.join(os.path.dirname(__file__), 'math_supine_flexion.py')
spec = importlib.util.spec_from_file_location("supine_scoring_math", math_file_path)
supine_scoring_math = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supine_scoring_math)

# Extract the functions we need for both age groups
# 6-year functions
score_neck_flex_6y = supine_scoring_math.score_neck_flex_6y
score_trunk_flex_6y = supine_scoring_math.score_trunk_flex_6y
score_hip_flex_6y = supine_scoring_math.score_hip_flex_6y
score_knee_flex_6y = supine_scoring_math.score_knee_flex_6y
score_hold_6y = supine_scoring_math.score_hold_6y
score_row_supine_6y = supine_scoring_math.score_row_supine_6y

# 7-year functions
score_neck_flex_7y = supine_scoring_math.score_neck_flex_7y
score_trunk_flex_7y = supine_scoring_math.score_trunk_flex_7y
score_hip_flex_7y = supine_scoring_math.score_hip_flex_7y
score_knee_flex_7y = supine_scoring_math.score_knee_flex_7y
score_hold_7y = supine_scoring_math.score_hold_7y
score_row_supine_7y = supine_scoring_math.score_row_supine_7y

# Unified scoring function
score_row_supine = supine_scoring_math.score_row_supine

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

# Landmark indices (same as supine flexion)
LM = dict(
    NOSE=0, L_EYE=1, R_EYE=2, L_EAR=7, R_EAR=8,
    L_SH=11, R_SH=12, L_EL=13, R_EL=14, L_WR=15, R_WR=16,
    L_HP=23, R_HP=24, L_KN=25, R_KN=26, L_AN=27, R_AN=28
)

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

def angle_between(u, v, eps=1e-8):
    """Angle between two vectors."""
    nu = np.linalg.norm(u)
    nv = np.linalg.norm(v)
    if nu < eps or nv < eps:
        return np.nan
    return float(np.degrees(np.arccos(np.clip(np.dot(u, v)/(nu*nv), -1.0, 1.0))))

def pelvis_width_xy(P2):
    """Pelvis width in pixels."""
    d = np.linalg.norm(P2[LM['L_HP']] - P2[LM['R_HP']])
    return float(d) if d > 1e-8 else np.nan

def estimate_floor_y(P2, H=None):
    """Estimate floor Y coordinate."""
    ylist = [P2[LM['L_AN'],1], P2[LM['R_AN'],1]]
    if P2.shape[0] >= 33:
        # 29,30 heels; 31,32 big toes (MediaPipe)
        for idx in (29,30,31,32):
            if idx < P2.shape[0]:
                ylist.append(P2[idx,1])
    y = np.array(ylist, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H*0.98) if H is not None else np.nan
    return float(np.percentile(y, 95))

def rolling_median(x, k=5):
    """Rolling median filter."""
    s = pd.Series(x, dtype=float)
    return s.rolling(k, center=True, min_periods=1).median().to_numpy()

def central_mask(n_frames, fps, trim_sec=2.0):
    """Create mask for central portion of video (excluding start/end)."""
    if not fps or fps <= 0:
        fps = 30.0
    s = int(round(trim_sec*fps))
    lo, hi = s, max(s, n_frames - s)
    m = np.zeros(n_frames, dtype=bool)
    m[lo:hi] = True
    return m

def chin_tuck_mask(df, fps, neck_thr_deg=12.0, nose_drop_frac=0.08):
    """Detect chin tuck: neck flex >= threshold AND nose-shoulder distance drops."""
    def _baseline(x, n=12):
        x = pd.Series(x, dtype=float)
        return float(x.iloc[:max(3, n)].median(skipna=True))
    
    base_nose = _baseline(df["nose_sh_dist"], n=12)
    drop_ok = (base_nose - df["nose_sh_dist"]) >= (nose_drop_frac * base_nose)
    return (df["neck_flex"] >= neck_thr_deg) & drop_ok

def measure_supine_flexion_video(video_path, smooth_k=5, model_complexity=1, progress_bar=None):
    """
    Full supine flexion per-frame measurement (based on supine.py).
    Returns DataFrame with all kinematic parameters.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or not (10 < fps < 120): 
        fps = 30.0
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    rows = []
    frame_idx = 0
    
    with mp.solutions.pose.Pose(
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
                # Fill with NaN row
                rows.append([np.nan] * 12)
                frame_idx += 1
                continue
                
            # 2D + world landmarks
            P2 = np.array([[lm.x*W, lm.y*H] for lm in res.pose_landmarks.landmark], dtype=float)
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.zeros((33, 3), dtype=float)  # fallback
            
            # Centroids (2D & 3D)
            sh2 = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
            hp2 = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
            sh3 = (P3[LM['L_SH']] + P3[LM['R_SH']]) / 2.0
            hp3 = (P3[LM['L_HP']] + P3[LM['R_HP']]) / 2.0
            
            # Choose head landmark (avg ears else nose)
            if np.isfinite(P3[LM['L_EAR']]).all() and np.isfinite(P3[LM['R_EAR']]).all():
                head3 = (P3[LM['L_EAR']] + P3[LM['R_EAR']]) / 2.0
            else:
                head3 = P3[LM['NOSE']]
                
            head2 = (P2[LM['L_EAR']] + P2[LM['R_EAR']]) / 2.0 if np.isfinite(P2[LM['L_EAR']]).all() and np.isfinite(P2[LM['R_EAR']]).all() \
                    else P2[LM['NOSE']]
            
            # ---- Angles ----
            # Neck flexion: relative (Head–Shoulder vs. Shoulder–MidHip) in 2D (camera-tilt robust)
            neck_flex = min(angle_between(sh2 - hp2, head2 - sh2), 90.0) if not np.isnan(angle_between(sh2 - hp2, head2 - sh2)) else np.nan
            
            # Trunk flexion (shoulder vertex): 180° - ∠(Head, Shoulder, MidHip) in 3D
            tf_int = angle_3pt(head3, sh3, hp3)   # internal angle at the shoulder
            trunk_flex = max(0.0, 180.0 - tf_int) if np.isfinite(tf_int) else np.nan # grows as the child curls
            
            # Hip/Knee flexion (3-point, world)
            hip_R = max(0.0, 180.0 - angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])) if np.isfinite(angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']])) else np.nan
            hip_L = max(0.0, 180.0 - angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])) if np.isfinite(angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']])) else np.nan
            knee_R = max(0.0, 180.0 - angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])) if np.isfinite(angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']])) else np.nan
            knee_L = max(0.0, 180.0 - angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])) if np.isfinite(angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']])) else np.nan
            
            # Floor + normalization (2D)
            y_floor = estimate_floor_y(P2, H=H)
            px_scale = pelvis_width_xy(P2) or np.nan
            sh_h = (y_floor - float(sh2[1])) / px_scale if np.isfinite(px_scale) else np.nan
            sh_h = max(sh_h, 0.0) if np.isfinite(sh_h) else np.nan
            
            # Chin-tuck proxy
            ns_dist = np.linalg.norm((P2[LM['NOSE']] if np.isfinite(P2[LM['NOSE']]).all() else head2) - sh2) / px_scale if np.isfinite(px_scale) else np.nan
            
            # Timing proxies (raw)
            sh_y = float(sh2[1])
            wr_min_y = float(min(P2[LM['L_WR'],1], P2[LM['R_WR'],1]))
            
            rows.append([neck_flex, trunk_flex, hip_R, hip_L, knee_R, knee_L,
                         sh_h, ns_dist, y_floor, px_scale, sh_y, wr_min_y])
            
            frame_idx += 1
    
    cap.release()
    
    cols = ["neck_flex","trunk_flex","hip_R","hip_L","knee_R","knee_L",
            "shoulder_h","nose_sh_dist","y_floor","pelvis_px","sh_y","wr_min_y"]
    df = pd.DataFrame(rows, columns=cols)
    
    # Smooth kinematic series (keep timing proxies raw)
    for k in ["neck_flex","trunk_flex","hip_R","hip_L","knee_R","knee_L","shoulder_h","nose_sh_dist"]:
        df[k] = pd.Series(df[k]).rolling(smooth_k, center=True, min_periods=1).median()
    
    return df, float(fps)

def summarize_supine_clip(df: pd.DataFrame, fps: float, trim_sec=0.0):
    """
    Returns clip-level means and which leg was used for hip/knee averaging.
    Based on supine.py summarize_supine_clip function.
    """
    n = len(df)
    # No trimming by default
    m = central_mask(n, fps, trim_sec=trim_sec)  # trim_sec=0 → all frames
    
    if df is None or len(df) == 0 or not m.any():
        return dict(
            neck_mean_deg=np.nan,
            trunk_mean_deg=np.nan,
            hip_mean_deg=np.nan,
            knee_mean_deg=np.nan,
            shoulder_h_mean_norm=np.nan,
            hold_duration_s=0.0,
            leg_used=None,
            analysis_frames=0,
            total_frames=n,
            chin_tuck_present=False,
            chin_tuck_time_s=0.0
        )
    
    # Choose reporting leg by larger median hip flexion
    medR = float(np.nanmedian(pd.Series(df.loc[m, "hip_R"])))
    medL = float(np.nanmedian(pd.Series(df.loc[m, "hip_L"])))
    leg = "R" if medR >= medL else "L"
    
    # Clip angles to reasonable ranges
    clip = lambda a, lo, hi: np.clip(a.astype(float), lo, hi)
    
    summary = dict(
        neck_mean_deg=float(np.nanmean(clip(df.loc[m,"neck_flex"].to_numpy(), 0, 45))),
        trunk_mean_deg=float(np.nanmean(clip(df.loc[m,"trunk_flex"].to_numpy(), 0, 80))),
        hip_mean_deg=float(np.nanmean(clip(df.loc[m,f"hip_{leg}"].to_numpy(), 0, 120))),
        knee_mean_deg=float(np.nanmean(clip(df.loc[m,f"knee_{leg}"].to_numpy(), 0, 135))),
        shoulder_h_mean_norm=float(np.nanmean(df.loc[m,"shoulder_h"])),
        leg_used=leg,
        analysis_frames=int(m.sum()),
        total_frames=n,
        hold_duration_s=float(n/(fps if fps else 30.0))
    )
    
    # Chin-tuck analysis
    ct_mask = chin_tuck_mask(df, fps)
    summary["chin_tuck_present"] = bool(ct_mask[m].any())
    summary["chin_tuck_time_s"] = float(ct_mask[m].sum() / (fps if fps else 30.0))
    
    return summary

def main():
    st.set_page_config(page_title="Supine Flexion Scorer", layout="wide")
    
    st.title("🏃 Supine Flexion Assessment & Scoring")
    st.markdown("Upload video to get automated supine flexion scores using age-appropriate rubrics (6-year or 7-year).")
    
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
            st.info("📊 **6 Years Scoring**: Max Score = 35 points (Neck: 6, Trunk: 8, Hip: 7, Knee: 6, Hold Duration: 8)")
        else:
            st.info("📊 **7 Years Scoring**: Max Score = 34 points (Neck: 6, Trunk: 8, Hip: 6, Knee: 6, Hold Duration: 8)")
    
    st.subheader("📹 Supine Flexion Video")
    video_file = st.file_uploader(
        "Upload Supine Flexion Video",
        type=["mp4", "mov", "avi", "mkv"],
        help="Upload a video showing the student performing supine flexion exercise"
    )
    
    st.divider()
    
    if st.button("🚀 Process Video & Calculate Scores", type="primary", use_container_width=True, disabled=not age_selected):
        
        if not video_file:
            st.error("❌ Please upload a video file to process.")
            st.stop()
        
        if not age_selected:
            st.error("❌ Please select an age group before processing.")
            st.stop()
        
        # Display selected scoring system
        st.success(f"✅ Using {age_group} scoring rubric for supine flexion assessment")
        
        # Process Video
        with st.spinner("🎥 Processing video..."):
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(video_file.read())
                tmp_path = tmp_file.name
            
            try:
                # Add progress bar
                progress_bar = st.progress(0)
                st.text("📊 Analyzing pose landmarks and calculating angles...")
                
                # Process the video
                df, fps = measure_supine_flexion_video(
                    tmp_path, 
                    smooth_k=5, 
                    model_complexity=1,
                    progress_bar=progress_bar
                )
                
                progress_bar.progress(1.0)
                st.success("✅ Video processing complete!")
                
                if df is None or len(df) == 0:
                    st.error("❌ Could not extract pose data from video. Please ensure the video shows a person clearly.")
                    os.unlink(tmp_path)
                    st.stop()
                
                # Get summary statistics
                summary = summarize_supine_clip(df, fps, trim_sec=0.0)
                
                st.subheader(f"📊 {age_group} Rubric - Calculated Parameters & Scores")
                
                # Score using age-appropriate functions
                scores = score_row_supine(summary, age_years)
                
                # Display results in a clean table
                results_data = [
                    {
                        "Parameter": "Neck Flexion",
                        "Raw Value": f"{summary['neck_mean_deg']:.2f}°" if np.isfinite(summary['neck_mean_deg']) else "N/A",
                        "Score": scores.get("neck_flex_score", "N/A"),
                        "Description": "Average neck flexion angle during hold"
                    },
                    {
                        "Parameter": "Trunk Flexion", 
                        "Raw Value": f"{summary['trunk_mean_deg']:.2f}°" if np.isfinite(summary['trunk_mean_deg']) else "N/A",
                        "Score": scores.get("trunk_flex_score", "N/A"),
                        "Description": "Average trunk flexion angle during hold"
                    },
                    {
                        "Parameter": "Hip Flexion",
                        "Raw Value": f"{summary['hip_mean_deg']:.2f}°" if np.isfinite(summary['hip_mean_deg']) else "N/A",
                        "Score": scores.get("hip_flex_score", "N/A"),
                        "Description": f"Average hip flexion angle (leg {summary['leg_used']})"
                    },
                    {
                        "Parameter": "Knee Flexion",
                        "Raw Value": f"{summary['knee_mean_deg']:.2f}°" if np.isfinite(summary['knee_mean_deg']) else "N/A",
                        "Score": scores.get("knee_flex_score", "N/A"),
                        "Description": f"Average knee flexion angle (leg {summary['leg_used']})"
                    },
                    {
                        "Parameter": "Hold Duration",
                        "Raw Value": f"{summary['hold_duration_s']:.2f}s" if np.isfinite(summary['hold_duration_s']) else "N/A",
                        "Score": scores.get("hold_duration_score", "N/A"),
                        "Description": "Total hold duration in seconds"
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
                max_score = scores.get("max_score", 35 if age_years == 6 else 34)
                
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
                    st.write("**Performance Summary:**")
                    st.write(f"• Analysis duration: {summary['hold_duration_s']:.2f} seconds")
                    st.write(f"• Primary leg used: {summary['leg_used']}")
                    st.write(f"• Video frame rate: {fps:.1f} FPS")
                    st.write(f"• Total frames analyzed: {len(df)}")
                    st.write(f"• Analysis frames used: {summary['analysis_frames']}")
                
                with col_right:
                    st.write("**Additional Features:**")
                    st.write(f"• Chin tuck detected: {'✅ Yes' if summary['chin_tuck_present'] else '❌ No'}")
                    if summary['chin_tuck_present']:
                        st.write(f"• Chin tuck duration: {summary['chin_tuck_time_s']:.2f}s")
                    st.write(f"• Shoulder height (normalized): {summary['shoulder_h_mean_norm']:.3f}")
                
                # Advanced metrics
                with st.expander("🔍 Advanced Flexion Analysis"):
                    st.write("**Per-side angle measurements:**")
                    st.write(f"• Right hip flexion mean: {np.nanmean(df['hip_R']):.2f}°")
                    st.write(f"• Left hip flexion mean: {np.nanmean(df['hip_L']):.2f}°")
                    st.write(f"• Right knee flexion mean: {np.nanmean(df['knee_R']):.2f}°")
                    st.write(f"• Left knee flexion mean: {np.nanmean(df['knee_L']):.2f}°")
                    
                    st.write("**Range of motion:**")
                    st.write(f"• Neck flexion range: {np.nanmin(df['neck_flex']):.1f}° - {np.nanmax(df['neck_flex']):.1f}°")
                    st.write(f"• Trunk flexion range: {np.nanmin(df['trunk_flex']):.1f}° - {np.nanmax(df['trunk_flex']):.1f}°")
                    
                    # Chin tuck timing
                    if 'chin_tuck_present' in summary and summary['chin_tuck_present']:
                        ct_mask = chin_tuck_mask(df, fps)
                        first_tuck = np.where(ct_mask)[0]
                        if len(first_tuck) > 0:
                            st.write(f"• First chin tuck at: {first_tuck[0]/fps:.2f}s")
                
                # Download results as CSV
                st.divider()
                
                # Combine all results for export
                export_data = {
                    "Student": student_name or "Unknown",
                    "Age Group": age_group,
                    **summary,
                    **scores,
                }
                
                export_df = pd.DataFrame([export_data])
                csv_data = export_df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Complete Results as CSV",
                    data=csv_data,
                    file_name=f"supine_flexion_results_{student_name if student_name else 'student'}.csv",
                    mime="text/csv"
                )
                
                # Show frame-by-frame data
                with st.expander("📈 View Frame-by-Frame Data"):
                    st.write("**Per-frame measurements:**")
                    display_df = df.copy()
                    display_df.index.name = "Frame"
                    st.dataframe(display_df, use_container_width=True)
                    
                    # Download frame data
                    frame_csv = display_df.to_csv()
                    st.download_button(
                        label="📥 Download Frame-by-Frame Data",
                        data=frame_csv,
                        file_name=f"supine_flexion_frames_{student_name if student_name else 'student'}.csv",
                        mime="text/csv"
                    )
            
            except Exception as e:
                st.error(f"❌ Error processing video: {str(e)}")
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

if __name__ == "__main__":
    main()