from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.job import Job
from app.schemas.job import (
    JobListResponse,
    JobNotesUpdate,
    JobResponse,
    JobSearchResponse,
    JobStatusUpdate,
    JobSummaryResponse
)
from app.services.job_service import (
    recalculate_all_job_matches,
    search_and_sync_greenhouse
)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.post("/search/greenhouse", response_model=JobSearchResponse)
async def search_greenhouse(db: Session = Depends(get_db)):
    """
    Crawls Greenhouse boards and saves/updates jobs matching against the user resume.
    """
    try:
        stats = await search_and_sync_greenhouse(db)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Greenhouse job crawl failed: {str(e)}"
        )

@router.get("", response_model=JobListResponse)
def get_jobs(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search keyword in title, company, description, or skills"),
    company: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_status: Optional[str] = Query(None),
    application_status: Optional[str] = Query(None),
    minimum_match_score: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    sort_by: str = Query("match_score"),
    sort_order: str = Query("desc")
):
    query = db.query(Job)

    # Filtering
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Job.title.ilike(search_filter) |
            Job.company_name.ilike(search_filter) |
            Job.location.ilike(search_filter) |
            Job.description.ilike(search_filter) |
            Job.skills.ilike(search_filter)
        )
    if company:
        query = query.filter(Job.company_name.ilike(f"%{company}%"))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if remote_status:
        query = query.filter(Job.remote_status == remote_status)
    if application_status:
        query = query.filter(Job.application_status == application_status)
    if minimum_match_score is not None:
        query = query.filter(Job.match_score >= minimum_match_score)

    # Sorting Column Mapping
    sort_map = {
        "match_score": Job.match_score,
        "created_at": Job.created_at,
        "company": Job.company_name,
        "title": Job.title
    }
    sort_column = sort_map.get(sort_by, Job.match_score)

    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    total_pages = max((total + page_size - 1) // page_size, 1)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/summary", response_model=JobSummaryResponse)
def get_jobs_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated stats on application statuses and strong matches for dashboard display.
    """
    total_jobs = db.query(Job).count()
    not_applied = db.query(Job).filter(Job.application_status == "not_applied").count()
    saved = db.query(Job).filter(Job.application_status == "saved").count()
    applied = db.query(Job).filter(Job.application_status == "applied").count()
    interviews = db.query(Job).filter(Job.application_status == "interview").count()
    rejected = db.query(Job).filter(Job.application_status == "rejected").count()
    offers = db.query(Job).filter(Job.application_status == "offer").count()
    strong_matches = db.query(Job).filter(Job.match_score >= 80).count()

    return {
        "total_jobs": total_jobs,
        "not_applied": not_applied,
        "saved": saved,
        "applied": applied,
        "interviews": interviews,
        "rejected": rejected,
        "offers": offers,
        "strong_matches": strong_matches
    }

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found."
        )
    return job

@router.patch("/{job_id}/status", response_model=JobResponse)
def update_job_status(job_id: int, status_update: JobStatusUpdate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found."
        )

    new_status = status_update.application_status
    job.application_status = new_status

    if new_status == "applied" and not job.applied_date:
        job.applied_date = datetime.utcnow()
    # Note: Transitioning away from "applied" preserves the history of applied_date to keep it simple.

    db.commit()
    db.refresh(job)
    return job

@router.patch("/{job_id}/notes", response_model=JobResponse)
def update_job_notes(job_id: int, notes_update: JobNotesUpdate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found."
        )

    job.notes = notes_update.notes
    db.commit()
    db.refresh(job)
    return job

@router.post("/recalculate-matches")
def recalculate_matches(db: Session = Depends(get_db)):
    """
    Recalculates profile match scores for all stored job entries.
    """
    try:
        count = recalculate_all_job_matches(db)
        return {"message": f"Successfully recalculated matches for {count} jobs."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate matches: {str(e)}"
        )

@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found."
        )

    db.delete(job)
    db.commit()
    return {"message": f"Job {job_id} has been deleted."}
