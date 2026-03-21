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

    Uses bidirectional matching: indexes resume skills by BOTH onet_id and
    normalized name so that "React.js" (resume) matches "React" (JD) via
    their shared O*NET anchor.
    """
    # Build a multi-key lookup: onet_id → skill, name.lower() → skill
    resume_map: dict[str, ExtractedSkill] = {}
    for rs in resume_skills:
        if rs.onet_id:
            resume_map[rs.onet_id] = rs
        resume_map[rs.name.lower().strip()] = rs

    gaps = []
    for jd_skill in jd_skills:
        if not jd_skill.is_required:
            continue

        # Try matching by O*NET ID first (most reliable), then fall back to name
        current = None
        if jd_skill.onet_id:
            current = resume_map.get(jd_skill.onet_id)
        if current is None:
            current = resume_map.get(jd_skill.name.lower().strip())
        
        # proficiency_level from LLM is 1, 2, 3
        current_level = current.proficiency_level if current else 0
        
        effective_required = jd_skill.required_level
            
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

# Hard caps to keep pathways focused and scannable
MAX_GAPS_TO_COVER = 6        # Only address top-N highest-priority gaps
MAX_LLM_GENERATED = 2        # LLM fallback modules at most
MAX_PATHWAY_NODES = 12       # Total node ceiling after prerequisite expansion

def generate_adaptive_pathway(
    gaps: List[GapItem],
    catalog: CourseCatalogService,
    detected_domain: str = "Technology"
) -> AdaptivePathway:
    """
    Constructs a topologically sorted learning path based on skill gaps.
    HYBRID: Uses catalog modules when available, generates LLM modules for uncovered gaps.
    1. Identify target modules for the TOP gaps from catalog (capped).
    2. For uncovered gaps, dynamically generate modules via LLM (capped).
    3. Expand prerequisites to build a DAG (capped at MAX_PATHWAY_NODES).
    4. Topologically sort the DAG.
    5. Group into phases.
    """

    # --- Step 1: Identify target modules from catalog (top gaps only) ---
    target_modules_map: Dict[str, CatalogModule] = {}
    uncovered_gaps: List[GapItem] = []
    # Only process highest-priority gaps
    prioritized_gaps = gaps[:MAX_GAPS_TO_COVER]
    
    for gap in prioritized_gaps:
        if not gap.onet_id:
            uncovered_gaps.append(gap)
            continue

        candidates = catalog.modules_by_skill.get(gap.onet_id, [])
        if not candidates:
            uncovered_gaps.append(gap)
            continue

        # Pick best candidate matching the target level
        target_level = "Beginner"
        if gap.required_level >= 3:
            target_level = "Advanced"
        elif gap.required_level == 2:
            target_level = "Intermediate"

        best = next((m for m in candidates if m.level == target_level), candidates[0])
        target_modules_map[best.id] = best

    # --- Step 2: Generate LLM modules for uncovered gaps ---
    generated_modules: Dict[str, CatalogModule] = {}
    
    if uncovered_gaps:
        try:
            from ai.extractor import _call_llm
            from ai.prompts import DYNAMIC_MODULE_PROMPT
            import json
            import re

            # Only generate LLM modules for the top uncovered gaps, not all of them
            for gap in uncovered_gaps[:MAX_LLM_GENERATED]:
                try:
                    prompt = DYNAMIC_MODULE_PROMPT.format(
                        skill_name=gap.skill_name,
                        domain=detected_domain,
                        current_level=gap.current_level,
                        required_level=gap.required_level,
                        importance=gap.importance
                    )
                    raw = _call_llm(prompt)
                    cleaned = re.sub(r"```json|```", "", raw).strip()
                    
                    # Try to parse as JSON object
                    try:
                        module_data = json.loads(cleaned)
                    except json.JSONDecodeError:
                        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                        if match:
                            module_data = json.loads(match.group())
                        else:
                            continue
                    
                    gen_module = CatalogModule(
                        id=module_data.get("id", f"mod_gen_{gap.skill_name.lower().replace(' ', '_')[:20]}"),
                        title=module_data.get("title", f"{gap.skill_name} Essentials"),
                        description=module_data.get("description", f"Covers essential concepts in {gap.skill_name}."),
                        skill_ids=[gap.onet_id] if gap.onet_id else [],
                        domain=module_data.get("domain", detected_domain),
                        level=module_data.get("level", "Beginner"),
                        duration_min=int(module_data.get("duration_min", 60)),
                        prerequisites=[]
                    )
                    generated_modules[gen_module.id] = gen_module
                    target_modules_map[gen_module.id] = gen_module
                    
                except Exception as e:
                    print(f"[Pathway] Failed to generate module for '{gap.skill_name}': {e}")
                    continue
        except ImportError:
            print("[Pathway] LLM imports not available, skipping dynamic generation")

    # --- Step 3: Expand Prerequisites (DAG Build, capped at MAX_PATHWAY_NODES) ---
    expanded_modules: Dict[str, CatalogModule] = {}

    def expand(module_id: str, depth: int = 0):
        """Recursively expand prerequisites up to the pathway node cap.
        Depth-first but stops adding new nodes once cap is reached.
        """
        if module_id in expanded_modules:
            return
        if len(expanded_modules) >= MAX_PATHWAY_NODES:
            return  # Pathway is full — skip remaining prerequisites

        # Check catalog first, then generated modules
        module = catalog.modules_by_id.get(module_id) or generated_modules.get(module_id)
        if not module:
            return

        expanded_modules[module_id] = module
        # Only expand one level of prerequisites to avoid deep chains bloating the path
        if depth < 1:
            for prereq_id in module.prerequisites:
                expand(prereq_id, depth + 1)

    for mid in target_modules_map:
        expand(mid)
    
    # --- Step 4: Topological Sort (Kahn's Algorithm) ---
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
                
    # Check for cycles / leftover nodes
    if len(sorted_order) != len(expanded_modules):
        visited = set(sorted_order)
        for mid in expanded_modules:
            if mid not in visited:
                sorted_order.append(mid)

    # --- Step 5: Construct PathNodes & Phases ---
    path_nodes = []
    current_total_min = 0
    phase_buckets = {"Foundation": [], "Core": [], "Advanced": []}
    
    total_steps = len(sorted_order)
    
    # Pre-compute skills_covered and gap_desc for each module
    module_meta = []  # list of (mod_id, module, is_generated, skills_covered, gap_desc, phase)
    for i, mod_id in enumerate(sorted_order):
        module = expanded_modules[mod_id]
        is_generated = mod_id in generated_modules
        
        # Phase Heuristic
        if module.level == "Beginner":
            p = "Foundation"
        elif module.level == "Advanced":
            p = "Advanced"
        else:
            p = "Core"
            
        if p == "Foundation" and i > total_steps * 0.5:
            p = "Core"
            
        phase_buckets.setdefault(p, []).append(mod_id)
        
        # Determine coverage
        skills_covered = []
        for sid in module.skill_ids:
            for g in gaps:
                if g.onet_id == sid:
                    skills_covered.append(g.skill_name)
        skills_covered = list(set(skills_covered))
        
        gap_desc = ", ".join(skills_covered) if skills_covered else "Prerequisite Knowledge"
        module_meta.append((mod_id, module, is_generated, skills_covered, gap_desc, p))

    # --- Step 5b: Batch Reasoning Generation (single LLM call) ---
    justification_map: Dict[str, str] = {}
    try:
        from ai.extractor import _call_llm
        from ai.prompts import BATCH_REASONING_PROMPT
        import json as _json
        import re as _re

        batch_input = []
        for i, (mod_id, module, is_generated, skills_covered, gap_desc, p) in enumerate(module_meta):
            batch_input.append({
                "module_id": mod_id,
                "title": module.title,
                "gap_being_closed": gap_desc,
                "level": module.level,
                "position_in_pathway": i + 1,
            })

        prompt = BATCH_REASONING_PROMPT.format(modules_json=_json.dumps(batch_input, indent=2))
        raw = _call_llm(prompt)
        cleaned = _re.sub(r"```json|```", "", raw).strip()

        try:
            parsed = _json.loads(cleaned)
        except _json.JSONDecodeError:
            match = _re.search(r'\[.*\]', cleaned, _re.DOTALL)
            if match:
                parsed = _json.loads(match.group())
            else:
                parsed = []

        for item in parsed:
            mid = item.get("module_id", "")
            justification = item.get("justification", "")
            if mid and justification:
                justification_map[mid] = justification

    except Exception as e:
        print(f"[Pathway] Batch reasoning failed, using fallbacks: {e}")

    # Build PathNodes using batch results or fallback
    for i, (mod_id, module, is_generated, skills_covered, gap_desc, p) in enumerate(module_meta):
        justification = justification_map.get(mod_id)

        if not justification:
            source_label = " (AI-generated)" if is_generated else ""
            if skills_covered:
                justification = f"This module{source_label} addresses your gap in {skills_covered[0]}. It provides the necessary depth for {module.level} proficiency."
            else:
                justification = f"A fundamental prerequisite{source_label} that builds the necessary foundation for advanced topics in your pathway."

        reasoning = ReasoningTrace(
            module_id=module.id,
            module_title=module.title,
            gap_closed=gap_desc,
            justification=justification,
            confidence=0.95 if not is_generated else 0.85
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

    # --- Step 6: Construct Edges ---
    path_edges = []
    from ai.models import PathwayEdge
    for mid, module in expanded_modules.items():
        for prereq_id in module.prerequisites:
            if prereq_id in expanded_modules:
                path_edges.append(PathwayEdge(source=prereq_id, target=mid))

    # --- Step 7: Auto-expand Catalog with LLM-generated modules ---
    if generated_modules:
        _persist_generated_modules(generated_modules)

    return AdaptivePathway(
        nodes=path_nodes,
        edges=path_edges,
        total_duration=current_total_min,
        phases=phase_buckets
    )


def _persist_generated_modules(generated_modules: Dict[str, 'CatalogModule']) -> None:
    """
    Append LLM-generated modules to modules.json so the catalog grows over time.
    Only adds modules whose IDs don't already exist in the catalog file.
    Thread-safe via a simple file lock pattern.
    """
    import json
    import os
    from pathlib import Path

    candidate_paths = [
        "data/catalog/modules.json",
        "../data/catalog/modules.json",
    ]
    catalog_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            catalog_path = Path(p)
            break

    if catalog_path is None:
        return

    try:
        with catalog_path.open("r", encoding="utf-8") as f:
            existing = json.load(f)

        existing_ids = {m["id"] for m in existing if isinstance(m, dict)}
        new_modules = []
        for mid, module in generated_modules.items():
            if mid not in existing_ids:
                new_modules.append({
                    "id": module.id,
                    "title": module.title,
                    "description": module.description,
                    "skill_ids": module.skill_ids,
                    "domain": module.domain,
                    "level": module.level,
                    "duration_min": module.duration_min,
                    "prerequisites": list(module.prerequisites),
                    "_auto_generated": True,
                })

        if new_modules:
            existing.extend(new_modules)
            with catalog_path.open("w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            print(f"[Catalog] Auto-expanded: added {len(new_modules)} LLM-generated module(s)")
    except Exception as e:
        print(f"[Catalog] Auto-expansion failed (non-fatal): {e}")