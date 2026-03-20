from .models import ExtractedSkill, JDSkill, GapItem

def compute_gap_vector(
    resume_skills: list[ExtractedSkill],
    jd_skills: list[JDSkill]
) -> list[GapItem]:
    """
    For each JD skill, compute gap = max(0, required_level - current_level).
    Weighted by O*NET importance. Returns sorted gap vector (highest first).
    """
    resume_map: dict[str, ExtractedSkill] = {}
    for rs in resume_skills:
        key = rs.onet_id or rs.name.lower()
        resume_map[key] = rs

    gaps = []
    for jd_skill in jd_skills:
        if not jd_skill.is_required:
            continue  # skip nice-to-haves for core pathway

        lookup_key = jd_skill.onet_id or jd_skill.name.lower()
        current = resume_map.get(lookup_key)
        current_level = current.proficiency_level if current else 0

        delta = max(0, jd_skill.required_level - current_level)
        if delta == 0:
            continue  # already satisfied

        gap_score = delta * jd_skill.importance
        gaps.append(GapItem(
            skill_name=jd_skill.name,
            onet_id=jd_skill.onet_id,
            current_level=current_level,
            required_level=jd_skill.required_level,
            gap_score=gap_score,
            importance=jd_skill.importance
        ))

    gaps.sort(key=lambda g: g.gap_score, reverse=True)
    return gaps