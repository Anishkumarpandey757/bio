#!/usr/bin/env python3
"""
Simplified test script to test processors with actual video data
Tests OLS, Jumping Jacks, and Tandem Walking processors
"""

import os
import sys
import traceback
from pathlib import Path

def add_sensory_flow_to_path():
    """Add Sensory-Flow backend to Python path"""
    sensory_flow_backend = os.path.join(os.getcwd(), 'Sensory-Flow', 'backend')
    if sensory_flow_backend not in sys.path:
        sys.path.insert(0, sensory_flow_backend)
    print(f"Added to path: {sensory_flow_backend}")

def test_imports():
    """Test if we can import all needed modules"""
    print("Testing imports...")
    
    try:
        # Test basic imports
        import cv2
        import numpy as np
        import pandas as pd
        import mediapipe as mp
        print("✓ Basic packages (cv2, numpy, pandas, mediapipe)")
        
        # Test processors
        from processors.jumping_jacks_fixed import process_jumping_jacks
        from processors.one_leg_standing_fixed import process_one_leg_standing  
        from processors.tandem_walking_fixed import process_tandem_walking
        print("✓ Processor modules")
        
        # Test scoring modules
        from scoring import math_jumping_jacks
        from scoring import math_ols_ec, math_ols_eo
        from scoring import math_tandem_walking_ec, math_tandem_walking_eo
        print("✓ Scoring modules")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def find_test_videos():
    """Find test videos in the exercise folder"""
    exercise_root = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise" 
    test_videos = {}
    
    # Look for jumping jacks
    jj_path = os.path.join(exercise_root, "jumping_jacks")
    if os.path.exists(jj_path):
        for age in ["6", "7"]:
            age_path = os.path.join(jj_path, age)
            if os.path.exists(age_path):
                for participant in os.listdir(age_path):
                    participant_path = os.path.join(age_path, participant)
                    if os.path.isdir(participant_path):
                        # Look for Front folder with video
                        front_path = os.path.join(participant_path, "Front")
                        if os.path.exists(front_path):
                            for file in os.listdir(front_path):
                                if file.lower().endswith(('.mp4', '.mov')):
                                    test_videos[f"jumping_jacks_age{age}"] = {
                                        'video': os.path.join(front_path, file),
                                        'age': int(age),
                                        'participant': participant
                                    }
                                    break
                        break
                break
    
    # Look for OLS videos - Left Leg Eyes Closed as test case
    ols_path = os.path.join(exercise_root, "ols_ll_ec")
    if os.path.exists(ols_path):
        for age in ["6", "7"]:
            age_path = os.path.join(ols_path, age)
            if os.path.exists(age_path):
                for participant in os.listdir(age_path):
                    participant_path = os.path.join(age_path, participant)
                    if os.path.isdir(participant_path):
                        front_video = None
                        side_video = None
                        
                        # Look for Front and Side videos
                        for view in ["Front", "Side"]:
                            view_path = os.path.join(participant_path, view)
                            if os.path.exists(view_path):
                                for file in os.listdir(view_path):
                                    if file.lower().endswith(('.mp4', '.mov')):
                                        if view == "Front":
                                            front_video = os.path.join(view_path, file)
                                        else:
                                            side_video = os.path.join(view_path, file)
                                        break
                        
                        if front_video or side_video:
                            test_videos[f"ols_ll_ec_age{age}"] = {
                                'front_video': front_video,
                                'side_video': side_video,
                                'age': int(age),
                                'participant': participant,
                                'raised_leg': 'L',
                                'eyes_open': False
                            }
                        break
                break
    
    # Look for Tandem Walking - Eyes Closed as test case  
    tandem_path = os.path.join(exercise_root, "tadem_ec")
    if os.path.exists(tandem_path):
        for age in ["6", "7"]:
            age_path = os.path.join(tandem_path, age)
            if os.path.exists(age_path):
                for participant in os.listdir(age_path):
                    participant_path = os.path.join(age_path, participant)
                    if os.path.isdir(participant_path):
                        front_video = None
                        side_video = None
                        
                        # Look for Front and Side videos
                        for view in ["Front", "Side"]:
                            view_path = os.path.join(participant_path, view)
                            if os.path.exists(view_path):
                                for file in os.listdir(view_path):
                                    if file.lower().endswith(('.mp4', '.mov')):
                                        if view == "Front":
                                            front_video = os.path.join(view_path, file)
                                        else:
                                            side_video = os.path.join(view_path, file)
                                        break
                        
                        if front_video or side_video:
                            test_videos[f"tadem_ec_age{age}"] = {
                                'front_video': front_video,
                                'side_video': side_video,
                                'age': int(age),
                                'participant': participant,
                                'eyes_open': False
                            }
                        break
                break
    
    return test_videos

def test_jumping_jacks(video_info):
    """Test jumping jacks processor"""
    print(f"\n--- Testing Jumping Jacks ---")
    print(f"Video: {video_info['video']}")
    print(f"Age: {video_info['age']}")
    print(f"Participant: {video_info['participant']}")
    
    try:
        from processors.jumping_jacks_fixed import process_jumping_jacks
        result = process_jumping_jacks(video_info['video'], video_info['age'])
        
        print("✓ Jumping Jacks processing successful!")
        print(f"  Total Score: {result.get('totalScore', 'N/A')}")
        print(f"  Max Score: {result.get('maxScore', 'N/A')}")
        print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
        
        if 'rawMetrics' in result:
            print(f"  Raw metrics available: {len(result['rawMetrics'])} items")
            
        return True
        
    except Exception as e:
        print(f"✗ Jumping Jacks test failed: {e}")
        print(traceback.format_exc())
        return False

def test_ols(video_info):
    """Test one-leg standing processor"""
    print(f"\n--- Testing One-Leg Standing ---")
    print(f"Front video: {video_info['front_video']}")
    print(f"Side video: {video_info['side_video']}")
    print(f"Age: {video_info['age']}")
    print(f"Raised leg: {video_info['raised_leg']}")
    print(f"Eyes open: {video_info['eyes_open']}")
    print(f"Participant: {video_info['participant']}")
    
    try:
        from processors.one_leg_standing_fixed import process_one_leg_standing
        result = process_one_leg_standing(
            video_info['front_video'], 
            video_info['side_video'], 
            video_info['age'], 
            video_info['eyes_open'], 
            video_info['raised_leg']
        )
        
        print("✓ One-Leg Standing processing successful!")
        print(f"  Total Score: {result.get('totalScore', 'N/A')}")
        print(f"  Max Score: {result.get('maxScore', 'N/A')}")
        print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
        
        if 'rawMetrics' in result:
            print(f"  Raw metrics available: {len(result['rawMetrics'])} items")
            
        return True
        
    except Exception as e:
        print(f"✗ One-Leg Standing test failed: {e}")
        print(traceback.format_exc())
        return False

def test_tandem_walking(video_info):
    """Test tandem walking processor"""
    print(f"\n--- Testing Tandem Walking ---")
    print(f"Front video: {video_info['front_video']}")
    print(f"Side video: {video_info['side_video']}")
    print(f"Age: {video_info['age']}")
    print(f"Eyes open: {video_info['eyes_open']}")
    print(f"Participant: {video_info['participant']}")
    
    try:
        from processors.tandem_walking_fixed import process_tandem_walking
        result = process_tandem_walking(
            video_info['front_video'], 
            video_info['side_video'], 
            video_info['age'], 
            video_info['eyes_open']
        )
        
        print("✓ Tandem Walking processing successful!")
        print(f"  Total Score: {result.get('totalScore', 'N/A')}")
        print(f"  Max Score: {result.get('maxScore', 'N/A')}")
        print(f"  Interpretation: {result.get('interpretation', 'N/A')}")
        
        if 'rawMetrics' in result:
            print(f"  Raw metrics available: {len(result['rawMetrics'])} items")
            
        return True
        
    except Exception as e:
        print(f"✗ Tandem Walking test failed: {e}")
        print(traceback.format_exc())
        return False

def main():
    """Main test function"""
    print("="*60)
    print("PROCESSOR TESTING WITH ACTUAL VIDEO DATA")
    print("="*60)
    
    # Change to the correct directory
    os.chdir(r"c:\Users\anish\OneDrive\Desktop\bio med")
    print(f"Working directory: {os.getcwd()}")
    
    # Add Sensory-Flow to path
    add_sensory_flow_to_path()
    
    # Test imports
    if not test_imports():
        print("Cannot proceed - import failures")
        return
    
    # Find test videos
    print("\nFinding test videos...")
    test_videos = find_test_videos()
    
    if not test_videos:
        print("No test videos found!")
        return
    
    print(f"Found {len(test_videos)} test video sets:")
    for key, info in test_videos.items():
        print(f"  {key}: {info.get('participant', 'Unknown')}")
    
    # Run tests
    results = {}
    
    # Test Jumping Jacks
    jj_videos = {k: v for k, v in test_videos.items() if 'jumping_jacks' in k}
    if jj_videos:
        for key, video_info in jj_videos.items():
            results[key] = test_jumping_jacks(video_info)
    
    # Test One-Leg Standing
    ols_videos = {k: v for k, v in test_videos.items() if 'ols_' in k}
    if ols_videos:
        for key, video_info in ols_videos.items():
            results[key] = test_ols(video_info)
    
    # Test Tandem Walking
    tandem_videos = {k: v for k, v in test_videos.items() if 'tadem_' in k}
    if tandem_videos:
        for key, video_info in tandem_videos.items():
            results[key] = test_tandem_walking(video_info)
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "PASSED" if success else "FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your processors are working correctly.")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check errors above.")
        print("\nCommon fixes needed:")
        print("- Convert MOV files to MP4 (MOV format may not be supported)")
        print("- Check video file paths and permissions")
        print("- Verify scoring module imports are working")

if __name__ == "__main__":
    main()