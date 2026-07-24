import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator, ConfigDict

class JobBase(BaseModel):
    title: str
    company_name: str
    location: Optional[str] = None
    remote_status: Optional[str] = "unknown"
    employment_type: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None
    source: str
    source_board: Optional[str] = None
    original_url: Optional[str] = None
    posted_date: Optional[str] = None
    match_score: int = 0
    application_status: str = "not_applied"
    applied_date: Optional[datetime] = None
    notes: Optional[str] = None

class JobResponse(JobBase):
    id: int
    skills: List[str] = []
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('skills', 'matched_skills', 'missing_skills', mode='before')
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
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class JobStatusUpdate(BaseModel):
    application_status: str

    @field_validator('application_status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"not_applied", "saved", "applied", "interview", "rejected", "offer"}
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
    errors: List[BoardError] = []

class JobSummaryResponse(BaseModel):
    total_jobs: int
    not_applied: int
    saved: int
    applied: int
    interviews: int
    rejected: int
    offers: int
    strong_matches: int
