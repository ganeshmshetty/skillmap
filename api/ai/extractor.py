import json
import re
from anthropic import Anthropic
from .prompts import RESUME_EXTRACTION_PROMPT, JD_EXTRACTION_PROMPT
from .models import ExtractedSkill, JDSkill

client = Anthropic()
nlp = None  # lazy load

def _get_nlp():
    """Lazy load spacy model on first use."""
    global nlp
    if nlp is None:
        import spacy
        nlp = spacy.load("en_core_web_sm")
    return nlp

def _call_llm(prompt: str) -> str:
    """Call Claude and return raw text response."""
    response = client.messages.create(
        model="claude-haiku-4-5",  # fast + cheap for extraction
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def _parse_json_safely(raw: str) -> list:
    """Strip markdown fences and parse JSON."""
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON array in the response
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []

def extract_resume_skills(resume_text: str) -> list[ExtractedSkill]:
    """Extract skills from resume using spaCy pre-filter + LLM structuring."""
    # spaCy pass: quick entity scan to check doc is parseable
    doc = _get_nlp()(resume_text[:10000])  # limit for speed
    
    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text[:4000])
    raw = _call_llm(prompt)
    items = _parse_json_safely(raw)
    
    skills = []
    for item in items:
        try:
            skills.append(ExtractedSkill(
                name=item.get("name", ""),
                proficiency_level=int(item.get("proficiency_level", 1)),
                years_exp=item.get("years_exp"),
                confidence=float(item.get("confidence", 0.7))
            ))
        except Exception:
            continue
    return skills

def extract_jd_skills(jd_text: str) -> list[JDSkill]:
    """Extract required skills from job description."""
    prompt = JD_EXTRACTION_PROMPT.format(jd_text=jd_text[:4000])
    raw = _call_llm(prompt)
    items = _parse_json_safely(raw)
    
    skills = []
    for item in items:
        try:
            skills.append(JDSkill(
                name=item.get("name", ""),
                required_level=int(item.get("required_level", 2)),
                is_required=bool(item.get("is_required", True)),
                importance=float(item.get("importance", 0.8))
            ))
        except Exception:
            continue
    return skills