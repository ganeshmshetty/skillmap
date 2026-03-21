# API Contract (v1 - Current)

Source of truth: `api/app/main.py` and `api/ai/models.py`.

## GET `/health`

### Response `200`
```json
{
  "status": "ok"
}
```

## GET `/catalog/health`

### Response `200`
```json
{
  "status": "ok",
  "modules": 114,
  "skills_indexed": 114
}
```

### Response `503`
```json
{
  "status": "unavailable",
  "error": "Catalog file not found. Set CATALOG_PATH or create data/catalog/modules.json"
}
```

## POST `/analyze`
Upload resume and JD files.

### Request
- Content-Type: `multipart/form-data`
- Fields:
  - `resume`: file (`.pdf`, `.docx`, `.txt`)
  - `jd`: file (`.pdf`, `.docx`, `.txt`)

### Response `200`
```json
{
  "job_id": "d4a1c94f-5e84-4ae9-a064-8b2ce4d6642d",
  "status": "queued"
}
```

### Error Shape
```json
{
  "error": {
    "code": "invalid_file_type",
    "message": "Only PDF, DOCX, TXT are supported",
    "details": {
      "field": "resume"
    }
  }
}
```

## GET `/result/{job_id}`
Fetch async analysis result.

### Response States
- `queued`
- `processing`
- `completed`
- `failed`
- `not_found`

### Response `completed`
```json
{
  "job_id": "d4a1c94f-5e84-4ae9-a064-8b2ce4d6642d",
  "status": "completed",
  "updated_at": "2026-03-20T12:34:56.000000+00:00",
  "result": {
    "resume_skills": [
      {
        "name": "Python",
        "onet_id": "TECH-abc123",
        "proficiency_level": 2,
        "years_exp": 2.5,
        "confidence": 0.91
      }
    ],
    "jd_skills": [
      {
        "name": "Python",
        "onet_id": "TECH-abc123",
        "required_level": 3,
        "is_required": true,
        "importance": 0.86
      }
    ],
    "gap_vector": [
      {
        "skill_name": "Python",
        "onet_id": "TECH-abc123",
        "current_level": 2,
        "required_level": 3,
        "gap_score": 0.86,
        "importance": 0.86
      }
    ],
    "pathway": {
      "nodes": [
        {
          "module_id": "mod_python_foundations",
          "title": "Python Foundations",
          "phase": "Foundation",
          "reasoning": {
            "module_id": "mod_python_foundations",
            "module_title": "Python Foundations",
            "gap_closed": "Python",
            "justification": "This module addresses your gap in Python",
            "confidence": 0.95,
            "prerequisite_chain": []
          },
          "status": "pending",
          "estimated_duration": 120,
          "skill_gaps_covered": [
            "Python"
          ]
        }
      ],
      "total_duration": 120,
      "phases": {
        "Foundation": [
          "mod_python_foundations"
        ],
        "Core": [],
        "Advanced": []
      }
    },
    "reasoning_traces": [
      {
        "module_id": "mod_python_foundations",
        "module_title": "Python Foundations",
        "gap_closed": "Python",
        "justification": "This module addresses your gap in Python",
        "confidence": 0.95,
        "prerequisite_chain": []
      }
    ],
    "coverage_score": 0.67,
    "redundancy_reduction": 0.42
  }
}
```

### Response `failed`
```json
{
  "job_id": "d4a1c94f-5e84-4ae9-a064-8b2ce4d6642d",
  "status": "failed",
  "updated_at": "2026-03-20T12:34:56.000000+00:00",
  "error": {
    "code": "analysis_failed",
    "message": "Failed to process analysis job",
    "details": {
      "reason": "..."
    }
  }
}
```



## GET \/api/history/{id}\`nFetch a specific historical run with its expanded module list from the DB.

## PUT \/api/pathway_modules/{id}\`nUpdate a status module payload (e.g. \{"status": "In Progress"}\).
Fetch historical analytics runs saved to the Supabase database.
Fetch historical analytics runs saved to the Supabase database.
Fetch a specific historical run with its expanded module list from the DB.
Fetch a specific historical run with its expanded module list from the DB.
Update a status module payload (e.g. \{"status": "In Progress"}\).
Update a status module payload (e.g. \{"status": "In Progress"}\).
