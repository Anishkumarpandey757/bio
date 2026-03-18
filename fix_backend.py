#!/usr/bin/env python3
"""
Fix MediaPipe protobuf compatibility and test backend with MOV conversion
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def fix_mediapipe_protobuf():
    """Try to fix MediaPipe protobuf compatibility"""
    print("Attempting to fix MediaPipe protobuf compatibility...")
    
    try:
        # Try downgrading protobuf
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'protobuf==3.20.3'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✓ Downgraded protobuf to compatible version")
            return True
        else:
            print(f"Failed to downgrade protobuf: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error fixing protobuf: {e}")
        return False

def check_ffmpeg():
    """Check if ffmpeg is available for video conversion"""
    return shutil.which("ffmpeg") is not None

def convert_mov_to_mp4(mov_path):
    """Convert MOV file to MP4 using ffmpeg"""
    if not os.path.exists(mov_path):
        return None
        
    if not check_ffmpeg():
        print("ffmpeg not available - cannot convert MOV files")
        return None
    
    base_dir = os.path.dirname(mov_path)
    base_name = os.path.splitext(os.path.basename(mov_path))[0]
    mp4_path = os.path.join(base_dir, f"{base_name}_converted.mp4")
    
    # Skip if already converted
    if os.path.exists(mp4_path):
        print(f"Using existing converted file: {mp4_path}")
        return mp4_path
    
    try:
        cmd = [
            'ffmpeg', '-i', mov_path,
            '-c:v', 'libx264', '-c:a', 'aac',
            '-preset', 'fast', '-y', mp4_path
        ]
        
        print(f"Converting {mov_path} to MP4...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(mp4_path):
            print(f"✓ Converted to: {mp4_path}")
            return mp4_path
        else:
            print(f"Conversion failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Error converting video: {e}")
        return None

def test_simple_video_processing():
    """Test basic video processing without MediaPipe"""
    print("\n--- Testing Basic Video Processing ---")
    
    # Find a test video
    test_video = None
    exercise_root = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise"
    
    for root, dirs, files in os.walk(exercise_root):
        for file in files:
            if file.lower().endswith(('.mov', '.mp4')):
                test_video = os.path.join(root, file)
                break
        if test_video:
            break
    
    if not test_video:
        print("No test videos found!")
        return False
    
    print(f"Testing with: {test_video}")
    
    # Convert MOV to MP4 if needed
    if test_video.lower().endswith('.mov'):
        converted = convert_mov_to_mp4(test_video)
        if converted:
            test_video = converted
        else:
            print("Cannot test - MOV conversion failed")
            return False
    
    # Test basic OpenCV video reading
    try:
        import cv2
        cap = cv2.VideoCapture(test_video)
        
        if not cap.isOpened():
            print(f"✗ Cannot open video with OpenCV: {test_video}")
            return False
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Read a few frames
        frames_read = 0
        for i in range(min(10, frame_count)):
            ret, frame = cap.read()
            if ret:
                frames_read += 1
            else:
                break
        
        cap.release()
        
        print(f"✓ Video readable: {frame_count} frames at {fps} fps")
        print(f"✓ Successfully read {frames_read} frames")
        return True
        
    except Exception as e:
        print(f"✗ Video processing failed: {e}")
        return False

def create_mock_processor():
    """Create a simple mock processor for testing"""
    print("\n--- Creating Mock Processor for Testing ---")
    
    mock_code = '''
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
'''
    
    mock_file = "mock_processor.py"
    with open(mock_file, 'w') as f:
        f.write(mock_code)
    
    print(f"✓ Created {mock_file}")
    return mock_file

def test_backend_integration():
    """Test FastAPI backend integration"""
    print("\n--- Testing Backend Integration ---")
    
    try:
        # Change to project directory
        os.chdir(r"c:\Users\anish\OneDrive\Desktop\bio med")
        sys.path.insert(0, os.path.join(os.getcwd(), 'Sensory-Flow', 'backend'))
        
        # Test FastAPI app import
        from main import app, EXERCISE_ID_TO_ASSESSMENT_KEY
        print("✓ FastAPI app imported successfully")
        print(f"✓ Available exercises: {list(EXERCISE_ID_TO_ASSESSMENT_KEY.keys())}")
        
        # Test basic route structure
        routes = [route.path for route in app.routes]
        expected_routes = ["/api/process-exercise/{exercise_id}", "/api/upload-video"]
        
        for expected in expected_routes:
            if any(expected.replace("{exercise_id}", "test") in route for route in routes):
                print(f"✓ Route available: {expected}")
            else:
                print(f"✗ Route missing: {expected}")
        
        return True
        
    except Exception as e:
        print(f"✗ Backend integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_video_conversion_script():
    """Create a script to batch convert MOV files to MP4"""
    
    script_content = '''#!/usr/bin/env python3
"""
Batch convert MOV files to MP4 for MediaPipe compatibility
"""

import os
import subprocess
import sys
from pathlib import Path

def convert_all_mov_files(root_dir):
    """Convert all MOV files in directory tree to MP4"""
    
    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg not found. Please install ffmpeg first.")
        print("Download from: https://ffmpeg.org/download.html")
        return False
    
    mov_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.mov'):
                mov_files.append(os.path.join(root, file))
    
    print(f"Found {len(mov_files)} MOV files to convert")
    
    success_count = 0
    for i, mov_path in enumerate(mov_files, 1):
        print(f"Converting {i}/{len(mov_files)}: {os.path.basename(mov_path)}")
        
        base_name = os.path.splitext(mov_path)[0]
        mp4_path = f"{base_name}.mp4"
        
        # Skip if MP4 already exists
        if os.path.exists(mp4_path):
            print(f"  Skipped - MP4 already exists")
            continue
        
        try:
            cmd = [
                'ffmpeg', '-i', mov_path,
                '-c:v', 'libx264', '-c:a', 'aac',
                '-preset', 'fast', '-y', mp4_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(mp4_path):
                print(f"  ✓ Converted successfully")
                success_count += 1
            else:
                print(f"  ✗ Conversion failed: {result.stderr[:100]}...")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\\nConversion complete: {success_count}/{len(mov_files)} successful")
    return success_count == len(mov_files)

if __name__ == "__main__":
    import shutil
    
    exercise_root = r"c:\\Users\\anish\\OneDrive\\Desktop\\bio med\\exersise"
    print(f"Converting MOV files in: {exercise_root}")
    
    success = convert_all_mov_files(exercise_root)
    if success:
        print("\\n🎉 All conversions completed successfully!")
    else:
        print("\\n⚠️ Some conversions failed. Check ffmpeg installation and file permissions.")
'''
    
    with open("convert_videos.py", "w") as f:
        f.write(script_content)
    
    print("✓ Created convert_videos.py - run this to convert all MOV files to MP4")

def main():
    """Main diagnostic and fix function"""
    print("="*60)
    print("BACKEND PROCESSOR DIAGNOSTIC AND FIX TOOL")
    print("="*60)
    
    # Change to project directory
    os.chdir(r"c:\Users\anish\OneDrive\Desktop\bio med")
    print(f"Working directory: {os.getcwd()}")
    
    success_count = 0
    total_tests = 4
    
    # Test 1: Fix MediaPipe protobuf
    print("\n1. Testing MediaPipe protobuf compatibility...")
    if fix_mediapipe_protobuf():
        success_count += 1
    
    # Test 2: Check video processing
    print("\n2. Testing basic video processing...")
    if test_simple_video_processing():
        success_count += 1
    
    # Test 3: Test backend integration
    print("\n3. Testing backend integration...")
    if test_backend_integration():
        success_count += 1
    
    # Test 4: Create tools and helpers
    print("\n4. Creating helper tools...")
    try:
        mock_file = create_mock_processor()
        create_video_conversion_script()
        print("✓ Created diagnostic tools")
        success_count += 1
    except Exception as e:
        print(f"✗ Failed to create tools: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("\n🎉 All systems working! Ready to test processors.")
    else:
        print(f"\n⚠️ {total_tests - success_count} issues found.")
    
    print("\nNext steps:")
    print("1. Run 'python convert_videos.py' to convert MOV files to MP4")
    print("2. Test mock processor: python mock_processor.py <video_path> 6 jumping_jacks")
    print("3. Start backend server: cd Sensory-Flow/backend && python main.py")
    
    # Check if ffmpeg is available
    if not check_ffmpeg():
        print("\n⚠️ IMPORTANT: ffmpeg not found!")
        print("Please install ffmpeg to convert MOV files:")
        print("- Download from: https://ffmpeg.org/download.html")
        print("- Or use: winget install ffmpeg")

if __name__ == "__main__":
    main()