import csv
import io
import json
from datetime import datetime
from typing import Any

from app.models.job import Job


def format_date(dt: Any) -> str:
    """
    Format datetime objects cleanly as YYYY-MM-DD HH:MM:SS or return raw values.
    """
    if not dt:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def parse_skills_list(skills_json: Any) -> str:
    """
    Safely deserializes skills list from JSON and joins them using ' | '.
    """
    if not skills_json:
        return ""
    try:
        arr = json.loads(skills_json)
        if isinstance(arr, list):
            return " | ".join(str(s).strip() for s in arr if str(s).strip())
    except Exception:
        pass
    return str(skills_json)


def sanitize_cell(value: Any) -> Any:
    """
    Escapes cells starting with formula trigger symbols (=, +, -, @)
    by prepending an apostrophe to prevent CSV formula injection.
    """
    if isinstance(value, str):
        if value.startswith(("=", "+", "-", "@")):
            return "'" + value
    return value


def create_jobs_csv(jobs: list[Job]) -> bytes:
    """
    Creates a CSV containing details of all target jobs.
    Uses UTF-8 encoding with a BOM (utf-8-sig) to ensure Excel compatibility on Windows.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # 1. Write Header Row
    headers = [
        "id",
        "match_score",
        "job_title",
        "company_name",
        "location",
        "remote_status",
        "employment_type",
        "salary",
        "source",
        "source_board",
        "posted_date",
        "application_status",
        "applied_date",
        "matched_skills",
        "missing_skills",
        "notes",
        "original_url",
        "created_at",
        "updated_at",
        "last_seen_at",
    ]
    writer.writerow(headers)

    # 2. Write Data Rows
    for job in jobs:
        matched_sk = parse_skills_list(job.matched_skills)
        missing_sk = parse_skills_list(job.missing_skills)

        row = [
            job.id,
            job.match_score if job.match_score is not None else "",
            job.title or "",
            job.company_name or "",
            job.location or "",
            job.remote_status or "",
            job.employment_type or "",
            job.salary or "",
            job.source or "",
            job.source_board or "",
            format_date(job.posted_date),
            job.application_status or "not_applied",
            format_date(job.applied_date),
            matched_sk,
            missing_sk,
            job.notes or "",
            job.original_url or "",
            format_date(job.created_at),
            format_date(job.updated_at),
            format_date(job.last_seen_at),
        ]
        sanitized_row = [sanitize_cell(cell) for cell in row]
        writer.writerow(sanitized_row)

    # Get string content
    csv_string = output.getvalue()
    output.close()

    # Encode as UTF-8 with BOM (utf-8-sig)
    return csv_string.encode("utf-8-sig")
