from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Heavy AI modules are imported lazily inside `_run_analysis` so the API
# can start for lightweight checks (e.g. /health) even if ML deps
# (spacy, sentence-transformers, etc.) are not installed in the env.
from app.services.catalog import CatalogValidationError, CourseCatalogService

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))

app = FastAPI(title="AI-Adaptive Onboarding Engine API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_response(code: str, message: str, details: dict, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


def _validate_upload(filename: str | None, file_bytes: bytes, field: str) -> JSONResponse | None:
    if not filename:
        return _error_response(
            code="missing_file",
            message="File is required",
            details={"field": field},
        )

    lower_name = filename.lower()
    if not any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return _error_response(
            code="invalid_file_type",
            message="Only PDF, DOCX, TXT are supported",
            details={"field": field},
        )

    if len(file_bytes) == 0:
        return _error_response(
            code="empty_file",
            message="Uploaded file is empty",
            details={"field": field},
        )

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return _error_response(
            code="file_too_large",
            message="Uploaded file exceeds size limit",
            details={"field": field, "max_bytes": MAX_UPLOAD_BYTES},
            status_code=413,
        )

    return None


JOBS: dict[str, dict] = {}
_JOBS_LOCK = Lock()

CATALOG: CourseCatalogService | None = None
CATALOG_ERROR: str | None = None
try:
    CATALOG = CourseCatalogService.from_env()
except CatalogValidationError as exc:
    CATALOG_ERROR = str(exc)


def _set_job(job_id: str, payload: dict) -> None:
    with _JOBS_LOCK:
        JOBS[job_id] = payload


def _get_job(job_id: str) -> dict | None:
    with _JOBS_LOCK:
        return JOBS.get(job_id)


def _run_analysis(job_id: str, resume_bytes: bytes, resume_filename: str, jd_bytes: bytes, jd_filename: str) -> None:
    _set_job(
        job_id,
        {
            "job_id": job_id,
            "status": "processing",
            "updated_at": _utc_now(),
        },
    )

    try:
        # Import heavy AI modules at runtime to avoid blocking server startup
        # when optional ML dependencies are not installed. If imports fail
        # the job will be marked as failed with a clear error.
        try:
            from ai.parser import extract_text
            from ai.extractor import extract_jd_skills, extract_resume_skills
            from ai.embedder import anchor_to_onet
            from ai.gap_analyzer import compute_gap_vector, generate_adaptive_pathway
            from ai.models import AnalysisResult
        except Exception as exc:
            raise RuntimeError(f"AI dependencies missing or failed to import: {exc}")

        resume_text = extract_text(resume_bytes, resume_filename)
        jd_text = extract_text(jd_bytes, jd_filename)

        resume_skills = anchor_to_onet(extract_resume_skills(resume_text))
        jd_skills = anchor_to_onet(extract_jd_skills(jd_text))
        print(f"DEBUG: Extracted {len(resume_skills)} resume skills, {len(jd_skills)} JD skills")
        
        gap_vector = compute_gap_vector(resume_skills, jd_skills)
        print(f"DEBUG: Computed {len(gap_vector)} gaps")

        if CATALOG is None:
            raise RuntimeError(CATALOG_ERROR or "Course catalog is unavailable")

        pathway = generate_adaptive_pathway(gap_vector, CATALOG)

        # Compute Metrics
        required_skills = [s for s in jd_skills if s.is_required]
        # Check coverage against gap vector (gaps imply missing)
        # Skills with gap score of 0 are covered.
        # But gap vector only contains gaps > 0.
        # So covered = total_required - len(gap_vector related to required)
        
        # Actually easier: check resume skills vs required (already done in compute_gap_vector usually but let's re-verify)
        # gap_vector has gaps.
        # coverage score = 1 - (sum of gap weights / sum of total weights) or simple count
        
        # Simple count heuristic:
        # Covered if delta is 0. compute_gap_vector returns ONLY items with delta > 0.
        # So items NOT in gap_vector are covered (or not required).
        gap_onet_ids = {g.onet_id for g in gap_vector if g.onet_id}
        total_required_count = len(required_skills)
        if total_required_count > 0:
            # skills in gap vector are "missing" or "partial"
            # let's count only fully missing for simplicity, or weighted
            # Hackathon simple metric:
            missing_count = sum(1 for s in required_skills if s.onet_id in gap_onet_ids)
            coverage = 1.0 - (missing_count / total_required_count)
        else:
            coverage = 1.0

        # Redundancy Reduction:
        # Static curriculum might be "all modules for all required skills"
        # Adaptive pathway is "only modules for gaps"
        # Let's estimate static count as sum of 'modules_for_skill' for all required skills
        # This is a bit heavy to compute perfectly, so let's use a heuristic:
        # Static = sum(len(CATALOG.modules_by_skill.get(s.onet_id, [])) for s in required_skills)
        # Adaptive = len(pathway.nodes)
        
        static_modules_count = 0
        for s in required_skills:
            if s.onet_id:
                static_modules_count += len(CATALOG.modules_by_skill.get(s.onet_id, []))
        
        if static_modules_count > 0:
            redundancy_reduction = 1.0 - (len(pathway.nodes) / static_modules_count)
            redundancy_reduction = max(0.0, redundancy_reduction) # clamp
        else:
            redundancy_reduction = 0.0

        # Collect reasoning traces from pathway nodes
        traces = []
        for node in pathway.nodes:
            if node.reasoning:
                traces.append(node.reasoning)

        result = AnalysisResult(
            resume_skills=resume_skills,
            jd_skills=jd_skills,
            gap_vector=gap_vector,
            pathway=pathway,
            reasoning_traces=traces,
            coverage_score=round(coverage, 2),
            redundancy_reduction=round(redundancy_reduction, 2)
        )

        _set_job(
            job_id,
            {
                "job_id": job_id,
                "status": "completed",
                "updated_at": _utc_now(),
                "result": result.model_dump(),
            },
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        _set_job(
            job_id,
            {
                "job_id": job_id,
                "status": "failed",
                "updated_at": _utc_now(),
                "error": {
                    "code": "analysis_failed",
                    "message": "Failed to process analysis job",
                    "details": {"reason": str(exc)},
                },
            },
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/catalog/health")
def catalog_health() -> JSONResponse:
    if CATALOG is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "error": CATALOG_ERROR or "unknown"},
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "modules": len(CATALOG.modules),
            "skills_indexed": len(CATALOG.modules_by_skill),
        },
    )


@app.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    jd: UploadFile = File(...),
) -> JSONResponse:
    resume_bytes = await resume.read()
    jd_bytes = await jd.read()

    validation_error = _validate_upload(resume.filename, resume_bytes, "resume")
    if validation_error:
        return validation_error

    validation_error = _validate_upload(jd.filename, jd_bytes, "jd")
    if validation_error:
        return validation_error

    job_id = str(uuid4())
    _set_job(
        job_id,
        {
            "job_id": job_id,
            "status": "queued",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        },
    )

    background_tasks.add_task(
        _run_analysis,
        job_id,
        resume_bytes,
        resume.filename or "resume.txt",
        jd_bytes,
        jd.filename or "jd.txt",
    )

    return JSONResponse(status_code=200, content={"job_id": job_id, "status": "queued"})


@app.get("/result/{job_id}")
def result(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    if not job:
        return JSONResponse(status_code=200, content={"job_id": job_id, "status": "not_found"})
    return JSONResponse(status_code=200, content=job)


@app.get("/metrics")
def metrics() -> JSONResponse:
    """Aggregate evaluation metrics across all completed jobs in the current session."""
    with _JOBS_LOCK:
        all_jobs = list(JOBS.values())

    completed = [j for j in all_jobs if j.get("status") == "completed"]
    total = len(all_jobs)
    n = len(completed)

    if n == 0:
        return JSONResponse(
            status_code=200,
            content={
                "total_jobs": total,
                "total_jobs_completed": 0,
                "avg_coverage_score": None,
                "avg_redundancy_reduction": None,
                "avg_estimated_minutes": None,
                "message": "No completed jobs yet.",
            },
        )

    coverage_scores = [
        j["result"].get("coverage_score", 0) for j in completed if "result" in j
    ]
    redundancy_vals = [
        j["result"].get("redundancy_reduction", 0) for j in completed if "result" in j
    ]
    minutes_vals = [
        j["result"]["pathway"].get("total_duration", 0) for j in completed if "result" in j
    ]

    return JSONResponse(
        status_code=200,
        content={
            "total_jobs": total,
            "total_jobs_completed": n,
            "avg_coverage_score": round(sum(coverage_scores) / len(coverage_scores), 4) if coverage_scores else None,
            "avg_redundancy_reduction": round(sum(redundancy_vals) / len(redundancy_vals), 4) if redundancy_vals else None,
            "avg_estimated_minutes": round(sum(minutes_vals) / len(minutes_vals)) if minutes_vals else None,
        },
    )

