"""
Test script to verify Colab-exact processors give correct sway angles (2-8 degrees)
instead of the wrong 90+ degree angles from the old *_fixed.py processors
"""

import os
import sys

# Add backend path
sys.path.insert(0, r'c:\Users\anish\OneDrive\Desktop\bio med\Sensory-Flow\backend')

print("=== TESTING COLAB-EXACT PROCESSORS ===")
print("Expected: Small angles like 2-8 degrees (not 90+ degrees)")
print()

# Test directories with structured video data
test_base = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise"

test_videos = {
    "jumping_jacks": {
        "6": os.path.join(test_base, "jumping_jacks", "6", "A. J. Kowsik"),
        "7": os.path.join(test_base, "jumping_jacks", "7", "Akshan Roy A")
    },
    "ols_ll_eo": {
        "6": os.path.join(test_base, "ols_ll_eo", "6", "A. J. Kowsik"),
        "7": os.path.join(test_base, "ols_ll_eo", "7", "Akshan Roy A")
    },
    "ols_ll_ec": {
        "6": os.path.join(test_base, "ols_ll_ec", "6", "A. J. Kowsik"),
        "7": os.path.join(test_base, "ols_ll_ec", "7", "Akshan Roy A")
    },
    "tadem_eo": {
        "6": os.path.join(test_base, "tadem_eo", "6", "A. J. Kowsik"),
        "7": os.path.join(test_base, "tadem_eo", "7", "Akshan Roy A")
    },
    "tadem_ec": {
        "6": os.path.join(test_base, "tadem_ec", "6", "A. J. Kowsik"),
        "7": os.path.join(test_base, "tadem_ec", "7", "Akshan Roy A")
    }
}

def find_video_files(directory):
    """Find Front.MOV and Side.MOV files in directory"""
    if not os.path.exists(directory):
        return None, None
    
    files = os.listdir(directory)
    front_file = side_file = None
    
    for f in files:
        if "Front" in f and f.endswith(('.MOV', '.mov', '.MP4', '.mp4')):
            front_file = os.path.join(directory, f)
        elif "Side" in f and f.endswith(('.MOV', '.mov', '.MP4', '.mp4')):
            side_file = os.path.join(directory, f)
    
    return front_file, side_file

def test_colab_exact_processors():
    """Test all Colab-exact processors"""
    
    # Import the Colab-exact processors
    try:
        from processors.jumping_jacks_colab_exact_v2 import process_jumping_jacks
        from processors.one_leg_standing_colab_exact_v2 import process_one_leg_standing
        from processors.tandem_walking_colab_exact_v2 import process_tandem_walking
        print("✓ All Colab-exact v2 processors imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return
    
    print()
    
    # Test jumping jacks
    print("--- Testing Jumping Jacks (Colab-exact) ---")
    jj_dir = test_videos["jumping_jacks"]["7"]  # 7-year-old
    front_video, side_video = find_video_files(jj_dir)
    
    if front_video or side_video:
        print(f"Processing: front={front_video}, side={side_video}")
        try:
            result = process_jumping_jacks(front_video, side_video, age_years=7)
            
            # Check the raw metrics for trunk sway
            raw = result.get("rawMetrics", {})
            sway_ss = raw.get("trunk_sway_SS_mean")
            sway_ap = raw.get("trunk_sway_AP_mean") 
            reps = raw.get("total_reps", 0)
            
            print(f"✓ Trunk sway SS mean: {sway_ss}°")
            print(f"✓ Trunk sway AP mean: {sway_ap}°")
            print(f"✓ Total reps: {reps}")
            print(f"✓ Total score: {result.get('totalScore', 0)}")
            
            # Check if angles are in expected range (should be small, not 90+)
            if sway_ss is not None and sway_ss < 30:
                print(f"✓ CORRECT: SS sway angle {sway_ss}° is in expected range (< 30°)")
            elif sway_ss is not None:
                print(f"✗ WARNING: SS sway angle {sway_ss}° seems too large")
            
            if sway_ap is not None and sway_ap < 30:
                print(f"✓ CORRECT: AP sway angle {sway_ap}° is in expected range (< 30°)")
            elif sway_ap is not None:
                print(f"✗ WARNING: AP sway angle {sway_ap}° seems too large")
                
        except Exception as e:
            print(f"✗ Jumping jacks processing error: {e}")
    else:
        print("✗ No videos found for jumping jacks")
    
    print()
    
    # Test OLS (left leg, eyes open)
    print("--- Testing OLS Left Leg Eyes Open (Colab-exact) ---")
    ols_dir = test_videos["ols_ll_eo"]["7"]  # 7-year-old
    front_video, side_video = find_video_files(ols_dir)
    
    if front_video or side_video:
        print(f"Processing: front={front_video}, side={side_video}")
        try:
            result = process_one_leg_standing(front_video, side_video, age_years=7, 
                                            eyes_open=True, raised_leg="L")
            
            # Check the raw metrics for sway
            raw = result.get("rawMetrics", {})
            sway_ss = raw.get("sway_SS_mean")
            sway_ap = raw.get("sway_AP_mean")
            
            print(f"✓ Sway SS mean: {sway_ss}°")
            print(f"✓ Sway AP mean: {sway_ap}°")
            print(f"✓ Total score: {result.get('totalScore', 0)}")
            
            # Check if angles are in expected range (should be small, not 90+)
            if sway_ss is not None and sway_ss < 30:
                print(f"✓ CORRECT: SS sway angle {sway_ss}° is in expected range (< 30°)")
            elif sway_ss is not None:
                print(f"✗ WARNING: SS sway angle {sway_ss}° seems too large")
            
            if sway_ap is not None and sway_ap < 30:
                print(f"✓ CORRECT: AP sway angle {sway_ap}° is in expected range (< 30°)")
            elif sway_ap is not None:
                print(f"✗ WARNING: AP sway angle {sway_ap}° seems too large")
                
        except Exception as e:
            print(f"✗ OLS processing error: {e}")
    else:
        print("✗ No videos found for OLS")
    
    print()
    
    # Test Tandem Walking (eyes open)
    print("--- Testing Tandem Walking Eyes Open (Colab-exact) ---")
    tandem_dir = test_videos["tadem_eo"]["7"]  # 7-year-old
    front_video, side_video = find_video_files(tandem_dir)
    
    if front_video or side_video:
        print(f"Processing: front={front_video}, side={side_video}")
        try:
            result = process_tandem_walking(front_video, side_video, age_years=7, eyes_open=True)
            
            # Check the raw metrics for sway
            raw = result.get("rawMetrics", {})
            sway_ss = raw.get("sway_SS_mean")
            sway_ap = raw.get("sway_AP_mean")
            total_steps = raw.get("total_steps", 0)
            
            print(f"✓ Sway SS mean: {sway_ss}°")
            print(f"✓ Sway AP mean: {sway_ap}°")
            print(f"✓ Total steps: {total_steps}")
            print(f"✓ Total score: {result.get('totalScore', 0)}")
            
            # Check if angles are in expected range (should be small, not 90+)
            if sway_ss is not None and sway_ss < 30:
                print(f"✓ CORRECT: SS sway angle {sway_ss}° is in expected range (< 30°)")
            elif sway_ss is not None:
                print(f"✗ WARNING: SS sway angle {sway_ss}° seems too large")
            
            if sway_ap is not None and sway_ap < 30:
                print(f"✓ CORRECT: AP sway angle {sway_ap}° is in expected range (< 30°)")
            elif sway_ap is not None:
                print(f"✗ WARNING: AP sway angle {sway_ap}° seems too large")
                
        except Exception as e:
            print(f"✗ Tandem walking processing error: {e}")
    else:
        print("✗ No videos found for tandem walking")
    
    print()
    print("=== TEST COMPLETE ===")
    print("Expected result: All sway angles should be < 30° (typically 2-8°)")
    print("If angles are 90+°, the old wrong calculations are still being used")

if __name__ == "__main__":
    test_colab_exact_processors()