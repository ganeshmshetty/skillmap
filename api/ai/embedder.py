import json
import os
from .models import ExtractedSkill, JDSkill

_onet_cache = None

# Common tech skill names → O*NET IDs that don't have exact title matches
# These handle cases where LLM extracts "Java" but O*NET titles it differently
COMMON_SKILL_ALIASES = {
    "java": "TECH-b6e13ad53d8e",  # Map to JavaScript as closest; Java not in O*NET separately
    "sql": "TECH-519968cbed98",  # Map to PostgreSQL
    "rest api": "TECH-90de35a5800e",  # Map to Node.js
    "rest apis": "TECH-90de35a5800e",
    "restful api": "TECH-90de35a5800e",
    "restful apis": "TECH-90de35a5800e",
    "api design": "TECH-90de35a5800e",
    "grpc": "TECH-90de35a5800e",
    "machine learning": "TECH-4235227b5143",  # Map to Python (ML uses Python)
    "ml": "TECH-4235227b5143",
    "deep learning": "TECH-3d3f421e9db6",  # Map to TensorFlow
    "artificial intelligence": "TECH-4235227b5143",
    "ai": "TECH-4235227b5143",
    "aws": "TECH-ba324ca7b1c7",  # Map to Linux (cloud = infra)
    "amazon web services": "TECH-ba324ca7b1c7",
    "azure": "TECH-ba324ca7b1c7",
    "microsoft azure": "TECH-ba324ca7b1c7",
    "gcp": "TECH-ba324ca7b1c7",
    "google cloud": "TECH-ba324ca7b1c7",
    "google cloud platform": "TECH-ba324ca7b1c7",
    "cloud": "TECH-ba324ca7b1c7",
    "cloud infrastructure": "TECH-ba324ca7b1c7",
    "cloud computing": "TECH-ba324ca7b1c7",
    "devops": "TECH-e982f17bcbe0",  # Map to Docker
    "ci/cd": "TECH-e982f17bcbe0",
    "cicd": "TECH-e982f17bcbe0",
    "continuous integration": "TECH-e982f17bcbe0",
    "continuous deployment": "TECH-e982f17bcbe0",
    "html": "TECH-b6e13ad53d8e",  # Map to JavaScript (web)
    "css": "TECH-b6e13ad53d8e",
    "html/css": "TECH-b6e13ad53d8e",
    "html5": "TECH-b6e13ad53d8e",
    "css3": "TECH-b6e13ad53d8e",
    "angular": "TECH-b6e13ad53d8e",
    "vue": "TECH-b6e13ad53d8e",
    "vue.js": "TECH-b6e13ad53d8e",
    "jenkins": "TECH-e982f17bcbe0",
    "terraform": "TECH-adc1f5c8707f",
    "ansible": "TECH-ba324ca7b1c7",
    "rust": "TECH-372946aa2608",  # Map to C++ (systems lang)
    "agile": "TECH-46f1a0bd5592",  # Map to Git (methodology)
    "scrum": "TECH-46f1a0bd5592",
    "data analysis": "TECH-4235227b5143",
    "data science": "TECH-4235227b5143",
    "data visualization": "TECH-4235227b5143",
    "data engineering": "TECH-4235227b5143",
    "microservices": "TECH-e982f17bcbe0",
    "containerization": "TECH-e982f17bcbe0",
    "kafka": "TECH-5dd9422f45dc",
    "communication": "TECH-46f1a0bd5592",  # soft skill → generic mapping
    "problem solving": "TECH-4235227b5143",
    "teamwork": "TECH-46f1a0bd5592",
    "leadership": "TECH-46f1a0bd5592",
    "react": "TECH-6b810c90aa9a",
    "react.js": "TECH-6b810c90aa9a",
    "reactjs": "TECH-6b810c90aa9a",
    "node": "TECH-90de35a5800e",
    "node.js": "TECH-90de35a5800e",
    "nodejs": "TECH-90de35a5800e",
    "express": "TECH-90de35a5800e",
    "express.js": "TECH-90de35a5800e",
    "postgresql": "TECH-519968cbed98",
    "postgres": "TECH-519968cbed98",
    "mysql": "TECH-f460c882a18c",
    "mongodb": "TECH-7f1c982e835a",
}

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
    Uses multi-stage matching: exact title → alias → common skill map → substring match.
    Mutates onet_id in place. Returns the same list.
    """
    onet_nodes = _get_onet_data()
    if not onet_nodes:
        return skills  # graceful degradation if data not ready

    # Pre-compute title map and alias map for O(1) lookup
    title_map = {}
    alias_map = {}
    for n in onet_nodes:
        title_map[n["title"].lower().strip()] = n["id"]
        for alias in n.get("aliases", []):
            alias_map[alias.lower().strip()] = n["id"]
    
    for skill in skills:
        if skill.onet_id: continue
        
        name = skill.name.lower().strip()
        
        # Stage 1: Exact title match
        if name in title_map:
            skill.onet_id = title_map[name]
            continue
        
        # Stage 2: Alias match
        if name in alias_map:
            skill.onet_id = alias_map[name]
            continue
        
        # Stage 3: Common tech aliases
        if name in COMMON_SKILL_ALIASES:
            skill.onet_id = COMMON_SKILL_ALIASES[name]
            continue
            
        # Stage 4: Substring Fallback (contains)
        # Check if skill name is a substring of O*NET titles (or vice-versa)
        for title, sid in title_map.items():
            if len(name) > 3 and (name in title or title in name):
                skill.onet_id = sid
                break
    
    return skills