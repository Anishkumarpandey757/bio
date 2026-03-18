# Backend Processors vs Origin Colab Reference

Backend processors are aligned with the following **origin** Colab notebooks (outside the backend). Sway metrics use the same convention: **small values = less tilt** (report as `90 - angle_from_vertical` where needed).

## One Leg Standing (OLS)

| Backend module | Origin colabs | Variants |
|----------------|---------------|----------|
| `one_leg_standing_colab_exact.py` | `ols_rightleg_eo/ols_rightleg_eo_colab.py`<br>`ols_rightleg_ec/ols_rightleg_ec_colab.py`<br>`ols_left_leg_eo/ols_leftleg_eo_colab.py`<br>`ols_leftleg_ec/ols_leftleg_ec_colab.py` | Right/Left leg, Eyes Open/Closed (via `raised_leg`, `eyes_open`) |

- **Sway:** `angle_signed_to_vertical(hp2, sh2)`, `trunk_abs_deg`; summarized as `(90 - mean)` so output matches origin (2–8° range).
- **Neck, drift, toe touches, strategy:** Same logic as origin.

## Tandem Walking

| Backend module | Origin colabs |
|----------------|---------------|
| `tandem_walking_colab_exact_v2.py` | `tademwalkingeo/tademmanin_colab.py` (Eyes Open)<br>`tademwalkingec/tademmanin_colab.py` (Eyes Closed) |

- **Sway:** Front view → `ml_sway_mean_deg` / `ml_sway_sd_deg`; side view → `ap_sway_mean_deg` / `ap_sway_sd_deg`. Reported as `(90 - angle)` to match origin and scoring rubrics.
- **Step gap, step counts:** From front/side data as in origin.

## Jumping Jacks

| Backend module | Origin colab |
|----------------|--------------|
| `jumping_jacks_colab_exact_v2.py` | `jumping_jacks/jumping_jacks colab.py` |

- **Metrics:** Shoulder abduction, hip abduction, trunk, reps; same formulas as origin.
- **MOV:** Handled via `ensure_video_readable()` (ffmpeg) in `common.py`.

## Shared

- **MOV handling:** All processors use `ensure_video_readable()` from `common.py` (convert MOV → MP4 when OpenCV cannot read the file).
- **Landmarks:** MediaPipe pose; same `LM` indices and 2D/3D usage as in the origin colabs.
