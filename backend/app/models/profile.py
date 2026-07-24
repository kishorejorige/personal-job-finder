from sqlalchemy import Column, Integer, String, Text, DateTime
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
    skills = Column(Text, nullable=True)           # e.g., '["Python", "FastAPI"]'
    work_experience = Column(Text, nullable=True)  # e.g., '["Google - Software Dev (2020-2022)"]'
    education = Column(Text, nullable=True)        # e.g., '["BS Computer Science"]'
    projects = Column(Text, nullable=True)         # e.g., '["Job Finder App"]'
    certifications = Column(Text, nullable=True)   # e.g., '["AWS Certified Developer"]'

    resume_filename = Column(String, nullable=True)
    resume_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
