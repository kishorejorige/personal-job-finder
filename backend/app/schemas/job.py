import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class JobBase(BaseModel):
    title: str
    company_name: str
    location: str | None = None
    remote_status: str | None = "unknown"
    employment_type: str | None = None
    salary: str | None = None
    description: str | None = None
    source: str
    source_board: str | None = None
    original_url: str | None = None
    posted_date: str | None = None
    match_score: int = 0
    application_status: str = "not_applied"
    applied_date: datetime | None = None
    notes: str | None = None
    job_fingerprint: str | None = None
    duplicate_of_id: int | None = None


class JobResponse(JobBase):
    id: int
    skills: list[str] = []
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("skills", "matched_skills", "missing_skills", mode="before")
    @classmethod
    def parse_json_lists(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [v]
            except Exception:
                return [v]
        elif v is None:
            return []
        return v


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobStatusUpdate(BaseModel):
    application_status: str

    @field_validator("application_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {
            "not_applied",
            "saved",
            "applied",
            "interview",
            "rejected",
            "offer",
        }
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return v


class JobNotesUpdate(BaseModel):
    notes: str


class BoardError(BaseModel):
    board: str
    message: str


class JobSearchResponse(BaseModel):
    source: str
    boards_checked: int
    boards_succeeded: int
    boards_failed: int
    jobs_received: int
    jobs_created: int
    jobs_updated: int
    errors: list[BoardError] = []


class SearchAllRequest(BaseModel):
    sources: list[str] | None = None


class ProviderStatus(BaseModel):
    source: str
    enabled: bool
    configured_sources: int
    last_run_at: datetime | None = None
    last_status: str
    last_jobs_received: int
    last_error: str | None = None


class ProviderRunResponse(BaseModel):
    id: int
    source: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    sources_checked: int
    sources_succeeded: int
    sources_failed: int
    jobs_received: int
    jobs_created: int
    jobs_updated: int
    error_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class JobSummaryResponse(BaseModel):
    total_jobs: int
    not_applied: int
    saved: int
    applied: int
    interviews: int
    rejected: int
    offers: int
    strong_matches: int
