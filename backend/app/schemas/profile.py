import json
from typing import List, Optional
from pydantic import BaseModel, field_validator, ConfigDict

class ProfileBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    professional_title: Optional[str] = None
    professional_summary: Optional[str] = None

class ProfileUpdate(ProfileBase):
    skills: Optional[List[str]] = []
    work_experience: Optional[List[str]] = []
    education: Optional[List[str]] = []
    projects: Optional[List[str]] = []
    certifications: Optional[List[str]] = []

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip()
            if v and ("@" not in v or "." not in v):
                raise ValueError("Invalid email format")
        return v

class ProfileResponse(ProfileBase):
    id: int
    skills: List[str] = []
    work_experience: List[str] = []
    education: List[str] = []
    projects: List[str] = []
    certifications: List[str] = []
    resume_filename: Optional[str] = None
    resume_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('skills', 'work_experience', 'education', 'projects', 'certifications', mode='before')
    @classmethod
    def parse_json_strings(cls, v):
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

class ResumeUploadResponse(BaseModel):
    message: str
    profile: ProfileResponse
