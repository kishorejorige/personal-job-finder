from datetime import UTC, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.job import Job
from app.models.provider_run import ProviderRun
from app.schemas.job import (
    JobListResponse,
    JobNotesUpdate,
    JobResponse,
    JobSearchResponse,
    JobStatusUpdate,
    JobSummaryResponse,
    SearchAllRequest,
    ProviderStatus,
    ProviderRunResponse
)
from app.services.job_service import (
    recalculate_all_job_matches,
    search_and_sync_greenhouse,
    refresh_all_job_sources
)
from app.providers.config import PROVIDER_SETTINGS
from app.providers.greenhouse_boards import GREENHOUSE_BOARDS
from app.providers.lever_sites import LEVER_SITES
from app.providers.ashby_boards import ASHBY_BOARDS
from app.providers.company_career_sites import COMPANY_CAREER_SITES

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.post("/search/all")
async def search_all(
    payload: Optional[SearchAllRequest] = None,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    Refreshes jobs from all enabled (or specified) providers concurrently.
    """
    sources = payload.sources if payload else None
    try:
        res = await refresh_all_job_sources(db, sources=sources, force=force)
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refetch failed: {str(e)}"
        )

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

@router.post("/search/{provider}")
async def search_single_provider(
    provider: str,
    force: bool = True,
    db: Session = Depends(get_db)
):
    """
    Runs search sync for a single provider.
    """
    provider_key = provider.replace("-", "_")
    valid_providers = ["greenhouse", "lever", "ashby", "remote_ok", "ycombinator", "hacker_news", "hasjob", "company_careers"]
    if provider_key not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}"
        )

    try:
        res = await refresh_all_job_sources(db, sources=[provider_key], force=force)
        # Return summary of this provider
        for result in res.get("provider_results", []):
            if result["source"] == provider_key:
                return result
        return {
            "source": provider,
            "status": "disabled",
            "sources_checked": 0,
            "sources_succeeded": 0,
            "sources_failed": 0,
            "jobs_received": 0,
            "jobs_created": 0,
            "jobs_updated": 0,
            "errors": []
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crawl for provider {provider} failed: {str(e)}"
        )

@router.get("", response_model=JobListResponse)
def get_jobs(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search keyword in title, company, description, or skills"),
    company: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_status: Optional[str] = Query(None),
    application_status: Optional[str] = Query(None),
    source: Optional[str] = Query(None, description="Filter by one or more sources, comma-separated"),
    include_duplicates: bool = Query(False, description="Whether to include duplicate job postings"),
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
    if source:
        source_list = [s.strip() for s in source.split(",") if s.strip()]
        if source_list:
            query = query.filter(Job.source.in_(source_list))
    if not include_duplicates:
        query = query.filter(Job.duplicate_of_id.is_(None))
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

@router.get("/providers", response_model=List[ProviderStatus])
def get_providers(db: Session = Depends(get_db)):
    """
    Returns the status and configuration data of all job sources.
    """
    providers = ["greenhouse", "lever", "ashby", "remote_ok", "ycombinator", "hacker_news", "hasjob", "company_careers"]
    result = []

    for p in providers:
        enabled = PROVIDER_SETTINGS.get(p, {}).get("enabled", True)

        # Determine configured sources count
        if p == "greenhouse":
            configured_sources = len(GREENHOUSE_BOARDS)
        elif p == "lever":
            configured_sources = len([s for s in LEVER_SITES if s.get("enabled", True)])
        elif p == "ashby":
            configured_sources = len([b for b in ASHBY_BOARDS if b.get("enabled", True)])
        elif p == "remote_ok":
            configured_sources = 1 if enabled else 0
        elif p == "ycombinator":
            configured_sources = 1 if enabled else 0
        elif p == "hacker_news":
            configured_sources = 1 if enabled else 0
        elif p == "hasjob":
            configured_sources = 1 if enabled else 0
        elif p == "company_careers":
            configured_sources = len([s for s in COMPANY_CAREER_SITES if s.get("enabled", True)])
        else:
            configured_sources = 0

        # Query last run details
        last_run = db.query(ProviderRun).filter(ProviderRun.source == p).order_by(ProviderRun.completed_at.desc()).first()

        if last_run:
            result.append({
                "source": p,
                "enabled": enabled,
                "configured_sources": configured_sources,
                "last_run_at": last_run.completed_at,
                "last_status": last_run.status,
                "last_jobs_received": last_run.jobs_received,
                "last_error": last_run.error_summary
            })
        else:
            result.append({
                "source": p,
                "enabled": enabled,
                "configured_sources": configured_sources,
                "last_run_at": None,
                "last_status": "never_run",
                "last_jobs_received": 0,
                "last_error": None
            })

    return result

@router.get("/provider-runs", response_model=List[ProviderRunResponse])
def get_provider_runs(
    source: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns a history of provider sync runs.
    """
    query = db.query(ProviderRun)
    if source:
        query = query.filter(ProviderRun.source == source)
    return query.order_by(ProviderRun.started_at.desc()).limit(limit).all()

@router.get("/summary", response_model=JobSummaryResponse)
def get_jobs_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated stats on application statuses and strong matches for dashboard display.
    """
    total_jobs = db.query(Job).filter(Job.duplicate_of_id.is_(None)).count()
    not_applied = db.query(Job).filter(Job.duplicate_of_id.is_(None), Job.application_status == "not_applied").count()
    saved = db.query(Job).filter(Job.duplicate_of_id.is_(None), Job.application_status == "saved").count()
    applied = db.query(Job).filter(Job.duplicate_of_id.is_(None), Job.application_status == "applied").count()
    interviews = db.query(Job).filter(Job.duplicate_of_id.is_(None), Job.application_status == "interview").count()
    rejected = db.query(Job).filter(Job.duplicate_of_id.is_(None), Job.application_status == "rejected").count()
    offers = db.query(Job).filter(Job.duplicate_of_id.is_(None), Job.application_status == "offer").count()
    strong_matches = db.query(Job).filter(Job.duplicate_of_id.is_(None), Job.match_score >= 80).count()

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
        job.applied_date = datetime.now(UTC)
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
