import os
import sqlite3
import uuid
import json
from typing import Dict, Any, Optional


DB_PATH = os.path.join(os.path.dirname(__file__), "sensory_assess.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create SQLite tables if they do not already exist."""
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS assessments (
            id TEXT PRIMARY KEY,
            age_years INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS exercise_results (
            id TEXT PRIMARY KEY,
            assessment_id TEXT NOT NULL,
            exercise_id TEXT NOT NULL,
            total_score REAL,
            max_score REAL,
            interpretation TEXT,
            raw_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assessment_id) REFERENCES assessments(id)
        )
        """
    )

    conn.commit()
    conn.close()


def create_assessment(age_years: int) -> str:
    """Insert a new assessment row and return its ID."""
    assessment_id = str(uuid.uuid4())
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO assessments (id, age_years) VALUES (?, ?)",
        (assessment_id, int(age_years)),
    )
    conn.commit()
    conn.close()
    return assessment_id


def get_assessment_age(assessment_id: str) -> Optional[int]:
    """Return age_years for a given assessment, or None if missing."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT age_years FROM assessments WHERE id = ?",
        (assessment_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    try:
        return int(row["age_years"])
    except Exception:
        return None


def save_exercise_result(
    assessment_id: str,
    exercise_id: str,
    result: Dict[str, Any],
) -> None:
    """
    Persist a single exercise processing result for an assessment.

    Expects `result` in the same structure returned by the FastAPI
    processing endpoints, i.e. containing at least:
      - totalScore
      - maxScore
      - interpretation
    """
    total_score = result.get("totalScore")
    max_score = result.get("maxScore")
    interpretation = result.get("interpretation")

    conn = _get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO exercise_results (
            id,
            assessment_id,
            exercise_id,
            total_score,
            max_score,
            interpretation,
            raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            assessment_id,
            exercise_id,
            total_score,
            max_score,
            interpretation,
            json.dumps(result),
        ),
    )

    conn.commit()
    conn.close()


def load_exercise_totals_for_assessment(
    assessment_id: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Return a mapping of exercise_id -> {"total_score": float or None}
    for all results that belong to a given assessment.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT exercise_id, total_score
        FROM exercise_results
        WHERE assessment_id = ?
        """,
        (assessment_id,),
    )
    rows = cur.fetchall()
    conn.close()

    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ex_id = row["exercise_id"]
        out[ex_id] = {"total_score": row["total_score"]}

    return out

