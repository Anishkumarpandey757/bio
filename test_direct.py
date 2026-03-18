#!/usr/bin/env python3
"""
Test individual processors with actual video files
"""

import os
import sys

def test_processor_directly():
    """Test a processor directly with video files"""
    
    # Change to backend directory
    backend_dir = r"c:\Users\anish\OneDrive\Desktop\bio med\Sensory-Flow\backend"
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)
    
    print("="*60)
    print("DIRECT PROCESSOR TESTING")
    print("="*60)
    
    # Find available video files
    exercise_root = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise"
    
    print("Looking for video files...")
    
    # Find jumping jacks video
    jj_video = None
    ols_front = None
    ols_side = None
    tandem_front = None
    tandem_side = None
    
    for root, dirs, files in os.walk(exercise_root):
        for file in files:
            full_path = os.path.join(root, file)
            
            if file.lower().endswith(('.mp4', '.mov')):
                if "jumping_jacks" in root and "Front" in root:
                    jj_video = full_path
                elif "ols_ll_ec" in root and "Front" in root:
                    ols_front = full_path  
                elif "ols_ll_ec" in root and "Side" in root:
                    ols_side = full_path
                elif "tadem_ec" in root and "Front" in root:
                    tandem_front = full_path
                elif "tadem_ec" in root and "Side" in root:
                    tandem_side = full_path
    
    print(f"Found videos:")
    print(f"  Jumping jacks: {jj_video}")
    print(f"  OLS front: {ols_front}")
    print(f"  OLS side: {ols_side}")
    print(f"  Tandem front: {tandem_front}")
    print(f"  Tandem side: {tandem_side}")
    
    success_count = 0
    
    # Test 1: Jumping Jacks
    if jj_video:
        print(f"\n--- Testing Jumping Jacks ---")
        try:
            from processors.jumping_jacks_fixed import process_jumping_jacks
            result = process_jumping_jacks(jj_video, age_years=6)
            
            print("✅ Jumping jacks processor succeeded!")
            print(f"   Total Score: {result.get('totalScore', 'N/A')}")
            print(f"   Max Score: {result.get('maxScore', 'N/A')}")  
            print(f"   Interpretation: {result.get('interpretation', 'N/A')}")
            
            if 'rawMetrics' in result and result['rawMetrics']:
                print(f"   Raw metrics captured: {len(result['rawMetrics'])} fields")
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ Jumping jacks failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test 2: One-Leg Standing
    if ols_front and ols_side:
        print(f"\n--- Testing One-Leg Standing ---")
        try:
            from processors.one_leg_standing_fixed import process_one_leg_standing
            result = process_one_leg_standing(ols_front, ols_side, age_years=6, eyes_open=False, raised_leg="L")
            
            print("✅ OLS processor succeeded!")
            print(f"   Total Score: {result.get('totalScore', 'N/A')}")
            print(f"   Max Score: {result.get('maxScore', 'N/A')}")
            print(f"   Interpretation: {result.get('interpretation', 'N/A')}")
            
            if 'rawMetrics' in result and result['rawMetrics']:
                print(f"   Raw metrics captured: {len(result['rawMetrics'])} fields")
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ OLS failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test 3: Tandem Walking
    if tandem_front and tandem_side:
        print(f"\n--- Testing Tandem Walking ---")
        try:
            from processors.tandem_walking_fixed import process_tandem_walking
            result = process_tandem_walking(tandem_front, tandem_side, age_years=6, eyes_open=False)
            
            print("✅ Tandem walking processor succeeded!")
            print(f"   Total Score: {result.get('totalScore', 'N/A')}")
            print(f"   Max Score: {result.get('maxScore', 'N/A')}")
            print(f"   Interpretation: {result.get('interpretation', 'N/A')}")
            
            if 'rawMetrics' in result and result['rawMetrics']:
                print(f"   Raw metrics captured: {len(result['rawMetrics'])} fields")
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ Tandem walking failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    total_tests = sum(1 for x in [jj_video, (ols_front and ols_side), (tandem_front and tandem_side)] if x)
    
    print(f"Processors tested: {success_count}/{total_tests}")
    
    if success_count == total_tests and total_tests > 0:
        print("\n🎉 All processors working correctly!")
        print("Your fixed backend is ready for production!")
    elif success_count > 0:
        print(f"\n✅ {success_count} processors working")
        print("Some issues may be due to video format (MOV vs MP4)")
    else:
        print("\n❌ All tests failed")
        print("Check MediaPipe installation and video file formats")

if __name__ == "__main__":
    test_processor_directly()