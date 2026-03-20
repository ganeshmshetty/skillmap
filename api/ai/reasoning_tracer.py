import os

from google import genai
from .prompts import REASONING_TRACE_PROMPT
from .models import GapItem, ReasoningTrace
from .hallucination_guard import filter_traces

_client = None
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

LEVEL_LABELS = {0: "no experience", 1: "junior", 2: "mid-level", 3: "senior"}


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=api_key)
    return _client

def generate_traces(
    ordered_modules: list[dict],   # from Member B's DAG engine
    gap_vector: list[GapItem],
    catalog: list[dict]
) -> list[ReasoningTrace]:
    """
    Generate a reasoning trace for each module in the ordered pathway.
    LLM only writes justification — never names modules or invents content.
    """
    gap_map = {g.onet_id or g.skill_name.lower(): g for g in gap_vector}
    traces = []

    for i, module in enumerate(ordered_modules):
        # Find the primary gap this module closes
        primary_gap = None
        for skill_id in module.get("skill_ids", []):
            if skill_id in gap_map:
                primary_gap = gap_map[skill_id]
                break

        if not primary_gap:
            # Module is a prerequisite, use generic gap context
            gap_description = f"prerequisite for {module.get('title', 'next module')}"
            current_level_label = "foundational"
            required_level_label = "intermediate"
        else:
            gap_description = primary_gap.skill_name
            current_level_label = LEVEL_LABELS.get(primary_gap.current_level, "unknown")
            required_level_label = LEVEL_LABELS.get(primary_gap.required_level, "unknown")

        prereq_chain = [
            catalog_lookup(pid, catalog)
            for pid in module.get("prerequisites", [])[:3]  # cap at 3 for prompt brevity
        ]

        prompt = REASONING_TRACE_PROMPT.format(
            module_title=module["title"],
            gap_description=gap_description,
            current_level=current_level_label,
            required_level=required_level_label,
            prereq_chain=", ".join(prereq_chain) if prereq_chain else "none"
        )

        try:
            response = _get_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            justification = (response.text or "").strip()
            if not justification:
                raise ValueError("Empty Gemini response")
        except Exception as e:
            justification = f"This module addresses the {gap_description} requirement."

        traces.append(ReasoningTrace(
            module_id=module["id"],
            module_title=module["title"],
            gap_closed=gap_description,
            justification=justification,
            confidence=0.9 if primary_gap else 0.7,
            prerequisite_chain=prereq_chain
        ))

    # Final hallucination guard pass
    valid_ids = {m["id"] for m in catalog}
    traces = [t for t in traces if t.module_id in valid_ids]
    return traces

def catalog_lookup(module_id: str, catalog: list[dict]) -> str:
    match = next((m for m in catalog if m["id"] == module_id), None)
    return match["title"] if match else module_id