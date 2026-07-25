from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    professional_title = Column(String, nullable=True)
    professional_summary = Column(Text, nullable=True)

    # List fields stored as JSON strings
    skills = Column(Text, nullable=True)  # e.g., '["Python", "FastAPI"]'
    work_experience = Column(Text, nullable=True)  # e.g., '["Google - Software Dev (2020-2022)"]'
    education = Column(Text, nullable=True)  # e.g., '["BS Computer Science"]'
    projects = Column(Text, nullable=True)  # e.g., '["Job Finder App"]'
    certifications = Column(Text, nullable=True)  # e.g., '["AWS Certified Developer"]'

    # New fields for expanded resume parsing support
    career_objective = Column(Text, nullable=True)
    total_experience = Column(String, nullable=True)
    current_company = Column(String, nullable=True)
    current_role = Column(String, nullable=True)
    preferred_job_role = Column(String, nullable=True)
    preferred_location = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    occupation_category = Column(String, nullable=True)

    # Expanded list fields stored as JSON strings
    technical_skills = Column(Text, nullable=True)
    soft_skills = Column(Text, nullable=True)
    languages = Column(Text, nullable=True)
    achievements = Column(Text, nullable=True)
    training = Column(Text, nullable=True)
    internships = Column(Text, nullable=True)
    licences = Column(Text, nullable=True)
    tools_and_equipment = Column(Text, nullable=True)

    additional_information = Column(Text, nullable=True)
    resume_quality = Column(String, nullable=True)

    resume_filename = Column(String, nullable=True)
    resume_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
