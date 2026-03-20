"""
Member A's public interface.
Member B calls: from ai import analyze
"""
from .gap_analyzer import compute_gap_vector
from .models import AnalysisResult


def analyze(
    resume_text: str,
    jd_text: str,
    ordered_modules: list[dict] = None,   # injected by Member B after DAG
    catalog: list[dict] = None
) -> dict:
    """
    Main entry point for the AI pipeline.
    
    Phase 1 (standalone): Call with just resume_text + jd_text → returns gap_vector.
    Phase 2 (integrated): Pass in ordered_modules + catalog → returns full result with traces.
    
    NOTE: spacy, sentence-transformers, and torch require Python 3.12 or earlier.
    Python 3.14 support is not yet available in the ML ecosystem.
    """
    # Lazy imports to defer dependency loading
    from .extractor import extract_resume_skills, extract_jd_skills
    from .embedder import anchor_to_onet
    from .reasoning_tracer import generate_traces

    # Step 1: Extract
    resume_skills = extract_resume_skills(resume_text)
    jd_skills = extract_jd_skills(jd_text)

    # Step 2: Anchor to O*NET
    resume_skills = anchor_to_onet(resume_skills)
    jd_skills = anchor_to_onet(jd_skills)

    # Step 3: Gap analysis
    gap_vector = compute_gap_vector(resume_skills, jd_skills)

    # Step 4: Reasoning traces (only if DAG output is available)
    traces = []
    coverage_score = 0.0
    redundancy_reduction = 0.0

    if ordered_modules and catalog:
        traces = generate_traces(ordered_modules, gap_vector, catalog)

        # Metrics
        jd_skill_ids = {s.onet_id or s.name.lower() for s in jd_skills if s.is_required}
        covered = sum(
            1 for m in ordered_modules
            for sid in m.get("skill_ids", [])
            if sid in jd_skill_ids
        )
        coverage_score = covered / len(jd_skill_ids) if jd_skill_ids else 0.0
        redundancy_reduction = 1.0 - (len([m for m in ordered_modules if m.get("is_prerequisite")]) / max(1, len(ordered_modules)))

    return {
        "resume_skills": [s.dict() for s in resume_skills],
        "jd_skills": [s.dict() for s in jd_skills],
        "gap_vector": [g.dict() for g in gap_vector],
        "reasoning_traces": [t.dict() for t in traces],
        "coverage_score": coverage_score,
        "redundancy_reduction": redundancy_reduction,
    }


__all__ = [
    "analyze",
    "AnalysisResult",
]