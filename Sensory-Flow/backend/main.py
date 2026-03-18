"""
FastAPI Backend for SensoryAssess Pro
Handles video uploads and exercise scoring using MediaPipe
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import tempfile
import shutil
import uuid

# Import exercise processors - Colab-exact versions (match external colab folders)
from backend.processors.prone_extension import process_prone_extension
from backend.processors.supine_flexion import process_supine_flexion
from backend.processors.one_leg_standing_colab_exact import process_one_leg_standing
from backend.processors.tandem_walking_colab_exact_v2 import process_tandem_walking
from backend.processors.jumping_jacks_colab_exact_v2 import process_jumping_jacks

from backend import db
from backend.scoring import math_total_assessment


app = FastAPI(
    title="SensoryAssess Pro API",
    description="Video processing and scoring API for pediatric motor assessments",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


# Store for uploaded videos (in production, use proper storage)
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "sensory_assess_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Map per-request exercise identifiers used by the API to the
# canonical keys expected by math_total_assessment.EXERCISE_KEYS.
EXERCISE_ID_TO_ASSESSMENT_KEY: Dict[str, str] = {
    # Core posture exercises
    "prone_extension": "prone_extension",
    "supine_flexion": "supine_flexion",
    # One-leg standing (OLS)
    # Convention: one_leg_<left/right>_<open/closed>
    "one_leg_left_open": "ols_ll_eo",
    "one_leg_left_close": "ols_ll_ec",
    "one_leg_right_open": "ols_rl_eo",
    "one_leg_right_close": "ols_rl_ec",
    # Tandem walking
    # Convention: tandem_walking_<open/closed>
    "tandem_walking_open": "tandem_eo",
    "tandem_walking_close": "tandem_ec",
    # Jumping jacks
    "jumping_jacks": "jumping_jacks",
}


def _map_exercise_scores_for_assessment(
    by_exercise_id: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Convert scores keyed by API exercise_id into the canonical
    keys expected by math_total_assessment.score_assessment.
    """
    mapped: Dict[str, Dict[str, Any]] = {}
    for exercise_id, payload in by_exercise_id.items():
        key = EXERCISE_ID_TO_ASSESSMENT_KEY.get(exercise_id)
        if not key:
            # Unknown or non-assessment exercise; ignore for totals
            continue
        mapped[key] = {"total_score": payload.get("total_score")}
    return mapped


class ProcessingResult(BaseModel):
    success: bool
    exerciseId: str
    rawMetrics: Dict[str, Any]
    scores: Dict[str, int]
    totalScore: int
    maxScore: int
    interpretation: str
    error: Optional[str] = None


class VideoUploadResponse(BaseModel):
    success: bool
    videoId: str
    filename: str
    path: str


class AssessmentCreateRequest(BaseModel):
    age_years: int


class AssessmentCreateResponse(BaseModel):
    success: bool
    assessmentId: str
    ageYears: int


class AssessmentSummaryResponse(BaseModel):
    success: bool
    assessmentId: str
    ageYears: int
    totalScore: Optional[float]
    mean: Optional[float]
    sd: Optional[float]
    zScore: Optional[float]
    interpretation: Optional[str]
    breakdown: Dict[str, Any]


@app.get("/")
async def root():
    return {"message": "SensoryAssess Pro API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/assessments", response_model=AssessmentCreateResponse)
async def create_assessment(req: AssessmentCreateRequest):
    """Create a new assessment record so per-exercise scores can be persisted."""
    assessment_id = db.create_assessment(req.age_years)
    return AssessmentCreateResponse(
        success=True,
        assessmentId=assessment_id,
        ageYears=req.age_years,
    )


@app.get("/api/assessments/{assessment_id}/summary", response_model=AssessmentSummaryResponse)
async def get_assessment_summary(assessment_id: str):
    """
    Aggregate all stored per-exercise scores for a given assessment and
    compute the Total Assessment Score + z-score using age norms.
    """
    age_years = db.get_assessment_age(assessment_id)
    if age_years is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    raw_scores = db.load_exercise_totals_for_assessment(assessment_id)
    exercise_scores = _map_exercise_scores_for_assessment(raw_scores)

    result = math_total_assessment.score_assessment(exercise_scores, age_years=age_years)

    return AssessmentSummaryResponse(
        success=True,
        assessmentId=assessment_id,
        ageYears=result["age_years"],
        totalScore=result["total_score"],
        mean=result["mean"],
        sd=result["sd"],
        zScore=result["z_score"],
        interpretation=result["interpretation"],
        breakdown=result["breakdown"],
    )


@app.post("/api/upload-video", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    exerciseId: str = Form(...),
    viewType: str = Form(...)  # "front" or "side"
):
    """Upload a video file for processing"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Generate unique ID
        video_id = str(uuid.uuid4())
        
        # Create exercise-specific directory
        exercise_dir = os.path.join(UPLOAD_DIR, exerciseId, video_id)
        os.makedirs(exercise_dir, exist_ok=True)
        
        # Save file
        filename = f"{viewType}_{file.filename}"
        file_path = os.path.join(exercise_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return VideoUploadResponse(
            success=True,
            videoId=video_id,
            filename=filename,
            path=file_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process-exercise/{exercise_id}", response_model=ProcessingResult)
async def process_exercise(
    exercise_id: str,
    age_group: str = Form(...),
    front_video_path: Optional[str] = Form(None),
    side_video_path: Optional[str] = Form(None),
    assessmentId: Optional[str] = Form(None),
):
    """Process uploaded videos and calculate exercise scores"""
    try:
        # Determine age in years
        age_years = 6 if "6" in age_group else 7
        
        # Route to appropriate processor
        if exercise_id == "prone_extension":
            if not side_video_path:
                raise HTTPException(status_code=400, detail="Side video required for prone extension")
            result = process_prone_extension(side_video_path, age_years)
            
        elif exercise_id == "supine_flexion":
            if not side_video_path:
                raise HTTPException(status_code=400, detail="Side video required for supine flexion")
            result = process_supine_flexion(side_video_path, age_years)
            
        elif exercise_id.startswith("one_leg"):
            if not front_video_path:
                raise HTTPException(status_code=400, detail="Front video required for one leg standing")
            # Determine which leg and eyes condition
            raised_leg = "R" if "right" in exercise_id else "L"
            eyes_open = "open" in exercise_id
            result = process_one_leg_standing(front_video_path, side_video_path, age_years, eyes_open, raised_leg)
            
        elif exercise_id.startswith("tandem_walking"):
            if not front_video_path:
                raise HTTPException(status_code=400, detail="Front video required for tandem walking")
            eyes_open = "open" in exercise_id
            result = process_tandem_walking(front_video_path, side_video_path, age_years, eyes_open)
            
        elif exercise_id == "jumping_jacks":
            if not front_video_path:
                raise HTTPException(status_code=400, detail="Video required for jumping jacks")
            result = process_jumping_jacks(front_video_path, age_years)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown exercise type: {exercise_id}")

        # Optionally persist this exercise result under an assessment ID
        if assessmentId:
            try:
                db.save_exercise_result(assessmentId, exercise_id, {
                    "exerciseId": exercise_id,
                    **result,
                })
            except Exception:
                # Persistence errors should not break scoring API
                pass

        return ProcessingResult(
            success=True,
            exerciseId=exercise_id,
            **result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return ProcessingResult(
            success=False,
            exerciseId=exercise_id,
            rawMetrics={},
            scores={},
            totalScore=0,
            maxScore=0,
            interpretation="Error",
            error=str(e)
        )


@app.post("/api/process-exercise-files/{exercise_id}")
async def process_exercise_files(
    exercise_id: str,
    age_group: str = Form(...),
    front_video: Optional[UploadFile] = File(None),
    side_video: Optional[UploadFile] = File(None),
    assessmentId: Optional[str] = Form(None),
):
    """Upload and process videos in a single request"""
    front_path = None
    side_path = None
    
    try:
        # Save uploaded files temporarily
        temp_dir = os.path.join(UPLOAD_DIR, f"temp_{uuid.uuid4()}")
        os.makedirs(temp_dir, exist_ok=True)
        
        if front_video:
            front_path = os.path.join(temp_dir, f"front_{front_video.filename}")
            with open(front_path, "wb") as f:
                shutil.copyfileobj(front_video.file, f)
        
        if side_video:
            side_path = os.path.join(temp_dir, f"side_{side_video.filename}")
            with open(side_path, "wb") as f:
                shutil.copyfileobj(side_video.file, f)
        
        # Determine age in years
        age_years = 6 if "6" in age_group else 7
        
        # Route to appropriate processor
        if exercise_id == "prone_extension":
            if not side_path:
                raise HTTPException(status_code=400, detail="Side video required for prone extension")
            result = process_prone_extension(side_path, age_years)
            
        elif exercise_id == "supine_flexion":
            if not side_path:
                raise HTTPException(status_code=400, detail="Side video required for supine flexion")
            result = process_supine_flexion(side_path, age_years)
            
        elif exercise_id.startswith("one_leg"):
            if not front_path or not side_path:
                raise HTTPException(status_code=400, detail="Both front and side videos required for one leg standing")
            raised_leg = "R" if "right" in exercise_id else "L"
            eyes_open = "open" in exercise_id
            result = process_one_leg_standing(front_path, side_path, age_years, eyes_open, raised_leg)
            
        elif exercise_id.startswith("tandem_walking"):
            if not front_path or not side_path:
                raise HTTPException(status_code=400, detail="Both front and side videos required for tandem walking")
            eyes_open = "open" in exercise_id
            result = process_tandem_walking(front_path, side_path, age_years, eyes_open)
            
        elif exercise_id == "jumping_jacks":
            if not front_path:
                raise HTTPException(status_code=400, detail="Front video required for jumping jacks")
            result = process_jumping_jacks(front_path, side_path, age_years)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown exercise type: {exercise_id}")

        # Optionally persist this exercise result under an assessment ID
        if assessmentId:
            try:
                db.save_exercise_result(assessmentId, exercise_id, {
                    "exerciseId": exercise_id,
                    **result,
                })
            except Exception:
                pass

        return {
            "success": True,
            "exerciseId": exercise_id,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "exerciseId": exercise_id,
            "error": str(e),
            "rawMetrics": {},
            "scores": {},
            "totalScore": 0,
            "maxScore": 0,
            "interpretation": f"Error: {e}",
        }
    finally:
        # Cleanup temp files
        if front_path and os.path.exists(front_path):
            os.unlink(front_path)
        if side_path and os.path.exists(side_path):
            os.unlink(side_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
