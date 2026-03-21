# Architecture

## End-to-End Flow
1. User uploads resume + JD from frontend.
2. Backend stores job state (`queued`).
3. Extraction pipeline returns structured skills for resume and JD.
4. Skills are mapped to canonical O*NET skill IDs.
5. Gap engine computes missing skill priorities.
6. DAG engine expands prerequisites and topologically sorts modules.
7. Reasoning engine returns grounded explanations per module.
8. Backend saves specific structured Pathway outputs permanently to Supabase (PostgreSQL) for dashboard retrieval.
9. Frontend renders graph, metrics, and reasoning panel, or lists from the historical dashboard DB.

## Layers
- Layer 1: Document ingestion (PDF, DOCX, TXT)
- Layer 2: Skill extraction + O*NET anchoring
- Layer 3: Gap analysis and ranking
- Layer 4: Path construction via prerequisite DAG
- Layer 5: Grounded output and visualization

## Service Boundaries
- Frontend owns interaction and visualization.
- Backend owns orchestration, persistence, and algorithm execution.
- AI extraction can be called by backend but must emit contract-compliant JSON.

## Reliability Rules
- Any unknown module ID is rejected before response.
- Cycle in prerequisite graph triggers safe error with details.
- Empty or invalid files return actionable validation errors.
