from uuid import uuid4

from fastapi import APIRouter, UploadFile

from app.models import AnalyzeResponse, HealthResponse

router = APIRouter()

# In-memory store for initial bootstrap; replace with Redis job state in Phase 1.
JOBS: dict[str, dict] = {}


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="resume-parser-api")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(resume: UploadFile, jd: UploadFile) -> AnalyzeResponse:
    job_id = str(uuid4())
    JOBS[job_id] = {
        "status": "queued",
        "resume_filename": resume.filename,
        "jd_filename": jd.filename,
    }
    return AnalyzeResponse(job_id=job_id, status="queued")


@router.get("/result/{job_id}")
def get_result(job_id: str) -> dict:
    return JOBS.get(job_id, {"job_id": job_id, "status": "not_found"})
