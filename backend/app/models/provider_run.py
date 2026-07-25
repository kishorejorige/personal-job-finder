from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class ProviderRun(Base):
    __tablename__ = "provider_runs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False) # success, partial_success, failed, disabled, running
    sources_checked = Column(Integer, default=0)
    sources_succeeded = Column(Integer, default=0)
    sources_failed = Column(Integer, default=0)
    jobs_received = Column(Integer, default=0)
    jobs_created = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    error_summary = Column(Text, nullable=True)
