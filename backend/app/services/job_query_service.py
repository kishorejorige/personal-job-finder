from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Query
from app.models.job import Job

def resolve_status_filter(status: Optional[str]) -> Optional[List[str]]:
    """
    Map report groups or custom status filters to a list of matching DB application_status values.
    """
    if not status or status == "all":
        return None
    if status == "applied":
        return ["applied"]
    if status == "non_applied":
        return ["not_applied", "saved"]
    if status == "saved":
        return ["saved"]
    if status == "interview":
        return ["interview"]
    if status == "rejected":
        return ["rejected"]
    if status == "offer":
        return ["offer"]
    if status == "application_activity":
        return ["applied", "interview", "rejected", "offer"]
    return [status]

def apply_job_filters(
    query: Query,
    search: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    remote_status: Optional[str] = None,
    application_status: Optional[str] = None,
    status_filter: Optional[str] = None,
    source: Optional[str] = None,
    include_duplicates: bool = False,
    minimum_match_score: Optional[int] = None,
    posted_after: Optional[str] = None
) -> Query:
    """
    Applies common filters to a Job query.
    """
    # 1. Search filter
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Job.title.ilike(search_filter) |
            Job.company_name.ilike(search_filter) |
            Job.location.ilike(search_filter) |
            Job.description.ilike(search_filter) |
            Job.skills.ilike(search_filter)
        )

    # 2. Company name filter
    if company:
        query = query.filter(Job.company_name.ilike(f"%{company}%"))

    # 3. Location filter
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))

    # 4. Remote Status filter
    if remote_status:
        query = query.filter(Job.remote_status == remote_status)

    # 5. Application Status grouping/filters
    statuses = None
    if status_filter:
        # report endpoint status grouping
        statuses = resolve_status_filter(status_filter)
    elif application_status:
        # direct UI job query status
        statuses = resolve_status_filter(application_status)

    if statuses is not None:
        query = query.filter(Job.application_status.in_(statuses))

    # 6. Source filter
    if source:
        source_list = [s.strip() for s in source.split(",") if s.strip()]
        if source_list:
            query = query.filter(Job.source.in_(source_list))

    # 7. Duplicate inclusion/exclusion
    if not include_duplicates:
        query = query.filter(Job.duplicate_of_id.is_(None))

    # 8. Minimum match score filter
    if minimum_match_score is not None:
        query = query.filter(Job.match_score >= minimum_match_score)

    # 9. Posted after date filter (YYYY-MM-DD)
    if posted_after:
        try:
            dt = datetime.strptime(posted_after.strip(), "%Y-%m-%d")
            query = query.filter(Job.posted_date >= dt)
        except Exception:
            pass

    return query

def apply_job_sorting(
    query: Query,
    sort_by: str = "match_score",
    sort_order: str = "desc"
) -> Query:
    """
    Applies common sorting rules to a Job query.
    """
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
    return query
