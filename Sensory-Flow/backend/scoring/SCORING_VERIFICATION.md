# Scoring Tables Verification: Math Folder ↔ Backend Code

This document maps **math folder** Word files to backend scoring modules and summarizes thresholds so you can verify they match.

**Convention in code:** Intervals are typically **[lo, hi)** (closed-left, open-right). Upper bound "≥ X" in a doc usually becomes `x >= X: return score`; ranges like "Y – Z" become `Y <= x < Z`.

---

## 1. Math Folder Word Files (Expected)

| Word file | Backend module | Age |
|-----------|----------------|-----|
| One Leg Standing (RL EO) FS (6 Years) (3).docx | math_ols_rl_eo.py | 6y |
| One Leg Standing (RL EO) FS (7 Years) (2).docx | math_ols_rl_eo.py | 7y |
| One Leg Standing (RL EC) FS (6 Years) (2).docx | math_ols_rl_ec.py | 6y |
| One Leg Standing (RL EC) FS (7 Years) (2).docx | math_ols_rl_ec.py | 7y |
| One Leg Standing (LL EO) FS (6 YEARS) (2).docx | math_ols_eo.py | 6y |
| One Leg Standing (LL EO) FS (7 YEARS) (4).docx | math_ols_eo.py | 7y |
| One Leg Standing (LL EC) FS (6 Years) (2).docx | math_ols_ec.py | 6y |
| One Leg Standing (LL EC) FS (7 Years) (2).docx | math_ols_ec.py | 7y |
| Tandem Walking EO FS (6 Years) (1).docx | math_tandem_walking_eo.py | 6y |
| Tandem Walking EO FS (7 Years) (1).docx | math_tandem_walking_eo.py | 7y |
| Tandem Walking EC FS (6 Years) (2).docx | math_tandem_walking_ec.py | 6y |
| Tandem Walking EC FS (7 Years) (2).docx | math_tandem_walking_ec.py | 7y |
| Jumping Jacks FS (6 Years) (1).docx | math_jumping_jacks.py | 6y |
| Jumping Jacks FS (7 Years) (1).docx | math_jumping_jacks.py | 7y |

**Not in math folder:** Prone Extension and Supine Flexion. Backend references:
- `math_prone_extension.py`: "Corrected Prone Extension FS (6/7 Years).docx"
- `math_supine_flexion.py`: "Supine Flexion FS (6 years / 7 Years).docx"

If you have these elsewhere, compare against those modules.

---

## 2. OLS — One Leg Standing

### 2.1 RL EO (Right Leg, Eyes Open)
- **Code:** `math_ols_rl_eo.py`  
- **Source comments:** One Leg Standing (RL EO) FS (6 Years).docx, (7 Years).docx

**7 Years (from code):**
- sway_SS_mean: [≥10.24→1], [8.21–10.24→2], [6.18–8.21→3], [4.15–6.18→4], [2.12–4.15→5], [0–2.12→6]
- sway_SS_SD: [≥4.43→1], [3.56–4.43→2], [2.69–3.56→3], [1.82–2.69→4], [0.95–1.82→5], [0–0.95→6]
- sway_AP_mean: [≥9.02→1], [7.01–9.02→2], [5.00–7.01→3], [2.99–5.00→4], [0.98–2.99→5], [0–0.98→6]
- sway_AP_SD: [≥4.62→1], [3.63–4.62→2], [2.64–3.63→3], [1.65–2.64→4], [0.66–1.65→5], [0–0.66→6]
- toe_touches: [≥8→1], [6–8→2], [4–6→3], [2–4→4], [0–2→5]
- Total interpretation: &lt;13, 13–16, 16–19, 19–25, 25–28, 28–29

**6 Years:** See code (SS mean 11.56, 9.39, 7.22, …; toe_touches 18, 14, 10, 6, 2, 0).

### 2.2 RL EC (Right Leg, Eyes Closed)
- **Code:** `math_ols_rl_ec.py`

**7 Years:** SS mean 9.19, 7.55, 5.91, …; toe_touches 22, 17, 12, 7, 2, 0.  
**6 Years:** SS mean 11.89, 9.75, …; toe_touches 19, 16, 13, 10, 7, 4, 1, 0.

### 2.3 LL EO (Left Leg, Eyes Open)
- **Code:** `math_ols_eo.py`  
- **Note:** Uses `>` for top bin in some 7y (e.g. `x > 10.47`), rest `<=`/`<`.

**7 Years:** SS mean >10.47→1, 8.41–10.47→2, …; toe_touches ≥12→1, 9–12→2, 6–9→3, 3–6→4, 0–3→5.  
**6 Years:** SS mean ≥13.19→1, …; toe_touches ≥14→1, 11–14→2, …

### 2.4 LL EC (Left Leg, Eyes Closed)
- **Code:** `math_ols_ec.py`

**7 Years:** SS mean 10.32, 8.50, …; toe_touches 20, 16, 12, 8, 4, 0.  
**6 Years:** SS mean 12.31, 10.42, …; toe_touches 22, 18, 14, 10, 6, 2, 0.

---

## 3. Tandem Walking

### 3.1 EO (Eyes Open)
- **Code:** `math_tandem_walking_eo.py`  
- **Bins:** [lo, hi) with `Bin(lo, hi, score)`.

**6 Years:** ML mean 11.83+, 8.97–11.83, 6.11–8.97, …; Step gap 6.21+, 4.97–6.21, …; max total 34.  
**7 Years:** Similar structure; see `_EO7_*` in code.

### 3.2 EC (Eyes Closed)
- **Code:** `math_tandem_walking_ec.py`

**6 Years:** ML mean 7.53+, 5.96–7.53, …; Step gap 5.52+, 4.57–5.52, …; max total 37.  
**7 Years:** See `_EC7_*` in code.

---

## 4. Jumping Jacks

- **Code:** `math_jumping_jacks.py`

**6 Years:** Shoulder abduction (&lt;101.09→1, 101.09–117.99→2, … 168.69+→6); Hip abd (&lt;2.15→1, … 4.97+→8); Jump (&lt;0.93→1, … 4.57+→6); Arm-leg open sync (lower better: &lt;0.28→8, … ≥2.14→1); Arm-leg close sync (&lt;0.36→7, … ≥4.01→1). Total interpretation 0–15, 15–17, …, 27–35.  
**7 Years:** Different cutpoints; see `score_*_7y` and `interpret_total_7y`.

---

## 5. Prone Extension & Supine Flexion

- **Prone:** `math_prone_extension.py` — neck, trunk, hip, knee, hold bins for 6y and 7y.  
- **Supine:** `math_supine_flexion.py` — same parameter set, different bins.

No matching Word files in **math folder**; code refers to "Corrected Prone Extension FS" and "Supine Flexion FS". If your Prone/Supine tables live elsewhere, compare those docs to these two modules.

---

## 6. How to Verify

1. Open the Word file for the exercise/age (e.g. One Leg Standing (RL EO) FS (7 Years)).
2. Open the corresponding backend file (e.g. `math_ols_rl_eo.py`).
3. For each row in the Word table (e.g. “Sway SS Mean”): check that the **range boundaries** and **score** match the `if` conditions or `Bin(lo, hi, score)` in the code.
4. Check **total score interpretation** bands (e.g. “Average” 19–25) against `interpret_total_*` or `_*_TOTAL_RANGES`.

If you find a mismatch, note the parameter name, age, and the Word vs code values and update the relevant `math_*.py` file to match the Word table.
