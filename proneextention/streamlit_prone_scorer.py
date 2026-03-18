#!/usr/bin/env python3
"""
Streamlit Prone Extension Assessment & Scoring App
Based on prone2_0.py preprocessing and math_prone_extension.py scoring
"""

import streamlit as st
import pandas as pd
import numpy as np
import cv2
import os
import tempfile
import importlib.util
from io import BytesIO

# Import scoring functions from local math_prone_extension.py file
import sys
import os

# Load the local math_prone_extension.py file explicitly
math_file_path = os.path.join(os.path.dirname(__file__), 'math_prone_extension.py')
spec = importlib.util.spec_from_file_location("prone_scoring_math", math_file_path)
prone_scoring_math = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prone_scoring_math)

# Extract the functions we need for both age groups
# 6-year functions
score_neck_ext_6y = prone_scoring_math.score_neck_ext_6y
score_trunk_ext_6y = prone_scoring_math.score_trunk_ext_6y
score_hip_ext_6y = prone_scoring_math.score_hip_ext_6y
score_knee_flex_6y = prone_scoring_math.score_knee_flex_6y
score_hold_6y = prone_scoring_math.score_hold_6y
score_row_prone_6y = prone_scoring_math.score_row_prone_6y

# 7-year functions
score_neck_ext_7y = prone_scoring_math.score_neck_ext_7y
score_trunk_ext_7y = prone_scoring_math.score_trunk_ext_7y
score_hip_ext_7y = prone_scoring_math.score_hip_ext_7y
score_knee_flex_7y = prone_scoring_math.score_knee_flex_7y
score_hold_7y = prone_scoring_math.score_hold_7y
score_row_prone_7y = prone_scoring_math.score_row_prone_7y

# Unified scoring function
score_row_prone = prone_scoring_math.score_row_prone

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

# Landmark indices (same as prone extension)
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
    # add heels and foot indices if available (Pose has 29,30 = heels; 31,32 = big toes)
    if P2.shape[0] >= 33:
        ylist += [P2[29,1], P2[30,1], P2[31,1], P2[32,1]]
    y = np.array(ylist, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float(H*0.98) if H is not None else np.nan  # bottom-of-frame fallback
    return float(np.percentile(y, 95))

def hip_extension_from_internal(a):
    """Convert internal angle to clinical hip extension."""
    if not np.isfinite(a): 
        return np.nan
    return max(0.0, 180.0 - float(a))      # clinical hip extension 0..30

def knee_flexion_from_internal(a):
    """Convert internal angle to clinical knee flexion."""
    if not np.isfinite(a): 
        return np.nan
    return max(0.0, 180.0 - float(a))      # clinical knee flexion 0..13

def rolling_median(x, k=5):
    """Rolling median filter."""
    s = pd.Series(x, dtype=float)
    return s.rolling(k, center=True, min_periods=1).median().to_numpy()

def measure_prone_extension_video(video_path, smooth_k=5, model_complexity=1, progress_bar=None):
    """
    Full prone extension per-frame measurement (based on prone2_0.py).
    Returns DataFrame with all kinematic parameters.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or not (10 < fps < 120): 
        fps = 30.0
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_count))
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
                # Fill with NaN row
                rows.append([np.nan] * 13)
                frame_idx += 1
                continue
                
            # 2D + 3D landmarks
            P2 = np.array([[lm.x*W, lm.y*H] for lm in res.pose_landmarks.landmark], dtype=float)
            if res.pose_world_landmarks:
                P3 = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks.landmark], dtype=float)
            else:
                P3 = np.zeros((33, 3), dtype=float)  # fallback
            
            # Centers
            sh2 = (P2[LM['L_SH']] + P2[LM['R_SH']]) / 2.0
            hp2 = (P2[LM['L_HP']] + P2[LM['R_HP']]) / 2.0
            head2 = (P2[LM['L_EAR']] + P2[LM['R_EAR']]) / 2.0
            
            # Neck angle (relative to trunk)
            neck_rel = angle_between(sh2 - hp2, head2 - sh2)
            neck_deg = min(neck_rel, 90.0) if np.isfinite(neck_rel) else np.nan
            
            # Trunk extension angle
            trunk_deg = max(0.0, 90.0 - angle_to_vertical(hp2, sh2)) if not np.isnan(angle_to_vertical(hp2, sh2)) else np.nan
            
            # Hip extension angles (both sides)
            hip_R = hip_extension_from_internal(angle_3pt(P3[LM['R_SH']], P3[LM['R_HP']], P3[LM['R_KN']]))
            hip_L = hip_extension_from_internal(angle_3pt(P3[LM['L_SH']], P3[LM['L_HP']], P3[LM['L_KN']]))
            
            # Knee flexion angles (both sides)
            knee_R = knee_flexion_from_internal(angle_3pt(P3[LM['R_HP']], P3[LM['R_KN']], P3[LM['R_AN']]))
            knee_L = knee_flexion_from_internal(angle_3pt(P3[LM['L_HP']], P3[LM['L_KN']], P3[LM['L_AN']]))
            
            # Floor estimation and pelvis scale
            y_floor = estimate_floor_y(P2)
            px_scale = pelvis_width_xy(P2) or np.nan
            
            # Thigh height calculations (for distal 1/3 thighs)
            hipR_xy, kneeR_xy = P2[LM['R_HP']], P2[LM['R_KN']]
            hipL_xy, kneeL_xy = P2[LM['L_HP']], P2[LM['L_KN']]
            distalR_xy = hipR_xy + (2.0/3.0)*(kneeR_xy - hipR_xy)
            distalL_xy = hipL_xy + (2.0/3.0)*(kneeL_xy - hipL_xy)
            
            thigh_R = (y_floor - distalR_xy[1]) / px_scale if np.isfinite(px_scale) else np.nan
            thigh_L = (y_floor - distalL_xy[1]) / px_scale if np.isfinite(px_scale) else np.nan
            thigh_R = max(thigh_R, 0.0) if np.isfinite(thigh_R) else np.nan
            thigh_L = max(thigh_L, 0.0) if np.isfinite(thigh_L) else np.nan
            
            # Y-series for timing analysis (UE/LE onset)
            sh_y = float(sh2[1])
            wr_min_y = float(min(P2[LM['L_WR'],1], P2[LM['R_WR'],1]))
            an_min_y = float(min(P2[LM['L_AN'],1], P2[LM['R_AN'],1]))
            
            rows.append([
                neck_deg, trunk_deg, hip_R, hip_L, knee_R, knee_L,
                thigh_R, thigh_L, y_floor, px_scale,
                sh_y, wr_min_y, an_min_y
            ])
            
            frame_idx += 1
    
    cap.release()
    
    cols = ["neck","trunk","hip_R","hip_L","knee_R","knee_L",
            "thigh_R","thigh_L","y_floor","pelvis_px",
            "sh_y","wr_min_y","an_min_y"]
    df = pd.DataFrame(rows, columns=cols)
    
    # Jitter smoothing (angles/distances only)
    for k in ["neck","trunk","hip_R","hip_L","knee_R","knee_L","thigh_R","thigh_L"]:
        df[k] = pd.Series(df[k]).rolling(smooth_k, center=True, min_periods=1).median()
    
    return df, float(fps)

def summarize_prone_clip(df: pd.DataFrame, fps: float):
    """
    Returns clip-level means and which leg was used for hip/knee/thigh averaging.
    Based on prone2_0.py summarize_prone_clip function.
    """
    if df is None or len(df) == 0:
        return dict(
            neck_mean_deg=np.nan,
            trunk_mean_deg=np.nan,
            hip_mean_deg=np.nan,
            knee_mean_deg=np.nan,
            thigh_floor_mean_norm=np.nan,
            hold_duration_s=0.0,
            leg_used=None,
            neck_ok=np.nan, trunk_ok=np.nan, hip_ok=np.nan, knee_ok=np.nan
        )
    
    # Choose the more lifted thigh (median) as the reporting leg
    medR = float(np.nanmedian(df["thigh_R"]))
    medL = float(np.nanmedian(df["thigh_L"]))
    leg = "R" if medR >= medL else "L"
    
    neck_mean = float(np.nanmean(df["neck"]))
    trunk_mean = float(np.nanmean(df["trunk"]))
    hip_mean = float(np.nanmean(df[f"hip_{leg}"]))
    knee_mean = float(np.nanmean(df[f"knee_{leg}"]))
    thigh_mean = float(np.nanmean(df[f"thigh_{leg}"]))
    
    # Simple QA flags (optional)
    knee_ok = (knee_mean <= 15.0) if np.isfinite(knee_mean) else np.nan     # small flexion = straighter knee
    hip_ok = (0.0 <= hip_mean <= 30.0) if np.isfinite(hip_mean) else np.nan
    trunk_ok = (0.0 <= trunk_mean <= 30.0) if np.isfinite(trunk_mean) else np.nan
    neck_ok = (neck_mean <= 45.0) if np.isfinite(neck_mean) else np.nan
    
    return dict(
        neck_mean_deg=neck_mean,
        trunk_mean_deg=trunk_mean,
        hip_mean_deg=hip_mean,
        knee_mean_deg=knee_mean,
        thigh_floor_mean_norm=thigh_mean,
        hold_duration_s=float(len(df) / (fps if fps else 30.0)),
        leg_used=leg,
        neck_ok=neck_ok, trunk_ok=trunk_ok, hip_ok=hip_ok, knee_ok=knee_ok
    )

def main():
    st.set_page_config(page_title="Prone Extension Scorer", layout="wide")
    
    st.title("🏃 Prone Extension Assessment & Scoring")
    st.markdown("Upload video to get automated prone extension scores using age-appropriate rubrics (6-year or 7-year).")
    
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
            st.info("📊 **6 Years Scoring**: Max Score = 36 points (Neck: 5, Trunk: 8, Hip: 6, Knee: 8, Hold Duration: 8)")
        else:
            st.info("📊 **7 Years Scoring**: Max Score = 35 points (Neck: 6, Trunk: 8, Hip: 6, Knee: 7, Hold Duration: 8)")
    
    st.subheader("📹 Prone Extension Video")
    video_file = st.file_uploader(
        "Upload Prone Extension Video",
        type=["mp4", "mov", "avi", "mkv"],
        help="Upload a video showing the student performing prone extension exercise"
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
        st.success(f"✅ Using {age_group} scoring rubric for prone extension assessment")
        
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
                df, fps = measure_prone_extension_video(
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
                summary = summarize_prone_clip(df, fps)
                
                st.subheader(f"📊 {age_group} Rubric - Calculated Parameters & Scores")
                
                # Score using age-appropriate functions
                scores = score_row_prone(summary, age_years)
                
                # Display results in a clean table
                results_data = [
                    {
                        "Parameter": "Neck Extension",
                        "Raw Value": f"{summary['neck_mean_deg']:.2f}°" if np.isfinite(summary['neck_mean_deg']) else "N/A",
                        "Score": scores.get("neck_ext_score", "N/A"),
                        "Description": "Average neck extension angle during hold"
                    },
                    {
                        "Parameter": "Trunk Extension", 
                        "Raw Value": f"{summary['trunk_mean_deg']:.2f}°" if np.isfinite(summary['trunk_mean_deg']) else "N/A",
                        "Score": scores.get("trunk_ext_score", "N/A"),
                        "Description": "Average trunk extension angle during hold"
                    },
                    {
                        "Parameter": "Hip Extension",
                        "Raw Value": f"{summary['hip_mean_deg']:.2f}°" if np.isfinite(summary['hip_mean_deg']) else "N/A",
                        "Score": scores.get("hip_ext_score", "N/A"),
                        "Description": f"Average hip extension angle (leg {summary['leg_used']})"
                    },
                    {
                        "Parameter": "Knee Flexion",
                        "Raw Value": f"{summary['knee_mean_deg']:.2f}°" if np.isfinite(summary['knee_mean_deg']) else "N/A",
                        "Score": scores.get("knee_flex_score", "N/A"),
                        "Description": f"Average knee flexion angle (leg {summary['leg_used']}) - lower is better"
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
                max_score = scores.get("max_score", 36 if age_years == 6 else 35)
                
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
                    st.write("**Quality Checks:**")
                    st.write(f"• Neck angle reasonable: {'✅' if summary['neck_ok'] else '⚠️' if summary['neck_ok'] is not np.nan else '❓'}")
                    st.write(f"• Trunk angle reasonable: {'✅' if summary['trunk_ok'] else '⚠️' if summary['trunk_ok'] is not np.nan else '❓'}")
                    st.write(f"• Hip angle reasonable: {'✅' if summary['hip_ok'] else '⚠️' if summary['hip_ok'] is not np.nan else '❓'}")
                    st.write(f"• Knee angle reasonable: {'✅' if summary['knee_ok'] else '⚠️' if summary['knee_ok'] is not np.nan else '❓'}")
                
                with col_right:
                    st.write("**Performance Summary:**")
                    st.write(f"• Analysis duration: {summary['hold_duration_s']:.2f} seconds")
                    st.write(f"• Primary leg used: {summary['leg_used']}")
                    st.write(f"• Video frame rate: {fps:.1f} FPS")
                    st.write(f"• Total frames analyzed: {len(df)}")
                
                # Thigh lift metrics
                with st.expander("🦵 Thigh Lift Analysis"):
                    st.write("**Normalized thigh height above floor (pelvis-width units):**")
                    st.write(f"• Right thigh mean: {np.nanmean(df['thigh_R']):.3f}")
                    st.write(f"• Left thigh mean: {np.nanmean(df['thigh_L']):.3f}")
                    st.write(f"• Selected leg ({summary['leg_used']}): {summary['thigh_floor_mean_norm']:.3f}")
                    
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
                    file_name=f"prone_extension_results_{student_name if student_name else 'student'}.csv",
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
                        file_name=f"prone_extension_frames_{student_name if student_name else 'student'}.csv",
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