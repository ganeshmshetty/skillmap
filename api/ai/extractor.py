import json
import re
import os
import spacy
import google.generativeai as genai
from dotenv import load_dotenv
from .prompts import RESUME_EXTRACTION_PROMPT, JD_EXTRACTION_PROMPT
from .models import ExtractedSkill, JDSkill

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini = genai.GenerativeModel("gemini-1.5-flash")

nlp = spacy.load("en_core_web_sm")

def _call_llm(prompt: str) -> str:
    response = gemini.generate_content(prompt)
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
    doc = nlp(resume_text[:10000])
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