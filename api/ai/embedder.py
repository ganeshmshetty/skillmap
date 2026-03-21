import json
import os
import math
from typing import Any

from dotenv import load_dotenv

from .models import ExtractedSkill, JDSkill

_onet_cache = None
_onet_index_cache = None
_embedding_client = None
_embedding_cache: dict[str, list[float]] = {}
_embedding_enabled: bool | None = None

load_dotenv()

EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2-preview")
EMBEDDING_THRESHOLD = float(os.getenv("GEMINI_EMBEDDING_THRESHOLD", "0.82"))
EMBEDDING_BATCH_SIZE = int(os.getenv("GEMINI_EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_MAX_CANDIDATES = int(os.getenv("GEMINI_EMBEDDING_MAX_CANDIDATES", "128"))
EMBEDDING_OUTPUT_DIMENSIONALITY = int(os.getenv("GEMINI_EMBEDDING_OUTPUT_DIMENSIONALITY", "768"))

# Common tech skill names → O*NET IDs verified against our SQLite skills table.
# RULE: only map to the *correct* skill or nearest correct parent, NEVER to an unrelated one.
COMMON_SKILL_ALIASES = {
    # --- Languages ---
    "java": "TECH-dd6ab6c595a4",           # Sun Microsystems Java (NOT JavaScript!)
    "javascript": "TECH-686155af75a6",      # JavaScript
    "js": "TECH-686155af75a6",
    "typescript": "TECH-558b544cf685",      # TypeScript
    "ts": "TECH-558b544cf685",
    "python": "TECH-a7f5f35426b9",          # Python
    "c++": "TECH-f6f87c9fdcf8",             # C++
    "cpp": "TECH-f6f87c9fdcf8",
    "rust": "TECH-bcfead2564ee",            # Rust programming language
    "scala": "TECH-3012dcff1477",           # Scala
    "kotlin": "TECH-539a3a5859d2",          # Kotlin
    "swift": "TECH-ae832e9b5bda",           # Swift
    "ruby": "TECH-d41a9e3915fd",            # Ruby on Rails (closest)
    "ruby on rails": "TECH-d41a9e3915fd",
    "rails": "TECH-d41a9e3915fd",

    # --- Frontend Frameworks ---
    "react": "TECH-50ce2da63bea",           # React
    "react.js": "TECH-50ce2da63bea",
    "reactjs": "TECH-50ce2da63bea",
    "react native": "TECH-bd9b1ab2f29a",    # React Native
    "react redux": "TECH-dfa2b57e329b",     # React Redux
    "redux": "TECH-dfa2b57e329b",
    "angular": "TECH-270d590270bb",         # Google Angular
    "angularjs": "TECH-270d590270bb",
    "vue": "TECH-75faee4ddc6a",             # Vue.js
    "vue.js": "TECH-75faee4ddc6a",
    "vuejs": "TECH-75faee4ddc6a",
    "jquery": "TECH-f590b4fda2c3",          # jQuery
    "html": "TECH-88f128a3530e",            # Hypertext markup language HTML
    "html5": "TECH-88f128a3530e",
    "html/css": "TECH-88f128a3530e",
    "webpack": "TECH-424516ca53b4",         # webpack

    # --- Backend Frameworks ---
    "node": "TECH-3b2819dd4c24",            # Node.js
    "node.js": "TECH-3b2819dd4c24",
    "nodejs": "TECH-3b2819dd4c24",
    "express": "TECH-3b2819dd4c24",         # Express ≈ Node.js ecosystem
    "express.js": "TECH-3b2819dd4c24",
    "django": "TECH-ef0f93c83e37",          # Django
    "flask": "TECH-9784e91c7b26",           # Flask
    "spring": "TECH-5d8ac1cd6ff5",          # Spring Framework
    "spring boot": "TECH-d2b84a7bb8d2",     # Spring Boot
    "rest api": "TECH-558052b80ee6",        # RESTful API
    "rest apis": "TECH-558052b80ee6",
    "restful api": "TECH-558052b80ee6",
    "restful apis": "TECH-558052b80ee6",
    "api design": "TECH-558052b80ee6",
    "graphql": "TECH-524de3d2ade4",         # GraphQL

    # --- Databases ---
    "sql": "TECH-b3d167ed9743",             # Structured query language SQL
    "postgresql": "TECH-399bd1ee5872",      # PostgreSQL
    "postgres": "TECH-399bd1ee5872",
    "mysql": "TECH-62a004b95946",           # MySQL
    "mongodb": "TECH-206e3718af09",         # MongoDB
    "mongo": "TECH-206e3718af09",
    "sqlite": "TECH-497757a9c5b2",          # SQLite
    "redis": "TECH-e111446745a1",           # Redis
    "cassandra": "TECH-b38d7ed57d79",       # Apache Cassandra

    # --- DevOps & Infrastructure ---
    "docker": "TECH-c5fd214cdd0d",          # Docker
    "kubernetes": "TECH-30136395f018",      # Kubernetes
    "k8s": "TECH-30136395f018",
    "git": "TECH-0bcc70105ad2",             # Git
    "github": "TECH-d3b7c913cd04",          # GitHub
    "jenkins": "TECH-6bf4ab292e19",         # Jenkins CI
    "terraform": "TECH-055fee38b236",       # IBM Terraform
    "ansible": "TECH-fa6c4dbaeaaa",         # Red Hat Ansible Engine
    "linux": "TECH-edc9f0a5a5d5",           # Linux
    "containerization": "TECH-c5fd214cdd0d",# Docker
    "ci/cd": "TECH-6bf4ab292e19",           # Jenkins CI (closest CI/CD tool)
    "cicd": "TECH-6bf4ab292e19",
    "continuous integration": "TECH-6bf4ab292e19",
    "continuous deployment": "TECH-6bf4ab292e19",
    "devops": "TECH-c5fd214cdd0d",          # Docker (DevOps ≈ containerization tools)
    "microservices": "TECH-c5fd214cdd0d",

    # --- Cloud Platforms ---
    "aws": "TECH-bddedb19a95d",             # → closest: Google Cloud software (generic cloud)
    "amazon web services": "TECH-bddedb19a95d",
    "azure": "TECH-d45e7661627f",           # Microsoft Azure software
    "microsoft azure": "TECH-d45e7661627f",
    "gcp": "TECH-bddedb19a95d",             # Google Cloud software
    "google cloud": "TECH-bddedb19a95d",
    "google cloud platform": "TECH-bddedb19a95d",
    "cloud": "TECH-bddedb19a95d",
    "cloud computing": "TECH-bddedb19a95d",
    "cloud infrastructure": "TECH-bddedb19a95d",

    # --- AI / ML / Data ---
    "tensorflow": "TECH-074dd699710d",      # TensorFlow
    "pytorch": "TECH-95b88f180e9e",         # PyTorch
    "pandas": "TECH-3a43b4f88325",          # pandas
    "spacy": "TECH-22fb6b7a2aeb",           # spaCy
    "machine learning": "TECH-a7f5f35426b9",# Python (ML's primary lang)
    "ml": "TECH-a7f5f35426b9",
    "deep learning": "TECH-074dd699710d",   # TensorFlow (DL framework)
    "artificial intelligence": "TECH-a7f5f35426b9",
    "ai": "TECH-a7f5f35426b9",
    "data analysis": "TECH-3a43b4f88325",   # pandas
    "data science": "TECH-a7f5f35426b9",    # Python
    "data visualization": "TECH-3a43b4f88325",
    "data engineering": "TECH-a7f5f35426b9",

    # --- Messaging ---
    "kafka": "TECH-bb2bd99338b1",           # Apache Kafka

    # --- Misc / Soft Skills → keep unmapped ---
    # Soft skills (communication, leadership, teamwork) are intentionally
    # NOT mapped to tech tools. They will go through embedding fallback.
}



def _normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _tokenize(text: str) -> list[str]:
    normalized = _normalize_text(text)
    tokens = []
    for raw in normalized.replace("/", " ").replace("-", " ").replace(".", " ").split():
        if len(raw) >= 2:
            tokens.append(raw)
    return tokens


def _normalize_vector(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return values
    return [v / norm for v in values]


def _dot_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return -1.0
    return sum(x * y for x, y in zip(a, b))


def _get_embedding_client():
    global _embedding_client
    if _embedding_client is not None:
        return _embedding_client

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        _embedding_client = genai.Client(api_key=api_key)
    except Exception:
        return None
    return _embedding_client


def _is_embedding_enabled() -> bool:
    global _embedding_enabled
    if _embedding_enabled is not None:
        return _embedding_enabled

    flag = os.getenv("ENABLE_GEMINI_EMBEDDING_MATCH", "true").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        _embedding_enabled = False
        return False

    _embedding_enabled = _get_embedding_client() is not None
    return _embedding_enabled


def _extract_values(embedding_obj: Any) -> list[float] | None:
    values = getattr(embedding_obj, "values", None)
    if values is None and isinstance(embedding_obj, dict):
        values = embedding_obj.get("values")
    if not values:
        return None
    return [float(v) for v in values]


def _embed_texts(texts: list[str], task_type: str) -> dict[str, list[float]]:
    client = _get_embedding_client()
    if client is None:
        return {}

    uncached = [t for t in texts if t not in _embedding_cache]
    if uncached:
        try:
            from google.genai import types
            for i in range(0, len(uncached), EMBEDDING_BATCH_SIZE):
                batch = uncached[i : i + EMBEDDING_BATCH_SIZE]
                config = types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBEDDING_OUTPUT_DIMENSIONALITY,
                )
                response = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=config,
                )
                embeddings = getattr(response, "embeddings", None)
                if embeddings is None and isinstance(response, dict):
                    embeddings = response.get("embeddings")
                if not embeddings:
                    continue

                for text, emb in zip(batch, embeddings):
                    values = _extract_values(emb)
                    if values is not None:
                        _embedding_cache[text] = _normalize_vector(values)
        except Exception as exc:
            print(f"[Embedder] Gemini embedding call failed: {exc}")
            return {}

    return {t: _embedding_cache[t] for t in texts if t in _embedding_cache}

def _get_db_connection():
    import sqlite3
    import os
    from pathlib import Path
    
    # Resolve robustly: api/ai/embedder.py -> project_root/data/onet.sqlite
    root_dir = Path(__file__).resolve().parent.parent.parent
    db_path = root_dir / "data" / "onet.sqlite"
    
    # Fallback just in case script is moved
    if not db_path.exists():
        fallback = Path("data/onet.sqlite")
        if fallback.exists():
            db_path = fallback
        else:
            fallback = Path("../data/onet.sqlite")
            if fallback.exists():
                db_path = fallback
                
    return sqlite3.connect(str(db_path))

def anchor_to_onet(skills: list, threshold: float = 0.82, on_match=None) -> list:
    """
    Match a list of ExtractedSkill or JDSkill to canonical O*NET nodes using SQLite.
    Uses multi-stage matching: exact title → alias → common skill map → FTS semantic → substring match.
    Mutates onet_id in place. Returns the same list.
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"[Embedder] Failed to connect to SQLite DB: {e}")
        return skills

    try:
        unresolved = []
        
        for skill in skills:
            if skill.onet_id:
                if on_match: on_match(skill.name, skill.onet_id, "pre_anchored", 1.0)
                continue
            
            name = _normalize_text(skill.name)
            
            # Stage 1: Exact title match
            cursor.execute("SELECT id FROM skills WHERE LOWER(title) = ?", (name,))
            row = cursor.fetchone()
            if row:
                skill.onet_id = row[0]
                if on_match: on_match(skill.name, skill.onet_id, "exact_title", 1.0)
                continue
            
            # Stage 2: Alias match
            cursor.execute("SELECT skill_id FROM aliases WHERE LOWER(alias) = ?", (name,))
            row = cursor.fetchone()
            if row:
                skill.onet_id = row[0]
                if on_match: on_match(skill.name, skill.onet_id, "alias", 1.0)
                continue
            
            # Stage 3: Common tech aliases
            if name in COMMON_SKILL_ALIASES:
                skill.onet_id = COMMON_SKILL_ALIASES[name]
                if on_match: on_match(skill.name, skill.onet_id, "alias", 1.0)
                continue

            unresolved.append(skill)

        # Stage 4: Gemini embedding semantic retrieval fallback
        semantic_threshold = threshold if threshold != 0.82 else EMBEDDING_THRESHOLD
        
        if unresolved and _is_embedding_enabled():
            query_texts = [_normalize_text(s.name) for s in unresolved]
            query_vectors = _embed_texts(query_texts, task_type="RETRIEVAL_QUERY")

            for skill, query_text in zip(unresolved, query_texts):
                query_vec = query_vectors.get(query_text)
                if query_vec is None:
                    continue

                tokens = _tokenize(query_text)
                if not tokens:
                    continue
                
                # Simple FTS OR query to get candidate matches quickly
                fts_query = " OR ".join(tokens)
                try:
                    cursor.execute("SELECT id, title FROM skills_fts WHERE skills_fts MATCH ? LIMIT ?", 
                                   (fts_query, EMBEDDING_MAX_CANDIDATES))
                    candidates = cursor.fetchall()
                except Exception as e:
                    print(f"[Embedder] FTS error: {e}")
                    continue
                    
                if not candidates:
                    continue

                candidate_texts = [row[1] for row in candidates]
                # Handle multiple IDs with the same title gracefully
                candidate_id_map = {row[1]: row[0] for row in candidates}
                
                candidate_vectors = _embed_texts(candidate_texts, task_type="RETRIEVAL_DOCUMENT")
                if not candidate_vectors:
                    continue

                best_sid = None
                best_score = -1.0
                for ctext, cid in candidate_id_map.items():
                    cvec = candidate_vectors.get(ctext)
                    if cvec is None:
                        continue
                    score = _dot_similarity(query_vec, cvec)
                    if score > best_score:
                        best_score = score
                        best_sid = cid

                if best_sid and best_score >= semantic_threshold:
                    skill.onet_id = best_sid
                    if on_match: on_match(skill.name, skill.onet_id, "embedding", best_score)

        # Stage 5: conservative substring fallback
        for skill in unresolved:
            if skill.onet_id:
                continue
            name = _normalize_text(skill.name)
            if len(name) > 3:
                cursor.execute("SELECT id FROM skills WHERE LOWER(title) LIKE ?", (f"%{name}%",))
                row = cursor.fetchone()
                if row:
                    skill.onet_id = row[0]
                    if on_match: on_match(skill.name, skill.onet_id, "substring", 1.0)
            
            if not skill.onet_id and on_match:
                on_match(skill.name, None, "unmatched", 0.0)
    finally:
        conn.close()
    
    return skills