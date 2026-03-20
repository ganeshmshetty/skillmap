from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai.embedder import anchor_to_onet
from ai.extractor import extract_jd_skills, extract_resume_skills
from ai.gap_analyzer import compute_gap_vector
from ai.parser import extract_text

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
        resume_text = extract_text(resume_bytes, resume_filename)
        jd_text = extract_text(jd_bytes, jd_filename)

        resume_skills = anchor_to_onet(extract_resume_skills(resume_text))
        jd_skills = anchor_to_onet(extract_jd_skills(jd_text))
        gap_vector = compute_gap_vector(resume_skills, jd_skills)

        # Placeholder pathway until DAG engine is wired.
        pathway_nodes = []
        reasoning_traces = []
        for idx, gap in enumerate(gap_vector[:10], start=1):
            module_id = f"placeholder_{idx:03d}"
            trace_id = f"trace_{idx:03d}"
            pathway_nodes.append(
                {
                    "module_id": module_id,
                    "title": f"Close gap: {gap.skill_name}",
                    "phase": "Foundation" if idx <= 3 else "Core",
                    "skills_targeted": [gap.onet_id] if gap.onet_id else [],
                    "reasoning_ref": trace_id,
                }
            )
            reasoning_traces.append(
                {
                    "id": trace_id,
                    "module_id": module_id,
                    "text": f"Recommended to reduce the gap in {gap.skill_name}.",
                    "confidence": min(0.99, max(0.6, float(gap.importance))),
                }
            )

        required_skills = [s for s in jd_skills if s.is_required]
        covered_required = 0
        resume_onet = {s.onet_id for s in resume_skills if s.onet_id}
        for req in required_skills:
            if req.onet_id and req.onet_id in resume_onet:
                covered_required += 1

        coverage = covered_required / len(required_skills) if required_skills else 1.0
        estimated_minutes = len(pathway_nodes) * 120

        _set_job(
            job_id,
            {
                "job_id": job_id,
                "status": "completed",
                "updated_at": _utc_now(),
                "result": {
                    "summary": {
                        "coverage_score": round(coverage, 4),
                        "redundancy_reduction": 0.0,
                        "estimated_total_minutes": estimated_minutes,
                    },
                    "pathway": {
                        "nodes": pathway_nodes,
                        "edges": [],
                    },
                    "reasoning_traces": reasoning_traces,
                },
            },
        )
    except Exception as exc:
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
