import collections
from typing import Dict, List, Optional, Set

from ai.models import ExtractedSkill, JDSkill, GapItem, AdaptivePathway, PathNode, ReasoningTrace
from app.services.catalog import CatalogModule, CourseCatalogService

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
            continue
            
        lookup_key = jd_skill.onet_id or jd_skill.name.lower()
        current = resume_map.get(lookup_key)
        
        # proficiency_level from LLM is 1, 2, 3
        current_level = current.proficiency_level if current else 0
        
        # DEMO LOGIC: If user matches required level, suggest pushing to NEXT level
        # if JD wants 2 and user is 2, set required to 3 so we suggest advanced modules
        effective_required = jd_skill.required_level
        if current_level >= effective_required and current_level < 3:
            effective_required = current_level + 1
            
        delta = max(0, effective_required - current_level)
        if delta == 0:
            continue

        gap_score = delta * jd_skill.importance
        gaps.append(GapItem(
            skill_name=jd_skill.name,
            onet_id=jd_skill.onet_id,
            current_level=current_level,
            required_level=effective_required,
            gap_score=gap_score,
            importance=jd_skill.importance
        ))

    gaps.sort(key=lambda g: g.gap_score, reverse=True)
    return gaps

def generate_adaptive_pathway(
    gaps: List[GapItem],
    catalog: CourseCatalogService
) -> AdaptivePathway:
    """
    Constructs a topologically sorted learning path based on skill gaps.
    1. Identify target modules for gaps.
    2. Expand prerequisites to build a DAG.
    3. Topologically sort the DAG.
    4. Group into phases.
    """
    
    # --- Step 1: Identify target modules ---
    # Convert gap skills to target modules via catalog
    needed_skill_ids = {g.onet_id for g in gaps if g.onet_id}
    
    # Use the catalog's heuristic to pick best modules for these skills
    # We ask for a few per gap to ensure coverage
    # Assuming catalog.filter_modules() or similar exists - we'll use scan
    
    potential_modules = []
    # Simple scan for now (hackathon speed) - ideally CatalogService has optimized lookup
    # In catalog.py we saw modules_by_skill
    
    # Let's interact with catalog service directly
    # catalog.modules_by_skill is available
    
    target_modules_map = {} # id -> module
    
    for gap in gaps:
        if not gap.onet_id:
            continue
        
        candidates = catalog.modules_by_skill.get(gap.onet_id, [])
        if not candidates:
            continue
            
        # Pick best candidate: e.g. matching level
        # If gap suggests moving from Level 1 -> 2, pick Intermediate
        target_level = "Beginner"
        if gap.required_level >= 3:
            target_level = "Advanced"
        elif gap.required_level == 2:
            target_level = "Intermediate"
            
        best = next((m for m in candidates if m.level == target_level), candidates[0])
        target_modules_map[best.id] = best

    # --- Step 2: Expand Prerequisites (DAG Build) ---
    # We need to include all prerequisites of the target modules recursively
    
    expanded_modules: Dict[str, CatalogModule] = {}
    
    def expand(module_id: str):
        if module_id in expanded_modules:
            return
        
        module = catalog.modules_by_id.get(module_id)
        if not module:
            return 
        
        expanded_modules[module_id] = module
        for prereq_id in module.prerequisites:
            expand(prereq_id)
            
    for mid in target_modules_map:
        expand(mid)
    
    # --- Step 3: Topological Sort (Kahn's Algorithm) ---
    # Build Adjacency List: Prereq -> [Dependents]
    adj = collections.defaultdict(list)
    in_degree = {mid: 0 for mid in expanded_modules}
    
    for mid, module in expanded_modules.items():
        for prereq_id in module.prerequisites:
            if prereq_id in expanded_modules:
                adj[prereq_id].append(mid)
                in_degree[mid] += 1
                
    queue = collections.deque([mid for mid, deg in in_degree.items() if deg == 0])
    sorted_order = []
    
    while queue:
        node_id = queue.popleft()
        sorted_order.append(node_id)
        
        for neighbor in adj[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                
    # Check for cycles / leftover nodes (simple fallback: append remaining)
    if len(sorted_order) != len(expanded_modules):
        visited = set(sorted_order)
        for mid in expanded_modules:
            if mid not in visited:
                sorted_order.append(mid)

    # --- Step 4: Construct PathNodes & Phases ---
    path_nodes = []
    current_total_min = 0
    phase_buckets = {"Foundation": [], "Core": [], "Advanced": []}
    
    total_steps = len(sorted_order)
    
    for i, mod_id in enumerate(sorted_order):
        module = expanded_modules[mod_id]
        
        # Phase Heuristic
        if module.level == "Beginner":
            p = "Foundation"
        elif module.level == "Advanced":
            p = "Advanced"
        else:
            p = "Core"
            
        # Fallback if distribution is skewed
        if p == "Foundation" and i > total_steps * 0.5:
            p = "Core"
            
        phase_buckets.setdefault(p, []).append(mod_id)
        
        # Determine coverage
        skills_covered = []
        for sid in module.skill_ids:
             # Find matching gap
            for g in gaps:
                if g.onet_id == sid:
                    skills_covered.append(g.skill_name)
        
        # Dedupe
        skills_covered = list(set(skills_covered))
        
        # --- Generate Reasoning ---
        # For the hackathon, we'll use a mix of template and LLM
        # to avoid hitting rate limits too hard if the path is long.
        
        gap_desc = ", ".join(skills_covered) if skills_covered else "Prerequisite Knowledge"
        
        # Real reasoning using LLM (if we have a client)
        # For Member A: This is the chain-of-thought generator
        justification = None
        try:
            from ai.extractor import _call_llm
            from ai.prompts import REASONING_TRACE_PROMPT
            
            # Only call LLM for the first few core modules to save time/quota
            if i < 5:
                prompt = REASONING_TRACE_PROMPT.format(
                    module_title=module.title,
                    gap_description=gap_desc,
                    current_level=0, # Simplified
                    required_level=module.level,
                    prereq_chain=", ".join(sorted_order[:i])
                )
                # Use a smaller/faster model if available
                justification = _call_llm(prompt)
        except Exception:
            pass

        if not justification:
            if skills_covered:
                justification = f"This module addresses your gap in {skills_covered[0]}. It provides the necessary depth for {module.level} proficiency."
            else:
                justification = f"A fundamental prerequisite that builds the necessary foundation for advanced technologies in your pathway."

        reasoning = ReasoningTrace(
            module_id=module.id,
            module_title=module.title,
            gap_closed=gap_desc,
            justification=justification,
            confidence=0.95
        )
        
        path_nodes.append(PathNode(
            module_id=module.id,
            title=module.title,
            phase=p,
            status="pending",
            estimated_duration=module.duration_min,
            skill_gaps_covered=skills_covered,
            reasoning=reasoning
        ))
        
        current_total_min += module.duration_min

    return AdaptivePathway(
        nodes=path_nodes,
        total_duration=current_total_min,
        phases=phase_buckets
    )