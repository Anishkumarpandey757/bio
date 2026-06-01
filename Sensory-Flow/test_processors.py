"""
Test all backend processors directly against exercise videos (7yr, Akshan Roy A).
Run from: cd Sensory-Flow && python test_processors.py
"""
import sys, os, json, time

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(__file__))

BASE = r"c:\Users\anish\OneDrive\Desktop\bio med\exersise"
STUDENT = "Akshan Roy A"
AGE = 7

def vpath(exercise, view):
    """Get video path for exercise/view"""
    d = os.path.join(BASE, exercise, "7", STUDENT, view)
    if not os.path.isdir(d):
        return None
    for f in os.listdir(d):
        if f.lower().endswith(('.mp4', '.mov', '.avi')):
            return os.path.join(d, f)
    return None

def pp(label, result):
    """Pretty print result"""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    if isinstance(result, dict):
        for k, v in result.items():
            if k == "rawMetrics" and isinstance(v, dict):
                print(f"  rawMetrics:")
                for mk, mv in v.items():
                    print(f"    {mk}: {mv}")
            elif k == "scores" and isinstance(v, dict):
                print(f"  scores:")
                for sk, sv in v.items():
                    print(f"    {sk}: {sv}")
            else:
                print(f"  {k}: {v}")
    else:
        print(f"  {result}")

# ============================================================
# 1. OLS RL Eyes Open
# ============================================================
print("\n\n>>> TEST 1: OLS Right Leg Eyes Open")
t0 = time.time()
from backend.processors.one_leg_standing_colab_exact import process_one_leg_standing
front = vpath("ols_rl_eo", "Front")
side = vpath("ols_rl_eo", "Side")
print(f"  Front: {front}")
print(f"  Side:  {side}")
result = process_one_leg_standing(front, side, age_years=AGE, eyes_open=True, raised_leg="R")
pp("OLS RL EO", result)
print(f"  Time: {time.time()-t0:.1f}s")

# ============================================================
# 2. OLS RL Eyes Close
# ============================================================
print("\n\n>>> TEST 2: OLS Right Leg Eyes Close")
t0 = time.time()
front = vpath("ols_rl_ec", "Front")
side = vpath("ols_rl_ec", "Side")
print(f"  Front: {front}")
print(f"  Side:  {side}")
result = process_one_leg_standing(front, side, age_years=AGE, eyes_open=False, raised_leg="R")
pp("OLS RL EC", result)
print(f"  Time: {time.time()-t0:.1f}s")

# ============================================================
# 3. OLS LL Eyes Open
# ============================================================
print("\n\n>>> TEST 3: OLS Left Leg Eyes Open")
t0 = time.time()
front = vpath("ols_ll_eo", "Front")
side = vpath("ols_ll_eo", "Side")
print(f"  Front: {front}")
print(f"  Side:  {side}")
result = process_one_leg_standing(front, side, age_years=AGE, eyes_open=True, raised_leg="L")
pp("OLS LL EO", result)
print(f"  Time: {time.time()-t0:.1f}s")

# ============================================================
# 4. OLS LL Eyes Close
# ============================================================
print("\n\n>>> TEST 4: OLS Left Leg Eyes Close")
t0 = time.time()
front = vpath("ols_ll_ec", "Front")
side = vpath("ols_ll_ec", "Side")
print(f"  Front: {front}")
print(f"  Side:  {side}")
result = process_one_leg_standing(front, side, age_years=AGE, eyes_open=False, raised_leg="L")
pp("OLS LL EC", result)
print(f"  Time: {time.time()-t0:.1f}s")

# ============================================================
# 5. Tandem Walking Eyes Open
# ============================================================
print("\n\n>>> TEST 5: Tandem Walking Eyes Open")
t0 = time.time()
from backend.processors.tandem_walking_colab_exact_v2 import process_tandem_walking
front = vpath("tadem_eo", "Front")
side = vpath("tadem_eo", "Side")
print(f"  Front: {front}")
print(f"  Side:  {side}")
result = process_tandem_walking(front, side, age_years=AGE, eyes_open=True)
pp("Tandem EO", result)
print(f"  Time: {time.time()-t0:.1f}s")

# ============================================================
# 6. Tandem Walking Eyes Close
# ============================================================
print("\n\n>>> TEST 6: Tandem Walking Eyes Close")
t0 = time.time()
front = vpath("tadem_ec", "Front")
side = vpath("tadem_ec", "Side")
print(f"  Front: {front}")
print(f"  Side:  {side}")
result = process_tandem_walking(front, side, age_years=AGE, eyes_open=False)
pp("Tandem EC", result)
print(f"  Time: {time.time()-t0:.1f}s")

# ============================================================
# 7. Jumping Jacks
# ============================================================
print("\n\n>>> TEST 7: Jumping Jacks")
t0 = time.time()
from backend.processors.jumping_jacks_colab_exact_v2 import process_jumping_jacks
front = vpath("jumping_jacks", "Front")
side = vpath("jumping_jacks", "Side")
print(f"  Front: {front}")
print(f"  Side:  {side}")
result = process_jumping_jacks(front, side, age_years=AGE)
pp("Jumping Jacks", result)
print(f"  Time: {time.time()-t0:.1f}s")

print("\n\n>>> ALL TESTS COMPLETE")
