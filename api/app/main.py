from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4
import logging

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        if job_id in JOBS:
            JOBS[job_id].update(payload)
        else:
            JOBS[job_id] = payload


def _get_job(job_id: str) -> dict | None:
    with _JOBS_LOCK:
        return JOBS.get(job_id)


def _emit_event(job_id: str, stage: str, detail: str, data: dict | None = None) -> None:
    """Append a structured trace event to the job's live event log."""
    with _JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return
        if "events" not in job:
            job["events"] = []
        job["events"].append({
            "ts": _utc_now(),
            "stage": stage,
            "detail": detail,
            "data": data or {},
        })

def _run_analysis(job_id: str, resume_bytes: bytes, resume_filename: str, jd_bytes: bytes, jd_filename: str) -> None:
    _set_job(
        job_id,
        {
            "status": "processing",
            "message": "Starting analysis job",
            "updated_at": _utc_now(),
        },
    )

    try:
        logger.info(f"[{job_id}] Started analysis job")
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

        logger.info(f"[{job_id}] Extracting text from files")
        _set_job(job_id, {"message": "Extracting text from files", "updated_at": _utc_now()})
        resume_text = extract_text(resume_bytes, resume_filename)
        jd_text = extract_text(jd_bytes, jd_filename)

        if not resume_text.strip():
            raise RuntimeError("Could not extract text from resume. If this is a scanned PDF, please use an OCR-converted version.")
        if not jd_text.strip():
            raise RuntimeError("Could not extract text from job description. The file appears to be empty.")

        resume_word_count = len(resume_text.split())
        jd_word_count = len(jd_text.split())
        _emit_event(job_id, "extract", f"Extracted {resume_word_count:,} words from {resume_filename}",
                    {"file": resume_filename, "words": resume_word_count})
        _emit_event(job_id, "extract", f"Extracted {jd_word_count:,} words from {jd_filename}",
                    {"file": jd_filename, "words": jd_word_count})

        logger.info(f"[{job_id}] Extracting skills and mapping to ONET")
        _set_job(job_id, {"message": "Extracting skills and mapping to ONET", "updated_at": _utc_now()})

        # --- Resume skills: extract then anchor with per-skill event callback ---
        resume_skills_raw = extract_resume_skills(resume_text)
        _emit_event(job_id, "skills", f"LLM extracted {len(resume_skills_raw)} resume skills", {
            "count": len(resume_skills_raw),
            "skills": [{"name": s.name, "level": s.proficiency_level, "years": s.years_exp} for s in resume_skills_raw]
        })

        anchor_events: list[dict] = []
        def _resume_anchor_cb(skill_name: str, onet_id: str | None, method: str, score: float):
            icons = {"exact_title": "●", "alias": "⬡", "embedding": "◈", "unmatched": "⚠", "substring": "~"}
            icon = icons.get(method, "?")
            label = onet_id or "no match"
            anchor_events.append({"skill": skill_name, "onet_id": onet_id, "method": method, "score": round(score, 3)})
            _emit_event(job_id, "anchor",
                        f"{icon} {skill_name!r} → {label} ({method}, {score:.0%})",
                        {"skill": skill_name, "onet_id": onet_id, "method": method, "score": round(score, 3), "side": "resume"})

        resume_skills = anchor_to_onet(resume_skills_raw, on_match=_resume_anchor_cb)

        # --- JD skills: extract then anchor ---
        detected_domain, jd_skills_raw = extract_jd_skills(jd_text)
        _emit_event(job_id, "skills", f"LLM extracted {len(jd_skills_raw)} JD skills · domain: {detected_domain}", {
            "count": len(jd_skills_raw),
            "domain": detected_domain,
            "skills": [{"name": s.name, "level": s.required_level, "required": s.is_required} for s in jd_skills_raw]
        })

        def _jd_anchor_cb(skill_name: str, onet_id: str | None, method: str, score: float):
            icons = {"exact_title": "●", "alias": "⬡", "embedding": "◈", "unmatched": "⚠", "substring": "~"}
            icon = icons.get(method, "?")
            label = onet_id or "no match"
            _emit_event(job_id, "anchor",
                        f"{icon} {skill_name!r} → {label} ({method}, {score:.0%})",
                        {"skill": skill_name, "onet_id": onet_id, "method": method, "score": round(score, 3), "side": "jd"})

        jd_skills = anchor_to_onet(jd_skills_raw, on_match=_jd_anchor_cb)
        logger.info(f"[{job_id}] Detected domain: {detected_domain}")
        logger.info(f"[{job_id}] Extracted {len(resume_skills)} resume skills, {len(jd_skills)} JD skills")
        
        logger.info(f"[{job_id}] Computing gap vector")
        _set_job(job_id, {"message": "Computing skill gaps", "updated_at": _utc_now()})
        gap_vector = compute_gap_vector(resume_skills, jd_skills)
        logger.info(f"[{job_id}] Computed {len(gap_vector)} gaps")

        top_gaps = gap_vector[:5]
        _emit_event(job_id, "gap", f"Identified {len(gap_vector)} skill gaps · top: {top_gaps[0].skill_name} (score {top_gaps[0].gap_score:.2f})" if gap_vector else "No skill gaps found", {
            "total": len(gap_vector),
            "gaps": [{"skill": g.skill_name, "score": round(g.gap_score, 3), "current": g.current_level, "required": g.required_level} for g in top_gaps]
        })

        if CATALOG is None:
            raise RuntimeError(CATALOG_ERROR or "Course catalog is unavailable")

        logger.info(f"[{job_id}] Generating adaptive pathway")
        _set_job(job_id, {"message": "Generating adaptive learning pathway", "updated_at": _utc_now()})
        pathway = generate_adaptive_pathway(
            gap_vector, 
            CATALOG, 
            detected_domain=detected_domain,
            on_event=lambda stage, detail, data=None: _emit_event(job_id, stage, detail, data)
        )

        # Pathway summary event
        phase_counts = {p: len(ids) for p, ids in pathway.phases.items() if ids}
        _emit_event(job_id, "pathway", f"Built pathway: {len(pathway.nodes)} modules · {pathway.total_duration} min total", {
            "nodes": len(pathway.nodes),
            "duration_min": pathway.total_duration,
            "phases": phase_counts,
            "modules": [{"id": n.module_id, "title": n.title, "phase": n.phase, "duration": n.estimated_duration} for n in pathway.nodes]
        })

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
        # Static curriculum = every unique catalog module relevant to ANY required skill.
        # We deduplicate by module ID so "shared" modules aren't double-counted.
        # Adaptive pathway = only the modules actually needed for skill gaps.
        static_module_ids: set[str] = set()
        for s in required_skills:
            if s.onet_id:
                for m in CATALOG.modules_by_skill.get(s.onet_id, []):
                    static_module_ids.add(m.id)

        static_modules_count = len(static_module_ids)
        adaptive_count = len(pathway.nodes)

        if static_modules_count > 0 and adaptive_count < static_modules_count:
            redundancy_reduction = 1.0 - (adaptive_count / static_modules_count)
            redundancy_reduction = max(0.0, min(1.0, redundancy_reduction))  # clamp [0,1]
        elif static_modules_count > 0:
            redundancy_reduction = 0.0
        else:
            # No catalog matches — pathway is fully LLM-generated, no static baseline
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
            detected_domain=detected_domain,
            pathway=pathway,
            reasoning_traces=traces,
            coverage_score=round(coverage, 4),
            redundancy_reduction=round(redundancy_reduction, 4)
        )

        logger.info(f"[{job_id}] Analysis job completed successfully")

        _set_job(
            job_id,
            {
                "status": "completed",
                "message": "Analysis complete",
                "updated_at": _utc_now(),
                "result": result.model_dump(),
            },
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        logger.error(f"[{job_id}] Analysis job failed: {exc}")
        _set_job(
            job_id,
            {
                "status": "failed",
                "message": "Analysis failed",
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
def result(job_id: str, since: int = 0) -> JSONResponse:
    job = _get_job(job_id)
    if not job:
        return JSONResponse(status_code=200, content={"job_id": job_id, "status": "not_found"})
    # Return only new events since last poll to avoid re-sending
    all_events = job.get("events", [])
    response = {k: v for k, v in job.items() if k != "events"}
    response["events"] = all_events[since:]
    response["event_count"] = len(all_events)
    return JSONResponse(status_code=200, content=response)


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

