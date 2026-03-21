import json
import os
from .models import ExtractedSkill, JDSkill

_onet_cache = None

def _get_onet_data(path="data/onet_skills.json"):
    global _onet_cache
    if _onet_cache is not None:
        return _onet_cache

    # Try multiple candidate paths
    candidates = [path, "../data/onet_skills.json"]
    found_path = None
    for p in candidates:
        if os.path.exists(p):
            found_path = p
            break

    if found_path is None:
        return []
        
    with open(found_path) as f:
        data = json.load(f)
        
    _onet_cache = data
    return _onet_cache

def anchor_to_onet(skills: list, threshold: float = 0.82) -> list:
    """
    Match a list of ExtractedSkill or JDSkill to canonical O*NET nodes.
    Mutates onet_id in place. Returns the same list.
    """
    onet_nodes = _get_onet_data()
    if not onet_nodes:
        return skills  # graceful degradation if data not ready

    # Pre-compute alias map for O(1) lookup
    alias_map = {}
    for n in onet_nodes:
        for alias in n.get("aliases", []):
            alias_map[alias.lower()] = n["id"]
    
    for i, skill in enumerate(skills):
        # Stage 1: exact string match (fastest)
        lower_name = skill.name.lower()
        exact = next((n for n in onet_nodes if n["title"].lower() == lower_name), None)
        if exact:
            skill.onet_id = exact["id"]
            continue
        
        # Stage 2: alias match (e.g. "k8s" → "Kubernetes")
        if lower_name in alias_map:
            skill.onet_id = alias_map[lower_name]
            continue
    
    return skills