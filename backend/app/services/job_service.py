import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.profile import Profile
from app.providers.greenhouse import GreenhouseProvider
from app.services.job_parser import clean_html, detect_remote_status, extract_skills_from_text
from app.services.job_matcher import calculate_match

logger = logging.getLogger(__name__)

async def search_and_sync_greenhouse(db: Session) -> dict:
    """
    Crawls public Greenhouse boards, normalizes job structures,
    evaluates matches, and persists them while preserving user details.
    """
    provider = GreenhouseProvider()

    # 1. Fetch raw jobs and stats from provider
    raw_jobs, stats = await provider.fetch_jobs()

    # 2. Get active profile
    profile = db.query(Profile).first()

    jobs_created = 0
    jobs_updated = 0

    for raw in raw_jobs:
        cleaned_desc = clean_html(raw["description"])
        detected_skills = extract_skills_from_text(f"{raw['title']} {cleaned_desc}")
        detected_remote = detect_remote_status(raw["title"], raw["location"], cleaned_desc)

        match_result = calculate_match(
            job_title=raw["title"],
            job_description=cleaned_desc,
            job_skills=detected_skills,
            job_remote=detected_remote,
            job_location=raw["location"],
            profile=profile
        )

        # Duplicate check: check source + external_id first
        existing = None
        if raw["external_id"]:
            existing = db.query(Job).filter(
                Job.source == raw["source"],
                Job.external_id == raw["external_id"]
            ).first()
        else:
            existing = db.query(Job).filter(
                Job.company_name == raw["company_name"],
                Job.title == raw["title"],
                Job.original_url == raw["original_url"]
            ).first()

        skills_str = json.dumps(detected_skills)
        matched_str = json.dumps(match_result["matched_skills"])
        missing_str = json.dumps(match_result["missing_skills"])

        if existing:
            # Update current details, keep application tracking fields intact
            existing.title = raw["title"]
            existing.location = raw["location"]
            existing.remote_status = detected_remote
            existing.description = cleaned_desc
            existing.skills = skills_str
            existing.matched_skills = matched_str
            existing.missing_skills = missing_str
            existing.match_score = match_result["match_score"]
            existing.original_url = raw["original_url"]
            existing.posted_date = raw["posted_date"]
            existing.last_seen_at = datetime.utcnow()

            jobs_updated += 1
        else:
            # Create a new job record
            new_job = Job(
                external_id=raw["external_id"],
                title=raw["title"],
                company_name=raw["company_name"],
                location=raw["location"],
                remote_status=detected_remote,
                description=cleaned_desc,
                skills=skills_str,
                matched_skills=matched_str,
                missing_skills=missing_str,
                source=raw["source"],
                source_board=raw["source_board"],
                original_url=raw["original_url"],
                posted_date=raw["posted_date"],
                match_score=match_result["match_score"],
                application_status="not_applied",
                last_seen_at=datetime.utcnow()
            )
            db.add(new_job)
            jobs_created += 1

    db.commit()

    stats["jobs_received"] = len(raw_jobs)
    stats["jobs_created"] = jobs_created
    stats["jobs_updated"] = jobs_updated

    return stats

def recalculate_all_job_matches(db: Session) -> int:
    """
    Recalculates matches for all jobs in the database.
    Usually triggered when a user updates their resume profile.
    """
    profile = db.query(Profile).first()
    jobs = db.query(Job).all()

    count = 0
    for job in jobs:
        try:
            job_skills = json.loads(job.skills) if job.skills else []
        except Exception:
            job_skills = []

        match_result = calculate_match(
            job_title=job.title,
            job_description=job.description or "",
            job_skills=job_skills,
            job_remote=job.remote_status or "unknown",
            job_location=job.location or "Unknown",
            profile=profile
        )

        job.matched_skills = json.dumps(match_result["matched_skills"])
        job.missing_skills = json.dumps(match_result["missing_skills"])
        job.match_score = match_result["match_score"]
        count += 1

    db.commit()
    return count
