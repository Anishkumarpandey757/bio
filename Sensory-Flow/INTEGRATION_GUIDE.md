# SensoryAssess Pro - Full Stack Integration Guide

## Architecture Overview

The system consists of three main components:

1. **React Frontend** (React + TypeScript + Vite)
   - Location: `client/src/`
   - Components for video upload, trimming, and result display
   
2. **Express.js Backend** (Node.js + Express)
   - Location: `server/`
   - Handles assessment CRUD operations
   - Routes video processing requests to FastAPI
   - Database: PostgreSQL with Drizzle ORM
   
3. **FastAPI Backend** (Python)
   - Location: `backend/`
   - Handles video processing with MediaPipe
   - Contains all exercise-specific scoring modules
   - Returns raw metrics and scores

## Setup Instructions

### Prerequisites

- Node.js 18+
- Python 3.10+
- PostgreSQL 14+
- FFmpeg (for video processing)

### Step 1: Install Node Dependencies

```bash
npm install
```

This installs:
- Frontend dependencies (React, Tailwind, shadcn/ui)
- Backend dependencies (Express, Drizzle, Multer, Form-Data)

### Step 2: Set Up PostgreSQL Database

```bash
# Create database
createdb sensory_assess

# Set DATABASE_URL in your .env
export DATABASE_URL="postgresql://user:password@localhost:5432/sensory_assess"

# Create tables using Drizzle migrations
npm run db:push
```

### Step 3: Set Up Python Environment

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sensory_assess

# FastAPI Backend
FASTAPI_URL=http://localhost:8000

# Express Backend
EXPRESS_PORT=5000
NODE_ENV=development
```

## Running the System

### Terminal 1: FastAPI Backend

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

FastAPI will be available at: `http://localhost:8000`
- API endpoints: `/api/process-exercise/{exercise_id}`
- Health check: `/health`

### Terminal 2: Express.js Backend

```bash
npm run dev
```

Express will be available at: `http://localhost:5000`
- API endpoints: `/api/assessments`, `/api/process-exercise`
- Health check: `/api/backend-health`

### Terminal 3: React Frontend

The frontend is served automatically through Vite during development.
Access at: `http://localhost:5173`

## API Contract

### Upload and Process Exercise Video

**Endpoint:** `POST /api/process-exercise`

**Request:**
```
Content-Type: multipart/form-data

Parameters:
- exerciseId: string (e.g., "prone_extension", "one_leg_right_open")
- ageGroup: string (e.g., "6 years", "7 years")
- frontVideo?: File (for exercises requiring front view)
- sideVideo?: File (for exercises requiring side view)
```

**Response:**
```json
{
  "success": boolean,
  "exerciseId": string,
  "rawMetrics": {
    "metric_name": number,
    ...
  },
  "scores": {
    "component_name_score": number,
    ...
  },
  "totalScore": number,
  "maxScore": number,
  "interpretation": string
}
```

### Exercise Video Requirements

| Exercise | Front | Side | Notes |
|----------|-------|------|-------|
| Prone Extension | No | Yes | Side view shows extension angles |
| Supine Flexion | No | Yes | Side view shows flexion angles |
| One Leg Standing (L/R, EO/EC) | Yes | Yes | Front=ML sway, Side=AP sway + toe touches |
| Tandem Walking (EO/EC) | Yes | Yes | Front=ML sway, Side=AP sway + step gap |
| Jumping Jacks | Yes | Yes | Front=arm angles, Side=jump height |

## Scoring System

Each exercise has an exercise-specific scoring module in `backend/scoring/`:

- **math_prone_extension.py** - Max score: 35-36 (age-dependent)
- **math_supine_flexion.py** - Max score: 34-35 (age-dependent)
- **math_ols_eo.py** - Max score: 34 (Eyes Open)
- **math_ols_ec.py** - Max score: 34 (Eyes Closed)
- **math_tandem_walking_eo.py** - Max score: 34-37 (age-dependent)
- **math_tandem_walking_ec.py** - Max score: 34-37 (age-dependent)
- **math_jumping_jacks.py** - Max score: 35-36 (age-dependent)
- **math_total_assessment.py** - Aggregates all exercise scores with z-score calculation

### Scoring Pipeline

```
Video Input
    ↓
[FastAPI Backend]
    ↓
extract_*_metrics() - Extract raw pose metrics
    ↓
score_*() - Apply age-specific scoring bins
    ↓
Return: {
  rawMetrics: {...},  // Raw MediaPipe measurements
  scores: {...},      // Individual component scores
  totalScore: ...,    // Total for this exercise
  maxScore: ...,      // Maximum possible score
  interpretation: ...  // Text interpretation
}
```

## Frontend Components

### DualVideoExerciseCard.tsx

Used for exercises requiring both front and side views:
- One Leg Standing (all variants)
- Tandem Walking (all variants)
- Jumping Jacks

Features:
- Dual video upload (front + side)
- Video preview with playback
- Trim functionality for each video
- Process button (enabled when both videos are ready)
- Results display with scores and interpretation

### ExerciseCard.tsx

Used for single-view exercises:
- Prone Extension
- Supine Flexion

Features:
- Single video upload
- Video preview with playback
- Trim functionality
- Results display

### Assessment Page

Displays:
- Patient demographic information
- Exercise results with scores
- Overall assessment summary
- Download PDF report functionality

## Testing

### Run Integration Tests

```bash
# Terminal that has npm environment available
npx ts-node test-integration.ts
```

This script tests:
1. FastAPI health check
2. Express health check
3. Video processing for each exercise type
4. Database connectivity
5. Assessment creation and retrieval

### Manual Testing

1. **Open Frontend:** `http://localhost:5173`
2. **Fill Demographic Form** - Provide child's information
3. **Select Age Group** - Choose 6 or 7 years
4. **Upload Videos** - For each exercise:
   - Click on exercise card
   - Upload video(s) - front-side pair or single video
   - Trim if needed to focus on the exercise
   - Click "Process Exercise"
5. **View Results** - See scores and interpretation
6. **Download Report** - Generate PDF with all results

## Troubleshooting

### FastAPI Backend Not Responding

```bash
# Check if port 8000 is in use
netstat -an | grep 8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Check logs for MediaPipe import errors
# Install required: pip install mediapipe==0.10.14
```

### Database Connection Error

```bash
# Verify PostgreSQL is running
psql -U postgres

# Check DATABASE_URL is correct
echo $DATABASE_URL

# Recreate tables
npm run db:push
```

### Video Upload Fails

```bash
# Check uploads directory has correct permissions
ls -la uploads/  # macOS/Linux
dir uploads  # Windows

# Ensure video file is valid MP4/MOV
file test-video.mp4
```

### Express Routes Not Working

```bash
# Verify multer configuration
# Check that express package is installed
npm list express multer

# Check that server is running on correct port
curl http://localhost:5000/health
```

## Database Schema

The PostgreSQL database contains the following main tables:

### assessments table
```sql
- id (primary key)
- demographic (jsonb)
- birthMedical (jsonb)
- physicalParameters (jsonb)
- educationalInfo (jsonb)
- caregiverInfo (jsonb)
- therapistInfo (jsonb)
- ageGroup (text)
- exercises (jsonb) -- Array of exercise results
- status (text) -- "draft", "in_progress", "completed"
- createdAt (timestamp)
- completedAt (timestamp)
```

Each exercise entry in the `exercises` array contains:
```json
{
  "exerciseId": "...",
  "status": "completed",
  "frontVideo": { "status": "ready", "videoUrl": "..." },
  "sideVideo": { "status": "ready", "videoUrl": "..." },
  "result": {
    "rawMetrics": {...},
    "scores": {...},
    "totalScore": ...,
    "maxScore": ...,
    "interpretation": "..."
  }
}
```

## Performance Optimization

### Video Processing

- MediaPipe uses GPU acceleration when available (CUDA/Metal)
- Frame processing is batched for efficiency
- Rolling median smoothing reduces noise
- Confidence threshold filtering (0.6) reduces false detections

### Database

- Drizzle ORM provides type-safe queries
- JSONB columns support complex nested data
- Indexes on commonly queried fields
- Connection pooling via node-postgres

### Frontend

- React Query for automatic caching
- Code splitting via Vite
- Virtual scrolling for exercise lists
- Lazy loading video elements

## Debugging

### Enable Verbose Logging

**Express.js:**
```typescript
import debug from "debug";
const log = debug("app:*");
```

**FastAPI:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Network Traffic

Use browser DevTools → Network tab to inspect:
- `/api/process-exercise` requests and responses
- Video file uploads
- Assessment API calls

### MediaPipe Debugging

```python
# In processors, add visualization:
import cv2
cv2.imshow("Pose Detection", frame)
cv2.waitKey(1)
```

## Deployment

### Production Build

```bash
# Build frontend
npm run build

# This creates optimized bundles in dist/
```

### Environment Configuration

Update .env for production:
```env
NODE_ENV=production
DATABASE_URL=postgresql://prod_user:prod_pass@prod_host/sensory_assess
FASTAPI_URL=https://api.sensoryassess.com
```

### Docker Deployment (Optional)

See `Dockerfile` for containerized deployment instructions.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review browser console errors (F12)
3. Check server logs in terminal
4. Run integration tests to identify component failures

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Port 5173)                │
│  ┌─────────────┐  ┌──────────────────────┐  ┌────────────┐  │
│  │  Assessment │  │ DualVideoExerciseCard│  │  Results   │  │
│  │    Page     │  │       Component      │  │   Page     │  │
│  └─────────────┘  └──────────────────────┘  └────────────┘  │
│          ↓                  ↓                      ↓          │
└──────────┼──────────────────┼──────────────────────┼─────────┘
           │                  │                      │
           │ Video Files + FormData                 │
           │                                        │
┌──────────▼──────────────────────────────────────┐ │
│ Express.js Backend (Port 5000)                  │ │
│ ┌────────────────────────────────────────────┐ │ │
│ │ POST /api/process-exercise                 │ │ │
│ │  - Accept FormData (video files)           │ │ │
│ │  - Forward to FastAPI                      │ │ │
│ │  - Return processed results                │ │ │
│ └────────────────────────────────────────────┘ │ │
│ ┌────────────────────────────────────────────┐ │ │
│ │ CRUD Routes /api/assessments               │ │ │
│ │  - Create: POST                            │ │ │
│ │  - Read: GET                               │ │ │
│ │  - Update: PATCH                           │ │ │
│ │  - Delete: DELETE                          │ │ │
│ └────────────────────────────────────────────┘ │ │
└────┬─────────────────────┬────────────────────┘ │
     │                     │                      │
     │ PostgreSQL          │ Video Files          │
     │                     │                      │
┌────▼───────────────┐   ┌─▼──────────────────────────────────┐
│PostgreSQL Database │   │FastAPI Backend (Port 8000)         │
│                    │   │┌────────────────────────────────────┤
│ assessments table  │   ││/api/process-exercise/{exercise_id}│
│                    │   ││ - Process video with MediaPipe    │
│                    │   ││ - Apply exercise-specific scoring │
│                    │   ││ - Return detailed results         │
│                    │   │└────────────────────────────────────┤
│                    │   │┌────────────────────────────────────┤
└────────────────────┘   ││scoring/ modules:                   │
                         ││ - math_prone_extension.py         │
                         ││ - math_ols_eo.py, math_ols_ec.py  │
                         ││ - math_tandem_walking_*.py         │
                         ││ - math_jumping_jacks.py           │
                         ││ +5 more for each exercise         │
                         │└────────────────────────────────────┤
                         └────────────────────────────────────┘
```

This integration connects:
- Video uploads through Express (using Multer)
- Processing through FastAPI (using MediaPipe)
- Results storage in PostgreSQL (using Drizzle ORM)
- Display in React frontend

All 9 exercises with 5 different base types (Prone, Supine, OLS, Tandem, JJ) are now fully integrated!
