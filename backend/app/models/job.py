from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    remote_status = Column(String, nullable=True, default="unknown")  # remote, hybrid, onsite, unknown
    employment_type = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Serialized JSON lists
    skills = Column(Text, nullable=True)          # List of detected skills
    matched_skills = Column(Text, nullable=True)  # Intersection with resume
    missing_skills = Column(Text, nullable=True)  # Skills required but not in resume

    source = Column(String, nullable=False)       # e.g., 'greenhouse'
    source_board = Column(String, nullable=True)  # Company board token
    original_url = Column(String, nullable=True)
    posted_date = Column(String, nullable=True)

    match_score = Column(Integer, default=0, index=True)
    application_status = Column(String, default="not_applied", index=True) # not_applied, saved, applied, etc.
    applied_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    job_fingerprint = Column(String, nullable=True, index=True)
    duplicate_of_id = Column(Integer, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('source', 'external_id', name='uq_source_external_id'),
    )
