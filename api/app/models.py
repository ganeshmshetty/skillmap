from pydantic import BaseModel


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str


class HealthResponse(BaseModel):
    status: str
    service: str
