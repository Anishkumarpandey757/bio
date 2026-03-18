# How to Start SensoryAssess Pro

## Quick Start (2 terminals required)

### Terminal 1: Start the FastAPI backend (video processing)

Run from the **project root** (`Sensory-Flow`), not from inside `backend`:

```bash
cd Sensory-Flow
python -m uvicorn backend.main:app --reload --port 8000
```

### Terminal 2: Start the Express server (frontend + API)

```bash
npm run dev
```

Then open **http://localhost:5000** in your browser.

---

## What each server does

| Server   | Port | Purpose                                      |
|----------|------|----------------------------------------------|
| Express  | 5000 | Serves the React app, API routes, and Vite HMR |
| FastAPI  | 8000 | Video processing and exercise scoring       |

## Troubleshooting

### `net::ERR_CONNECTION_REFUSED` or `Failed to fetch`

1. **Express not running** – Run `npm run dev` in the project root.
2. **FastAPI not running** – From project root: `python -m uvicorn backend.main:app --reload --port 8000`, or run `backend\run_server.bat` from the backend folder.
3. **Port in use** – Ensure ports 5000 and 8000 are free.

### Vite HMR connection refused

The frontend and HMR are served by Express on port 5000. Use `npm run dev` instead of running Vite separately.

---

## Backend processors (aligned with Colab reference code)

| Exercise          | Processor module                          | Videos      | MOV handling      |
|------------------|-------------------------------------------|-------------|-------------------|
| Prone extension  | `prone_extension`                         | Side only   | Yes (via common)  |
| Supine flexion   | `supine_flexion`                          | Side only   | Yes (via common)  |
| One leg standing | `one_leg_standing_colab_exact`            | Front + side| Yes               |
| Tandem walking   | `tandem_walking_colab_exact_v2`           | Front + side| Yes               |
| Jumping jacks    | `jumping_jacks_colab_exact_v2`            | Front (+ side optional) | Yes   |

Reference Colab implementations live in folders outside the backend (e.g. `proneextention/`, `tademwalkingeo/`, `tademwalkingec/`, `jumping_jacks/`, `ols_*`). MOV files are auto-converted to MP4 using ffmpeg when OpenCV cannot read them.
