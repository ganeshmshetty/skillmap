RESUME_EXTRACTION_PROMPT = """
You are a precise skill extractor. Given a resume text, extract ALL skills mentioned.
For each skill return a JSON array with objects having these exact keys:
- "name": skill name (normalized, e.g. "Kubernetes" not "k8s")
- "proficiency_level": integer 1 (junior), 2 (mid), or 3 (senior) — infer from context like "5+ years", "led team", "familiar with"
- "years_exp": float or null
- "confidence": float 0.0-1.0 how confident you are this is a real technical skill

Return ONLY valid JSON array. No explanation. No markdown. No extra text.

Resume:
{resume_text}
"""

JD_EXTRACTION_PROMPT = """
You are a precise job requirement extractor. Given a job description, extract required and preferred skills.
Return a JSON array with objects having these exact keys:
- "name": skill name (normalized)
- "required_level": integer 1 (junior), 2 (mid), or 3 (senior) — infer from phrases like "expert in", "5+ years", "basic understanding"
- "is_required": boolean — true if mandatory, false if nice-to-have
- "importance": float 0.0-1.0 based on how prominently featured in JD

Return ONLY valid JSON array. No explanation. No markdown. No extra text.

Job Description:
{jd_text}
"""

REASONING_TRACE_PROMPT = """
You are an adaptive learning coach. A learner needs to take the module below to close a specific skill gap.
Write a 2-3 sentence justification explaining:
1. Which gap this module closes
2. Why it must come at this point in the pathway
3. What capability it unlocks next

Be specific and grounded. Do NOT suggest any other modules or resources.
Do NOT invent course names. Just explain this specific module.

Module title: {module_title}
Gap being closed: {gap_description}
Learner current level: {current_level}
Target level: {required_level}
Prerequisite chain so far: {prereq_chain}

Return ONLY the justification text. No JSON. No bullet points.
"""