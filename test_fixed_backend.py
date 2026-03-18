#!/usr/bin/env python3
"""
Test the fixed backend with proper imports
"""

import os
import sys

def test_backend_fixed():
    """Test that the backend imports work with fixed processors"""
    
    # Change to the backend directory
    backend_dir = r"c:\Users\anish\OneDrive\Desktop\bio med\Sensory-Flow\backend"
    os.chdir(backend_dir)
    
    # Add to path
    sys.path.insert(0, backend_dir)
    
    print(f"Testing from: {backend_dir}")
    print(f"Python path: {sys.path[0]}")
    
    try:
        # Test processor imports
        print("\nTesting processor imports...")
        from processors.jumping_jacks_fixed import process_jumping_jacks
        print("✓ jumping_jacks_fixed")
        
        from processors.one_leg_standing_fixed import process_one_leg_standing
        print("✓ one_leg_standing_fixed")
        
        from processors.tandem_walking_fixed import process_tandem_walking
        print("✓ tandem_walking_fixed")
        
        # Test scoring imports
        print("\nTesting scoring imports...")
        from scoring import score_jumping_jacks, score_ols, score_tandem_walking
        print("✓ scoring wrappers")
        
        # Test main import
        print("\nTesting main backend...")
        from main import app, EXERCISE_ID_TO_ASSESSMENT_KEY
        print("✓ FastAPI app")
        print(f"✓ Available exercises: {list(EXERCISE_ID_TO_ASSESSMENT_KEY.keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_actual_video():
    """Test with an actual video file (converted to MP4)"""
    
    print("\n" + "="*50)
    print("TESTING WITH ACTUAL VIDEO")  
    print("="*50)
    
    # Find an MP4 video file  
    exercise_root = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise"
    test_video = None
    
    for root, dirs, files in os.walk(exercise_root):
        for file in files:
            if file.lower().endswith('.mp4'):
                test_video = os.path.join(root, file)
                break
        if test_video:
            break
    
    if not test_video:
        print("No MP4 videos found. Need to convert MOV files first.")
        return False
    
    print(f"Testing with: {test_video}")
    
    # Change back to backend directory
    backend_dir = r"c:\Users\anish\OneDrive\Desktop\bio med\Sensory-Flow\backend"
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)
    
    try:
        # Test jumping jacks if it's a front view video
        if "Front" in test_video or "front" in test_video.lower():
            print("Testing jumping jacks processor...")
            from processors.jumping_jacks_fixed import process_jumping_jacks
            
            result = process_jumping_jacks(test_video, age_years=6)
            print(f"✓ Process completed!")
            print(f"  Total score: {result.get('totalScore', 'N/A')}")
            print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
            return True
        
        # Test OLS if we can find front/side pair
        elif "Side" in test_video:
            # Look for corresponding front video
            front_video = test_video.replace("Side", "Front").replace(".mp4", ".MOV")
            if not os.path.exists(front_video):
                front_video = test_video.replace("Side", "Front")
            
            if os.path.exists(front_video):
                print("Testing OLS processor...")
                from processors.one_leg_standing_fixed import process_one_leg_standing
                
                result = process_one_leg_standing(front_video, test_video, 6, False, "L")
                print(f"✓ Process completed!")
                print(f"  Total score: {result.get('totalScore', 'N/A')}")
                print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
                return True
        
        print("Could not determine exercise type from video path")
        return False
        
    except Exception as e:
        print(f"✗ Video processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def convert_sample_mov():
    """Convert one MOV file to MP4 for testing"""
    
    print("\n" + "="*50)
    print("CONVERTING SAMPLE MOV TO MP4")
    print("="*50)
    
    import subprocess
    import shutil
    
    # Check ffmpeg
    if not shutil.which("ffmpeg"):
        print("ffmpeg not available - cannot convert videos")
        return False
    
    # Find first MOV file
    exercise_root = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise" 
    sample_mov = None
    
    for root, dirs, files in os.walk(exercise_root):
        for file in files:
            if file.lower().endswith('.mov'):
                sample_mov = os.path.join(root, file)
                break
        if sample_mov:
            break
    
    if not sample_mov:
        print("No MOV files found")
        return False
    
    print(f"Converting: {sample_mov}")
    
    # Generate MP4 path
    mp4_path = sample_mov.rsplit('.', 1)[0] + "_converted.mp4"
    
    if os.path.exists(mp4_path):
        print(f"Already converted: {mp4_path}")
        return True
    
    try:
        cmd = [
            'ffmpeg', '-i', sample_mov,
            '-c:v', 'libx264', '-c:a', 'aac', 
            '-preset', 'fast', '-y', mp4_path
        ]
        
        print("Running ffmpeg conversion...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(mp4_path):
            print(f"✓ Converted successfully: {mp4_path}")
            return True
        else:
            print(f"✗ Conversion failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error during conversion: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("TESTING FIXED BACKEND PROCESSORS")
    print("="*60)
    
    success_count = 0
    
    # Test 1: Backend imports
    print("1. Testing backend imports...")
    if test_backend_fixed():
        print("✅ Backend imports working!")
        success_count += 1
    else:
        print("❌ Backend import issues remain")
    
    # Test 2: Convert a sample video
    print("\n2. Converting sample video...")
    if convert_sample_mov():
        print("✅ Video conversion working!")
        success_count += 1
    else:
        print("❌ Video conversion failed")
    
    # Test 3: Test with actual video
    print("\n3. Testing with actual video...")
    if test_with_actual_video():
        print("✅ Video processing working!")
        success_count += 1
    else:
        print("❌ Video processing issues")
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    if success_count >= 2:
        print("🎉 Backend is ready! Your fixed processors are working.")
        print("\nNext steps:")
        print("1. Start the backend: cd Sensory-Flow/backend && python main.py")
        print("2. Test the API endpoints with your video data")
        print("3. Convert remaining MOV files: python convert_videos.py")
    else:
        print("⚠️ Still have issues to resolve.")
        print("Check the error messages above.")

if __name__ == "__main__":
    main()