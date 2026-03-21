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
Return a JSON object with two keys:
1. "detected_domain": a string — the primary industry domain of this job. Pick one of: "Technology", "Healthcare", "Sales", "Operations", "Finance", "Engineering", "Education", "Legal", "Marketing", "Design", or "General".
2. "skills": a JSON array with objects having these exact keys:
   - "name": skill name (normalized, e.g. "React.js" not "react")
   - "required_level": integer 1 (junior), 2 (mid), or 3 (senior) — infer from phrases like "expert in", "5+ years", "basic understanding"
   - "is_required": boolean — true if mandatory, false if nice-to-have
   - "importance": float 0.0-1.0 based on how prominently featured in JD

Return ONLY valid JSON object. No explanation. No markdown. No extra text.

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

BATCH_REASONING_PROMPT = """
You are an adaptive learning coach. A learner has been assigned the following modules to close skill gaps.
For EACH module, write a 2-3 sentence justification explaining:
1. Which gap this module closes
2. Why it must come at this point in the pathway
3. What capability it unlocks next

Be specific and grounded. Do NOT suggest other modules.

Modules (in learning order):
{modules_json}

Return a JSON array of objects, one per module, with exactly these keys:
- "module_id": the module ID from the input
- "justification": your 2-3 sentence justification

Return ONLY valid JSON array. No explanation. No markdown.
"""

DYNAMIC_MODULE_PROMPT = """
You are a curriculum designer. A learner has a skill gap that no existing course in our catalog can address.
Generate a single learning module to fill this gap.

Return a JSON object with these exact keys:
- "id": a module ID in the format "mod_gen_<short_slug>" (e.g. "mod_gen_cloud_security")
- "title": a concise, professional course title (5-8 words max)
- "description": a 1-2 sentence course description covering key topics
- "level": one of "Beginner", "Intermediate", or "Advanced" — pick based on the target level below
- "duration_min": estimated duration in minutes (30, 45, 60, 90, or 120)
- "domain": the domain this module belongs to (e.g. "Technology", "Healthcare", "Sales", etc.)

Context:
- Skill name: {skill_name}
- Target domain: {domain}
- Learner current level: {current_level} (0=none, 1=junior, 2=mid, 3=senior)
- Required level: {required_level}
- Gap importance: {importance}

Return ONLY valid JSON object. No explanation. No markdown. No extra text.
"""