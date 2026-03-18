"""
Mock processors for testing backend API without MediaPipe
These return realistic but fake metrics to test the scoring and API flow
"""

import os
import cv2
from typing import Dict, Any, Optional

def mock_get_video_info(video_path: str) -> Dict[str, Any]:
    """Get basic video info without MediaPipe"""
    if not os.path.exists(video_path):
        return {"error": "Video file not found", "fps": 30.0}
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": "Cannot open video", "fps": 30.0}
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        cap.release()
        
        return {
            "frame_count": frame_count,
            "fps": fps if fps > 0 else 30.0,
            "width": width,
            "height": height,
            "duration_s": frame_count / fps if fps > 0 else 0,
            "readable": True
        }
    except Exception as e:
        return {"error": str(e), "fps": 30.0}

def mock_process_jumping_jacks(video_path: Optional[str], age_years: int) -> Dict[str, Any]:
    """Mock jumping jacks processor"""
    
    if not video_path or not os.path.exists(video_path):
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 35,
            "interpretation": "Error: No video provided"
        }
    
    video_info = mock_get_video_info(video_path)
    if "error" in video_info:
        return {
            "rawMetrics": video_info, "scores": {},
            "totalScore": 0, "maxScore": 35,
            "interpretation": f"Error: {video_info['error']}"
        }
    
    # Generate realistic mock metrics
    raw_metrics = {
        "valid_reps_total_jumps": 8,
        "jump_count": 8,
        "partial_reps": 0,
        "shoulder_abduction_angle_mean_deg": 145.2,
        "shoulder_abduction_angle_max_deg": 165.8,
        "hip_abduction_distance_mean_norm": 1.2,
        "hip_abduction_distance_max_norm": 1.8,
        "hip_upward_displacement_mean_norm": 0.15,
        "hip_upward_displacement_max_norm": 0.25,
        "arm_leg_open_sync_mean_s": 0.08,
        "arm_leg_close_sync_mean_s": 0.12,
        "duration_s": video_info["duration_s"],
        "fps": video_info["fps"],
    }
    
    # Use real scoring
    try:
        from scoring import score_jumping_jacks
        score_result = score_jumping_jacks(raw_metrics, age_years=age_years)
    except Exception as e:
        # Fallback mock scoring
        score_result = {
            "shoulder_abduction_score": 6,
            "hip_abduction_score": 7,
            "jump_score": 6,
            "sync_open_score": 5,
            "sync_close_score": 4,
            "total_score": 28,
            "interpretation": f"Good performance (mock) - Age {age_years}"
        }
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": score_result.get("total_score", 28),
        "maxScore": 35,
        "interpretation": score_result.get("interpretation", f"Good performance - Age {age_years}")
    }

def mock_process_one_leg_standing(front_video_path: Optional[str], side_video_path: Optional[str],
                                 age_years: int, eyes_open: bool = True, raised_leg: str = "L") -> Dict[str, Any]:
    """Mock one-leg standing processor"""
    
    if not front_video_path and not side_video_path:
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": "Error: No videos provided"
        }
    
    # Check videos exist
    errors = []
    if front_video_path and not os.path.exists(front_video_path):
        errors.append("Front video not found")
    if side_video_path and not os.path.exists(side_video_path):
        errors.append("Side video not found")
    
    if errors:
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 34,
            "interpretation": f"Error: {'; '.join(errors)}"
        }
    
    # Generate realistic mock metrics
    raw_metrics = {
        "sway_SS_mean": 2.1 if eyes_open else 4.3,
        "sway_SS_SD": 1.8 if eyes_open else 3.2,
        "sway_AP_mean": 1.9 if eyes_open else 3.8,
        "sway_AP_SD": 1.6 if eyes_open else 2.9,
        "drift_max_cm": 3.2,
        "drift_mean_cm": 1.8,
        "neck_mean_deg": 12.5,
        "neck_sd_deg": 8.2,
        "toe_touches": 0 if eyes_open else 2,
        "foot_touches": 0 if eyes_open else 1,
        "hands_off_cnt": 0,
        "hands_off_pct": 0.0,
        "balance_strategy": "ankle" if eyes_open else "hip",
        "fps": 30.0,
    }
    
    # Use real scoring
    try:
        from scoring import score_ols
        score_result = score_ols(raw_metrics, age_years=age_years, eyes_open=eyes_open, raised_leg=raised_leg)
    except Exception as e:
        # Fallback mock scoring
        base_score = 25 if eyes_open else 20
        score_result = {
            "sway_score": base_score // 4,
            "stability_score": base_score // 4,
            "strategy_score": base_score // 4,
            "total_score": base_score,
            "interpretation": f"{'Good' if eyes_open else 'Fair'} balance (mock) - Age {age_years}"
        }
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": score_result.get("total_score", base_score),
        "maxScore": 34,
        "interpretation": score_result.get("interpretation", f"Balance performance - Age {age_years}"),
        "eyesOpen": eyes_open,
        "raisedLeg": raised_leg,
    }

def mock_process_tandem_walking(front_video_path: Optional[str], side_video_path: Optional[str], 
                               age_years: int, eyes_open: bool = True) -> Dict[str, Any]:
    """Mock tandem walking processor"""
    
    if not front_video_path and not side_video_path:
        return {
            "rawMetrics": {}, "scores": {},
            "totalScore": 0, "maxScore": 28,
            "interpretation": "Error: No videos provided"
        }
    
    # Generate realistic mock metrics
    raw_metrics = {
        "steps_total": 10,
        "steps_valid": 8 if eyes_open else 6,
        "step_gap_cm_mean": 2.1 if eyes_open else 4.5,
        "step_gap_cm_max": 3.8 if eyes_open else 8.2,
        "sway_ML_mean_cm": 1.2 if eyes_open else 2.8,
        "sway_ML_SD_cm": 0.8 if eyes_open else 1.9,
        "sway_AP_mean_cm": 1.0 if eyes_open else 2.1,
        "sway_AP_SD_cm": 0.6 if eyes_open else 1.5,
        "step_time_mean_s": 0.95,
        "step_time_SD_s": 0.15,
        "arms_up_cnt": 0 if eyes_open else 2,
        "arms_out_cnt": 1 if eyes_open else 3,
        "wall_touch_cnt": 0 if eyes_open else 1,
        "fps": 30.0,
    }
    
    # Use real scoring
    try:
        from scoring import score_tandem_walking
        score_result = score_tandem_walking(raw_metrics, age_years=age_years, eyes_open=eyes_open)
    except Exception as e:
        # Fallback mock scoring
        base_score = 22 if eyes_open else 18
        score_result = {
            "steps_score": base_score // 4,
            "gap_score": base_score // 4,
            "sway_score": base_score // 4,
            "stability_score": base_score // 4,
            "total_score": base_score,
            "interpretation": f"{'Good' if eyes_open else 'Fair'} tandem walking (mock) - Age {age_years}"
        }
    
    return {
        "rawMetrics": raw_metrics,
        "scores": {k: v for k, v in score_result.items() if "_score" in k},
        "totalScore": score_result.get("total_score", base_score),
        "maxScore": 28,
        "interpretation": score_result.get("interpretation", f"Tandem walking performance - Age {age_years}"),
        "eyesOpen": eyes_open,
    }

if __name__ == "__main__":
    # Test the mock processors
    print("Testing mock processors...")
    
    # Find a test video
    exercise_root = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise"
    test_video = None
    
    for root, dirs, files in os.walk(exercise_root):
        for file in files:
            if file.lower().endswith(('.mp4', '.mov')):
                test_video = os.path.join(root, file)
                break
        if test_video:
            break
    
    if test_video:
        print(f"Testing with: {test_video}")
        
        print("\n--- Mock Jumping Jacks ---")
        result = mock_process_jumping_jacks(test_video, 6)
        print(f"Total Score: {result['totalScore']}")
        print(f"Interpretation: {result['interpretation']}")
        
        print("\n--- Mock OLS ---")
        result = mock_process_one_leg_standing(test_video, test_video, 6, False, "L")
        print(f"Total Score: {result['totalScore']}")  
        print(f"Interpretation: {result['interpretation']}")
        
        print("\n--- Mock Tandem ---")
        result = mock_process_tandem_walking(test_video, test_video, 6, False)
        print(f"Total Score: {result['totalScore']}")
        print(f"Interpretation: {result['interpretation']}")
        
    else:
        print("No test videos found")