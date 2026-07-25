from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.models.profile import Profile
from app.services.job_query_service import apply_job_filters, apply_job_sorting
from app.services.pdf_exporter import create_jobs_pdf, create_single_job_pdf, create_application_summary_pdf
from app.services.csv_exporter import create_jobs_csv

router = APIRouter()

def get_report_title(status_str: str) -> str:
    """
    Format report headers based on the status category.
    """
    titles = {
        "all": "All Jobs Report",
        "applied": "Applied Jobs Report",
        "non_applied": "Non-Applied Jobs Report",
        "saved": "Saved Jobs Report",
        "interview": "Interview Stage Jobs Report",
        "rejected": "Rejected Jobs Report",
        "offer": "Offer Stage Jobs Report",
        "application_activity": "Application Activity Report"
    }
    return titles.get(status_str.lower(), f"{status_str.replace('_', ' ').title()} Jobs Report")

@router.get("/jobs.pdf")
def export_jobs_pdf(
    db: Session = Depends(get_db),
    status: str = Query("all"),
    search: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    minimum_match_score: Optional[int] = Query(None),
    posted_after: Optional[str] = Query(None),
    sort_by: str = Query("match_score"),
    sort_order: str = Query("desc"),
    include_duplicates: bool = Query(False)
):
    """
    Exports a PDF report matching status and query filters.
    """
    query = db.query(Job)

    # Apply shared filters (note we map report status to status_filter)
    query = apply_job_filters(
        query=query,
        search=search,
        company=company,
        location=location,
        remote_status=remote_status,
        status_filter=status,
        source=source,
        include_duplicates=include_duplicates,
        minimum_match_score=minimum_match_score,
        posted_after=posted_after
    )

    # Apply sorting
    query = apply_job_sorting(
        query=query,
        sort_by=sort_by,
        sort_order=sort_order
    )

    jobs = query.all()
    profile = db.query(Profile).first()

    title = get_report_title(status)
    pdf_bytes = create_jobs_pdf(jobs, title, profile)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"personal-job-finder-{status}-jobs-{date_str}.pdf"

    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Access-Control-Expose-Headers": "Content-Disposition"
    }

    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/jobs.csv")
def export_jobs_csv(
    db: Session = Depends(get_db),
    status: str = Query("all"),
    search: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    minimum_match_score: Optional[int] = Query(None),
    posted_after: Optional[str] = Query(None),
    sort_by: str = Query("match_score"),
    sort_order: str = Query("desc"),
    include_duplicates: bool = Query(False)
):
    """
    Exports a CSV report matching status and query filters.
    """
    query = db.query(Job)

    # Apply shared filters
    query = apply_job_filters(
        query=query,
        search=search,
        company=company,
        location=location,
        remote_status=remote_status,
        status_filter=status,
        source=source,
        include_duplicates=include_duplicates,
        minimum_match_score=minimum_match_score,
        posted_after=posted_after
    )

    # Apply sorting
    query = apply_job_sorting(
        query=query,
        sort_by=sort_by,
        sort_order=sort_order
    )

    jobs = query.all()
    csv_bytes = create_jobs_csv(jobs)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"personal-job-finder-{status}-jobs-{date_str}.csv"

    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Access-Control-Expose-Headers": "Content-Disposition"
    }

    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)

@router.get("/jobs/{job_id}.pdf")
def export_single_job_pdf(job_id: int, db: Session = Depends(get_db)):
    """
    Exports details of a single job post in portrait PDF format.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found."
        )

    profile = db.query(Profile).first()
    pdf_bytes = create_single_job_pdf(job, profile)

    filename = f"job-details-{job_id}.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Access-Control-Expose-Headers": "Content-Disposition"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/application-summary.pdf")
def export_application_summary(db: Session = Depends(get_db)):
    """
    Exports tracking summary report.
    """
    jobs = db.query(Job).filter(Job.duplicate_of_id.is_(None)).all()
    profile = db.query(Profile).first()

    pdf_bytes = create_application_summary_pdf(jobs, profile)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"personal-job-finder-application-summary-{date_str}.pdf"

    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Access-Control-Expose-Headers": "Content-Disposition"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
