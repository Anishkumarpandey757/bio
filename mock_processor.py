
def mock_process_exercise(video_path, age_years, exercise_type="jumping_jacks"):
    """Mock processor that returns dummy scores for testing"""
    
    import cv2
    import os
    
    if not os.path.exists(video_path):
        return {
            "rawMetrics": {},
            "scores": {},
            "totalScore": 0,
            "maxScore": 35,
            "interpretation": "Error: Video file not found"
        }
    
    # Test basic video reading
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {
            "rawMetrics": {},
            "scores": {},
            "totalScore": 0,
            "maxScore": 35,
            "interpretation": "Error: Cannot open video file"
        }
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    
    # Generate mock metrics based on video properties
    mock_metrics = {
        "frame_count": frame_count,
        "fps": fps,
        "duration_s": frame_count / fps if fps > 0 else 0,
        "video_readable": True
    }
    
    # Mock scoring based on age
    if age_years == 6:
        total_score = 25
        interpretation = "Good performance"
    else:
        total_score = 28
        interpretation = "Very good performance"
    
    return {
        "rawMetrics": mock_metrics,
        "scores": {
            "coordination_score": total_score // 3,
            "balance_score": total_score // 3,
            "timing_score": total_score // 3,
        },
        "totalScore": total_score,
        "maxScore": 35,
        "interpretation": interpretation,
        "ageYears": age_years,
        "exerciseType": exercise_type
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: mock_processor.py <video_path> <age_years> <exercise_type>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    age_years = int(sys.argv[2])
    exercise_type = sys.argv[3]
    
    result = mock_process_exercise(video_path, age_years, exercise_type)
    print(f"Result: {result}")
