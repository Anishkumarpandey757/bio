# SensoryAssess Pro (Bio Med)

Full-stack pediatric sensory-motor assessment platform with:
- React frontend (multi-step assessment flow)
- Express API layer (frontend API + Mongo persistence)
- FastAPI video-processing backend (MediaPipe + exercise scoring)
- Assessment-level math aggregation (z-score + interpretation)

## 1. Project Workflow (End-to-End)

1. User fills student demographics and therapist details in frontend.
2. User uploads exercise videos (front/side based on exercise requirement).
3. Frontend calls Express endpoint `/api/process-exercise`.
4. Express forwards files to FastAPI endpoint `/api/process-exercise-files/{exercise_id}`.
5. FastAPI extracts raw metrics and computes per-exercise scores.
6. Frontend displays each exercise result immediately.
7. On Save Assessment, frontend sends complete assessment JSON to Express `/api/assessments`.
8. Express stores full structured assessment in MongoDB Atlas.
9. Total assessment score can be computed from `backend/scoring/math_total_assessment.py`.

## 2. Tech Stack

- Frontend: React + TypeScript + Vite + Tailwind
- API server: Node.js + Express + Multer + Axios
- Video processing: Python + FastAPI + MediaPipe + OpenCV
- Database: MongoDB Atlas (assessment storage)

## 3. Folder/File Meaning (What each file is for)

### Root
- `README.md`: this guide
- `.env`: runtime environment values (Mongo URI, FastAPI URL)
- `package.json`: Node scripts + dependencies
- `script/verify_mongo_assessment_flow.py`: terminal verifier for full data flow

### Frontend
- `client/src/pages/Assessment.tsx`: main multi-step UI and results screen
- `client/src/pages/ExerciseDetail.tsx`: per-exercise upload/process page
- `client/src/context/AssessmentContext.tsx`: global assessment state, save/load logic
- `client/src/components/ReportGenerator.tsx`: PDF generation output

### Express API
- `server/index.ts`: server boot and middleware
- `server/routes.ts`: API routes (`/api/assessments`, `/api/process-exercise`, etc.)
- `server/storage.ts`: Mongo-backed persistence implementation

### FastAPI and scoring
- `backend/main.py`: processing routes and exercise routing
- `backend/processors/*.py`: per-exercise metric extraction + scoring wrappers
- `backend/scoring/math_total_assessment.py`: total assessment aggregation math

## 4. Exercise IDs used in workflow

- `prone_extension`
- `supine_flexion`
- `one_leg_right_open`
- `one_leg_right_close`
- `one_leg_left_open`
- `one_leg_left_close`
- `tandem_walking_open`
- `tandem_walking_close`
- `jumping_jacks`

## 5. Environment Setup

Create `.env` in project root:

```env
DATABASE_URL=mysql://root:Anish%40123@localhost:3306/biomed
MONGODB_URI=mongodb+srv://samaltman2204_db_user:s94h5G9dadGjSRWa@cluster0.fgx67qg.mongodb.net/?appName=Cluster0
FASTAPI_URL=http://localhost:8000
EXPRESS_PORT=5000
NODE_ENV=development
```

Note:
- For Mongo URI credentials with `@`, use `%40` in password.
- Assessments are stored via `MONGODB_URI`.

## 6. Install Dependencies

### Node
```bash
npm install
```

### Python
Use your active Python env and install backend requirements (if needed):
```bash
cd backend
pip install -r requirements.txt
```

## 7. Run Application (2 servers)

### Terminal A: FastAPI backend
Run from project root:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Health check:
```bash
curl http://127.0.0.1:8000/health
```

### Terminal B: Frontend + Express
Run from project root:
```bash
npm run dev
```

Open:
- Frontend: `http://localhost:5000`

## 8. Verify Full Data Flow in Terminal

Run verifier script:
```bash
python script/verify_mongo_assessment_flow.py
```

What it verifies:
- Creates random student with all 9 exercise results
- Saves assessment via frontend API (`/api/assessments`)
- Reads stored document back from Mongo (`/api/assessments/{id}`)
- Computes total assessment score from math file
- Prints score breakdown, z-score, interpretation

## 9. How frontend final results work

- `Process Exercise` computes and updates that exercise result in frontend state.
- `Proceed to Results` shows the latest processed values from frontend state.
- `Save Assessment` persists all current values to MongoDB.

## 10. Troubleshooting

### `Failed to fetch` / `ERR_CONNECTION_REFUSED`
- Ensure both servers are running (5000 and 8000).

### `500: Failed to create assessment`
- Check Mongo URI in `.env`.
- Confirm Express server restarted after `.env` changes.
- Check Express logs in terminal for detailed error payload.

### MediaPipe/Protobuf error (`GetPrototype`)
- Ensure protobuf is compatible with mediapipe in the Python environment used by uvicorn.

## 11. Git workflow for this repo

```bash
git status
git add README.md
git commit -m "Add detailed README for setup, workflow, and Mongo verification"
git push origin main
```

If branch is not `main`, replace with your current branch name.

---

For contributors: keep exercise IDs and mapping consistent across frontend, Express routes, FastAPI processors, and total assessment math keys.
