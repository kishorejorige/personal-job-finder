import json

from pydantic import BaseModel, ConfigDict, field_validator


class ProfileBase(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    professional_title: str | None = None
    professional_summary: str | None = None
    career_objective: str | None = None
    total_experience: str | None = None
    current_company: str | None = None
    current_role: str | None = None
    preferred_job_role: str | None = None
    preferred_location: str | None = None
    availability: str | None = None
    occupation_category: str | None = None
    additional_information: str | None = None
    resume_quality: str | None = None


class ProfileUpdate(ProfileBase):
    skills: list[str] | None = []
    work_experience: list[str] | None = []
    education: list[str] | None = []
    projects: list[str] | None = []
    certifications: list[str] | None = []
    technical_skills: list[str] | None = []
    soft_skills: list[str] | None = []
    languages: list[str] | None = []
    achievements: list[str] | None = []
    training: list[str] | None = []
    internships: list[str] | None = []
    licences: list[str] | None = []
    tools_and_equipment: list[str] | None = []

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str | None) -> str | None:
        if v:
            v = v.strip()
            if v and ("@" not in v or "." not in v):
                raise ValueError("Invalid email format")
        return v


class ProfileResponse(ProfileBase):
    id: int
    skills: list[str] = []
    work_experience: list[str] = []
    education: list[str] = []
    projects: list[str] = []
    certifications: list[str] = []
    technical_skills: list[str] = []
    soft_skills: list[str] = []
    languages: list[str] = []
    achievements: list[str] = []
    training: list[str] = []
    internships: list[str] = []
    licences: list[str] = []
    tools_and_equipment: list[str] = []
    resume_filename: str | None = None
    resume_text: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "skills",
        "work_experience",
        "education",
        "projects",
        "certifications",
        "technical_skills",
        "soft_skills",
        "languages",
        "achievements",
        "training",
        "internships",
        "licences",
        "tools_and_equipment",
        mode="before",
    )
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
