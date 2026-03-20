import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from .models import ExtractedSkill, JDSkill

_model = None  # lazy load

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def _load_onet(path="data/onet_skills.json") -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def anchor_to_onet(skills: list, threshold: float = 0.82) -> list:
    """
    Match a list of ExtractedSkill or JDSkill to canonical O*NET nodes.
    Mutates onet_id in place. Returns the same list.
    """
    onet_nodes = _load_onet()
    if not onet_nodes:
        return skills  # graceful degradation if data not ready

    model = _get_model()
    onet_names = [n["title"] for n in onet_nodes]
    onet_ids = [n["id"] for n in onet_nodes]
    
    # Batch embed O*NET titles once
    onet_embeddings = model.encode(onet_names, batch_size=64, show_progress_bar=False)
    
    for skill in skills:
        # Stage 1: exact string match (fastest)
        lower_name = skill.name.lower()
        exact = next((n for n in onet_nodes if n["title"].lower() == lower_name), None)
        if exact:
            skill.onet_id = exact["id"]
            continue
        
        # Stage 2: alias match (e.g. "k8s" → "Kubernetes")
        alias_match = next(
            (n for n in onet_nodes if lower_name in [a.lower() for a in n.get("aliases", [])]),
            None
        )
        if alias_match:
            skill.onet_id = alias_match["id"]
            continue
        
        # Stage 3: semantic similarity
        skill_emb = model.encode([skill.name])[0]
        sims = [_cosine_sim(skill_emb, oe) for oe in onet_embeddings]
        best_idx = int(np.argmax(sims))
        if sims[best_idx] >= threshold:
            skill.onet_id = onet_ids[best_idx]
    
    return skills