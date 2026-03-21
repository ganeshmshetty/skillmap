import json
import re
import os
import time

from google import genai
from dotenv import load_dotenv
from .prompts import RESUME_EXTRACTION_PROMPT, JD_EXTRACTION_PROMPT
from .models import ExtractedSkill, JDSkill

# Re-evaluate the path to the api/.env file explicitly
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

# Then explicitly re-load standard dotenv as fallback in case it's run differently
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _call_llm(prompt: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                print(f"Rate limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    # Final attempt without catching
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text

def _parse_json_safely(raw: str) -> list:
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []

def extract_resume_skills(resume_text: str) -> list[ExtractedSkill]:

    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text[:30000])
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

def extract_jd_skills(jd_text: str) -> tuple[str, list[JDSkill]]:
    """
    Returns (detected_domain, list_of_jd_skills).
    The LLM now returns a JSON object with 'detected_domain' and 'skills'.
    """
    prompt = JD_EXTRACTION_PROMPT.format(jd_text=jd_text[:30000])
    raw = _call_llm(prompt)
    
    # Parse the response — could be a dict (new format) or list (old format)
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find a JSON object
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            # Fallback: try to find old-style array
            match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
            else:
                return ("General", [])
    
    # Handle both formats
    if isinstance(parsed, dict):
        detected_domain = parsed.get("detected_domain", "General")
        items = parsed.get("skills", [])
    elif isinstance(parsed, list):
        detected_domain = "General"
        items = parsed
    else:
        return ("General", [])

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
    return (detected_domain, skills)