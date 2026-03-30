import json
import random
import urllib.request
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.scoring.math_total_assessment import score_assessment

API_BASE = "http://localhost:5000"

EXERCISE_IDS = [
    "prone_extension",
    "supine_flexion",
    "one_leg_left_close",
    "one_leg_left_open",
    "one_leg_right_close",
    "one_leg_right_open",
    "tandem_walking_close",
    "tandem_walking_open",
    "jumping_jacks",
]

ID_TO_MATH_KEY = {
    "prone_extension": "prone_extension",
    "supine_flexion": "supine_flexion",
    "one_leg_left_close": "ols_ll_ec",
    "one_leg_left_open": "ols_ll_eo",
    "one_leg_right_close": "ols_rl_ec",
    "one_leg_right_open": "ols_rl_eo",
    "tandem_walking_close": "tandem_ec",
    "tandem_walking_open": "tandem_eo",
    "jumping_jacks": "jumping_jacks",
}


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def random_exercise_result(ex_id: str) -> dict:
    total = random.randint(18, 35)
    max_score = 35 if ex_id == "jumping_jacks" else random.choice([25, 34, 35, 36])
    return {
        "exerciseId": ex_id,
        "status": "completed",
        "result": {
            "rawMetrics": {
                "metric_a": round(random.uniform(0.1, 10.0), 3),
                "metric_b": round(random.uniform(0.1, 10.0), 3),
            },
            "scores": {
                "total_score": total,
            },
            "totalScore": total,
            "maxScore": max_score,
            "interpretation": random.choice([
                "Average",
                "Above Average",
                "Below Average",
                "Well-Above Average",
            ]),
        },
    }


def main() -> None:
    random.seed()

    exercises = [random_exercise_result(eid) for eid in EXERCISE_IDS]

    payload = {
        "demographic": {
            "childName": f"Student_{random.randint(1000, 9999)}",
            "gender": random.choice(["Male", "Female", "Others"]),
            "dateOfBirth": "2019-02-14",
            "dateOfAssessment": "2026-03-30",
            "calculatedAge": "7 years 2 months",
        },
        "birthMedical": {
            "lowBirthWeight": "No",
            "premature": "No",
            "birthComplications": "No",
            "developmentalDisability": "No",
        },
        "physicalParameters": {
            "height": 1.23,
            "weight": 24.5,
            "bmi": 16.2,
        },
        "educationalInfo": {
            "enrolledInSchool": "Yes",
            "educationType": "Mainstream",
            "standardClass": "2",
            "schoolName": "Demo School",
        },
        "caregiverInfo": {
            "caregiverName": "Parent Demo",
            "relationToChild": "Mother",
            "caregiverContact": "9999999999",
        },
        "therapistInfo": {
            "therapistName": "Therapist Demo",
            "therapistProfession": "OT",
            "licenseNumber": "LIC-001",
            "therapistDesignation": "Senior Therapist",
            "serviceProviderDetails": "Sensory Center",
        },
        "ageGroup": "7 years 0 months - 7 years 11 months",
        "exercises": exercises,
        "status": "in_progress",
    }

    created = post_json(f"{API_BASE}/api/assessments", payload)
    assessment_id = created["id"]

    stored = get_json(f"{API_BASE}/api/assessments/{assessment_id}")

    exercise_scores = {}
    for ex in stored.get("exercises", []):
        ex_id = ex.get("exerciseId")
        if ex_id not in ID_TO_MATH_KEY:
            continue
        total_score = ((ex.get("result") or {}).get("totalScore"))
        exercise_scores[ID_TO_MATH_KEY[ex_id]] = {"total_score": total_score}

    total_summary = score_assessment(exercise_scores, age_years=7)

    print("=== MONGO SAVE/READ VERIFICATION ===")
    print(f"Assessment ID: {assessment_id}")
    print(f"Student: {stored.get('demographic', {}).get('childName')}")
    print(f"Exercises stored: {len(stored.get('exercises', []))}")

    print("\n=== PER-EXERCISE SCORES USED FOR MATH ===")
    for k, v in exercise_scores.items():
        print(f"{k}: {v.get('total_score')}")

    print("\n=== TOTAL ASSESSMENT (math_total_assessment.py) ===")
    print(json.dumps(total_summary, indent=2))


if __name__ == "__main__":
    main()
