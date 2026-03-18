#!/usr/bin/env python3
"""
Test script to verify all exercise processors work with structured video data
"""

import os
import sys
import traceback
from pathlib import Path

# Add the Sensory-Flow backend to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Sensory-Flow', 'backend'))

# Import processors
try:
    from processors.jumping_jacks_fixed import process_jumping_jacks
    from processors.one_leg_standing_fixed import process_one_leg_standing
    from processors.tandem_walking_fixed import process_tandem_walking
    print("✓ All processors imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

def find_video_files(exercise_root):
    """Find all video files in the exercise folder structure"""
    videos = {}
    
    for age_folder in ['6', '7']:
        age_path = os.path.join(exercise_root, age_folder)
        if not os.path.exists(age_path):
            continue
            
        for participant in os.listdir(age_path):
            participant_path = os.path.join(age_path, participant)
            if not os.path.isdir(participant_path):
                continue
                
            participant_videos = {}
            
            # Check for Front and Side folders
            for view in ['Front', 'Side']:
                view_path = os.path.join(participant_path, view)
                if os.path.exists(view_path):
                    for file in os.listdir(view_path):
                        if file.lower().endswith(('.mp4', '.mov', '.avi')):
                            participant_videos[view.lower()] = os.path.join(view_path, file)
                            break
            
            # Also check for videos directly in participant folder
            for file in os.listdir(participant_path):
                if file.lower().endswith(('.mp4', '.mov', '.avi')):
                    if 'front' not in participant_videos:
                        participant_videos['front'] = os.path.join(participant_path, file)
            
            if participant_videos:
                key = f"age{age_folder}_{participant.replace(' ', '_').replace('.', '')}"
                videos[key] = participant_videos
    
    return videos

def test_jumping_jacks():
    """Test jumping jacks processor"""
    print("\n" + "="*50)
    print("Testing Jumping Jacks Processor")
    print("="*50)
    
    exercise_root = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise\jumping_jacks"
    videos = find_video_files(exercise_root)
    
    print(f"Found videos for {len(videos)} participants:")
    for key, video_dict in videos.items():
        print(f"  {key}: {video_dict}")
    
    if not videos:
        print("✗ No jumping jacks videos found")
        return False
    
    # Test with first available video
    test_key = list(videos.keys())[0]
    test_videos = videos[test_key]
    
    # Use front video if available, otherwise any video
    video_path = test_videos.get('front') or list(test_videos.values())[0]
    age_years = 6 if 'age6' in test_key else 7
    
    print(f"\nTesting with: {video_path}")
    print(f"Age: {age_years} years")
    
    try:
        result = process_jumping_jacks(video_path, age_years)
        print("✓ Jumping jacks test PASSED")
        print(f"  Total Score: {result.get('totalScore', 'N/A')}")
        print(f"  Max Score: {result.get('maxScore', 'N/A')}")
        print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
        if 'rawMetrics' in result:
            print(f"  Raw metrics keys: {list(result['rawMetrics'].keys())}")
        return True
    except Exception as e:
        print(f"✗ Jumping jacks test FAILED: {e}")
        print(traceback.format_exc())
        return False

def test_one_leg_standing():
    """Test all OLS variations"""
    print("\n" + "="*50)
    print("Testing One-Leg Standing Processors")
    print("="*50)
    
    ols_types = [
        ('ols_ll_ec', 'L', False),  # Left leg, eyes closed
        ('ols_ll_eo', 'L', True),   # Left leg, eyes open
        ('ols_rl_ec', 'R', False),  # Right leg, eyes closed
        ('ols_rl_eo', 'R', True),   # Right leg, eyes open
    ]
    
    results = {}
    
    for ols_type, raised_leg, eyes_open in ols_types:
        print(f"\nTesting {ols_type} (raised leg: {raised_leg}, eyes: {'open' if eyes_open else 'closed'})")
        
        exercise_root = os.path.join(r"c:\Users\anish\OneDrive\Desktop\bio med\exersise", ols_type)
        videos = find_video_files(exercise_root)
        
        if not videos:
            print(f"✗ No videos found for {ols_type}")
            results[ols_type] = False
            continue
        
        # Test with first available participant
        test_key = list(videos.keys())[0]
        test_videos = videos[test_key]
        age_years = 6 if 'age6' in test_key else 7
        
        front_video = test_videos.get('front')
        side_video = test_videos.get('side')
        
        print(f"  Front video: {front_video}")
        print(f"  Side video: {side_video}")
        print(f"  Age: {age_years} years")
        
        try:
            result = process_one_leg_standing(front_video, side_video, age_years, eyes_open, raised_leg)
            print(f"✓ {ols_type} test PASSED")
            print(f"  Total Score: {result.get('totalScore', 'N/A')}")
            print(f"  Max Score: {result.get('maxScore', 'N/A')}")
            print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
            if 'rawMetrics' in result:
                print(f"  Raw metrics keys: {list(result['rawMetrics'].keys())}")
            results[ols_type] = True
        except Exception as e:
            print(f"✗ {ols_type} test FAILED: {e}")
            print(traceback.format_exc())
            results[ols_type] = False
    
    return results

def test_tandem_walking():
    """Test tandem walking variations"""
    print("\n" + "="*50)
    print("Testing Tandem Walking Processors")
    print("="*50)
    
    tandem_types = [
        ('tadem_ec', False),  # Eyes closed
        ('tadem_eo', True),   # Eyes open
    ]
    
    results = {}
    
    for tandem_type, eyes_open in tandem_types:
        print(f"\nTesting {tandem_type} (eyes: {'open' if eyes_open else 'closed'})")
        
        exercise_root = os.path.join(r"c:\Users\anish\OneDrive\Desktop\bio med\exersise", tandem_type)
        videos = find_video_files(exercise_root)
        
        if not videos:
            print(f"✗ No videos found for {tandem_type}")
            results[tandem_type] = False
            continue
        
        # Test with first available participant
        test_key = list(videos.keys())[0]
        test_videos = videos[test_key]
        age_years = 6 if 'age6' in test_key else 7
        
        front_video = test_videos.get('front')
        side_video = test_videos.get('side')
        
        print(f"  Front video: {front_video}")
        print(f"  Side video: {side_video}")
        print(f"  Age: {age_years} years")
        
        try:
            result = process_tandem_walking(front_video, side_video, age_years, eyes_open)
            print(f"✓ {tandem_type} test PASSED")
            print(f"  Total Score: {result.get('totalScore', 'N/A')}")
            print(f"  Max Score: {result.get('maxScore', 'N/A')}")
            print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
            if 'rawMetrics' in result:
                print(f"  Raw metrics keys: {list(result['rawMetrics'].keys())}")
            results[tandem_type] = True
        except Exception as e:
            print(f"✗ {tandem_type} test FAILED: {e}")
            print(traceback.format_exc())
            results[tandem_type] = False
    
    return results

def test_backend_api():
    """Test the FastAPI backend with structured data"""
    print("\n" + "="*50)
    print("Testing Backend API Integration")
    print("="*50)
    
    # Test if we can import FastAPI main
    try:
        from main import app
        print("✓ Backend main app imported successfully")
    except Exception as e:
        print(f"✗ Backend import failed: {e}")
        return False
    
    # Test exercise ID mappings
    from main import EXERCISE_ID_TO_ASSESSMENT_KEY
    print(f"✓ Exercise mappings available: {list(EXERCISE_ID_TO_ASSESSMENT_KEY.keys())}")
    
    return True

def main():
    """Run all tests"""
    print("Starting Processor Testing Suite")
    print("This will test all exercise processors with real video data")
    
    # Make sure we can activate the environment
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    
    results = {}
    
    # Test individual processors
    results['jumping_jacks'] = test_jumping_jacks()
    results['ols'] = test_one_leg_standing()
    results['tandem'] = test_tandem_walking()
    results['backend'] = test_backend_api()
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    all_passed = True
    
    if results['jumping_jacks']:
        print("✓ Jumping Jacks: PASSED")
    else:
        print("✗ Jumping Jacks: FAILED")
        all_passed = False
    
    if isinstance(results['ols'], dict):
        ols_passed = all(results['ols'].values())
        if ols_passed:
            print("✓ One-Leg Standing (all variations): PASSED")
        else:
            print("✗ One-Leg Standing: Some variations FAILED")
            for ols_type, passed in results['ols'].items():
                status = "PASSED" if passed else "FAILED"
                print(f"    {ols_type}: {status}")
            all_passed = False
    else:
        print("✗ One-Leg Standing: FAILED to initialize")
        all_passed = False
    
    if isinstance(results['tandem'], dict):
        tandem_passed = all(results['tandem'].values())
        if tandem_passed:
            print("✓ Tandem Walking (all variations): PASSED")
        else:
            print("✗ Tandem Walking: Some variations FAILED")
            for tandem_type, passed in results['tandem'].items():
                status = "PASSED" if passed else "FAILED"
                print(f"    {tandem_type}: {status}")
            all_passed = False
    else:
        print("✗ Tandem Walking: FAILED to initialize")
        all_passed = False
    
    if results['backend']:
        print("✓ Backend API: PASSED")
    else:
        print("✗ Backend API: FAILED")
        all_passed = False
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Your processors are working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the error messages above for details.")
        print("\nCommon issues to check:")
        print("- MOV files may not be supported (convert to MP4)")
        print("- Missing dependencies (install MediaPipe, OpenCV, etc.)")
        print("- Python path issues (make sure scoring modules are importable)")
    
    return all_passed

if __name__ == "__main__":
    main()