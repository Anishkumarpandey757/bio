#!/usr/bin/env python3
"""
Test just the scoring modules without the processors first
"""

import os
import sys

# Add Sensory-Flow backend to path
sensory_flow_backend = os.path.join(os.getcwd(), 'Sensory-Flow', 'backend')
sys.path.insert(0, sensory_flow_backend)

print(f"Testing scoring imports from: {sensory_flow_backend}")

try:
    # Test scoring module imports - use the wrapper functions
    print("Testing scoring wrapper functions...")
    from scoring import score_jumping_jacks
    print("✓ score_jumping_jacks")
    
    from scoring import score_ols
    print("✓ score_ols")
    
    from scoring import score_tandem_walking
    print("✓ score_tandem_walking")
    
    print("\n🎉 All scoring wrapper functions imported successfully!")
    
    # Now test processors
    print("\nTesting processor imports...")
    
    from processors.jumping_jacks_fixed import process_jumping_jacks
    print("✓ jumping_jacks_fixed")
    
    from processors.one_leg_standing_fixed import process_one_leg_standing
    print("✓ one_leg_standing_fixed")
    
    from processors.tandem_walking_fixed import process_tandem_walking
    print("✓ tandem_walking_fixed")
    
    print("\n🎉 All processors imported successfully!")
    
except ImportError as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()