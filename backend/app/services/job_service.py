import json
import logging
import asyncio
import re
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.models.job import Job
from app.models.profile import Profile
from app.models.provider_run import ProviderRun
from app.services.job_parser import clean_html, detect_remote_status, extract_skills_from_text
from app.services.job_matcher import calculate_match

# Import base provider and implementations
from app.providers import (
    JobProvider,
    ProviderFetchResult,
    GreenhouseProvider,
    LeverProvider,
    AshbyProvider,
    RemoteOkProvider,
    YCombinatorProvider,
    HasjobProvider,
    CompanyCareersProvider
)
from app.providers.config import PROVIDER_SETTINGS

logger = logging.getLogger(__name__)

# Priority map for duplicate resolution (preferred sources first)
SOURCE_PRIORITY = ["company_careers", "greenhouse", "lever", "ashby", "ycombinator", "hacker_news", "hasjob", "remote_ok"]

def generate_fingerprint(company: str, title: str, location: str) -> str:
    def normalize(text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        # Remove non-alphanumeric and collapse whitespaces
        text = re.sub(r'[^a-z0-9]', ' ', text)
        return " ".join(text.split())

    c = normalize(company)
    t = normalize(title)
    l = normalize(location or "unknown")
    return f"{c}|{t}|{l}"

def resolve_duplicates(db: Session):
    """
    Groups jobs by fingerprint and updates duplicate_of_id to point to
    the preferred source record, preserving other records as duplicates.
    """
    jobs = db.query(Job).all()
    groups = {}
    for j in jobs:
        if j.job_fingerprint:
            groups.setdefault(j.job_fingerprint, []).append(j)

    for fp, group in groups.items():
        if len(group) <= 1:
            for j in group:
                j.duplicate_of_id = None
            continue

        def get_priority(job):
            try:
                return SOURCE_PRIORITY.index(job.source)
            except ValueError:
                return 99

        # Sort ascending (lower index = higher priority)
        sorted_group = sorted(group, key=get_priority)
        main_job = sorted_group[0]
        main_job.duplicate_of_id = None

        for duplicate_job in sorted_group[1:]:
            duplicate_job.duplicate_of_id = main_job.id

    db.commit()

async def process_and_save_jobs(db: Session, raw_jobs: list[dict], source_name: str) -> tuple[int, int]:
    """
    Transforms, matches, and persists raw jobs into the database.
    """
    profile = db.query(Profile).first()
    jobs_created = 0
    jobs_updated = 0

    for raw in raw_jobs:
        raw_desc = raw.get("description") or ""
        cleaned_desc = clean_html(raw_desc)
        detected_skills = extract_skills_from_text(f"{raw.get('title', '')} {cleaned_desc}")

        # Merge pre-extracted tags if provider provides them
        if "skills" in raw and isinstance(raw["skills"], list):
            detected_skills = sorted(list(set(detected_skills + raw["skills"])))

        detected_remote = raw.get("remote_status") or "unknown"
        if detected_remote == "unknown":
            detected_remote = detect_remote_status(raw.get("title", ""), raw.get("location", ""), cleaned_desc)

        match_result = calculate_match(
            job_title=raw.get("title", ""),
            job_description=cleaned_desc,
            job_skills=detected_skills,
            job_remote=detected_remote,
            job_location=raw.get("location") or "Unknown",
            profile=profile
        )

        fingerprint = generate_fingerprint(
            company=raw.get("company_name", ""),
            title=raw.get("title", ""),
            location=raw.get("location", "")
        )

        # Duplicate check: check source + external_id first
        existing = None
        ext_id = raw.get("external_id")
        if ext_id:
            existing = db.query(Job).filter(
                Job.source == raw["source"],
                Job.external_id == ext_id
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
            # Update details but preserve application tracking fields
            existing.title = raw.get("title", "")
            existing.location = raw.get("location")
            existing.remote_status = detected_remote
            existing.description = cleaned_desc
            existing.skills = skills_str
            existing.matched_skills = matched_str
            existing.missing_skills = missing_str
            existing.match_score = match_result["match_score"]
            existing.original_url = raw.get("original_url")
            existing.posted_date = raw.get("posted_date")
            existing.job_fingerprint = fingerprint
            existing.last_seen_at = datetime.now(UTC)

            jobs_updated += 1
        else:
            new_job = Job(
                external_id=ext_id,
                title=raw.get("title", ""),
                company_name=raw.get("company_name", ""),
                location=raw.get("location"),
                remote_status=detected_remote,
                employment_type=raw.get("employment_type"),
                salary=raw.get("salary"),
                description=cleaned_desc,
                skills=skills_str,
                matched_skills=matched_str,
                missing_skills=missing_str,
                source=raw["source"],
                source_board=raw.get("source_board"),
                original_url=raw.get("original_url"),
                posted_date=raw.get("posted_date"),
                match_score=match_result["match_score"],
                application_status="not_applied",
                job_fingerprint=fingerprint,
                last_seen_at=datetime.now(UTC)
            )
            db.add(new_job)
            jobs_created += 1

    db.commit()
    return jobs_created, jobs_updated

def create_provider(provider_name: str) -> JobProvider:
    if provider_name == "greenhouse":
        return GreenhouseProvider()
    elif provider_name == "lever":
        return LeverProvider()
    elif provider_name == "ashby":
        return AshbyProvider()
    elif provider_name == "remote_ok":
        return RemoteOkProvider()
    elif provider_name == "ycombinator":
        return YCombinatorProvider()
    elif provider_name == "hacker_news":
        from app.providers.hacker_news import HackerNewsProvider
        return HackerNewsProvider()
    elif provider_name == "hasjob":
        return HasjobProvider()
    elif provider_name == "company_careers":
        return CompanyCareersProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

async def refresh_all_job_sources(db: Session, sources: list[str] = None, force: bool = False) -> dict:
    """
    Refreshes selected job sources concurrently, normalizes jobs,
    runs matching, saves runs history, and groups duplicates.
    """
    started_at = datetime.now(UTC)

    # Cooldown check
    if not force:
        latest_run = db.query(ProviderRun).filter(
            ProviderRun.source == "all",
            ProviderRun.status == "success"
        ).order_by(ProviderRun.completed_at.desc()).first()
        if latest_run and latest_run.completed_at:
            time_diff = (started_at - latest_run.completed_at.replace(tzinfo=UTC)).total_seconds()
            if time_diff < 600: # 10 minutes
                raise ValueError("A refresh was completed recently. Use force=true to refresh again.")

    available_providers = ["greenhouse", "lever", "ashby", "remote_ok", "ycombinator", "hacker_news", "hasjob", "company_careers"]
    if sources:
        run_sources = [s for s in sources if s in available_providers]
    else:
        run_sources = available_providers

    enabled_sources = [s for s in run_sources if PROVIDER_SETTINGS.get(s, {}).get("enabled", True)]

    provider_results = []
    total_received = 0
    total_created = 0
    total_updated = 0
    providers_succeeded = 0
    providers_failed = 0

    # 3 concurrent providers at a time
    sem = asyncio.Semaphore(3)

    async def run_one(src: str):
        nonlocal total_received, total_created, total_updated, providers_succeeded, providers_failed
        async with sem:
            run_started = datetime.now(UTC)
            status = "success"
            errors_list = []
            jobs_rcvd = 0
            jobs_cre = 0
            jobs_upd = 0
            sources_checked = 0
            sources_succeeded = 0
            sources_failed_count = 0

            try:
                provider = create_provider(src)
                result = await provider.fetch_jobs()

                # Check for legacy tuple format: (jobs, stats) from existing tests
                if isinstance(result, tuple):
                    jobs_list = result[0]
                    stats_dict = result[1]
                    jobs_rcvd = len(jobs_list)
                    sources_checked = stats_dict.get("boards_checked", 0)
                    sources_succeeded = stats_dict.get("boards_succeeded", 0)
                    sources_failed_count = stats_dict.get("boards_failed", 0)
                    errors_list = stats_dict.get("errors", [])
                else:
                    jobs_list = result.jobs
                    jobs_rcvd = len(result.jobs)
                    sources_checked = result.sources_checked
                    sources_succeeded = result.sources_succeeded
                    sources_failed_count = result.sources_failed
                    errors_list = result.errors

                # Insert/update jobs in DB
                jobs_cre, jobs_upd = await process_and_save_jobs(db, jobs_list, src)

                total_received += jobs_rcvd
                total_created += jobs_cre
                total_updated += jobs_upd

                if not isinstance(result, tuple):
                    if result.sources_failed > 0:
                        if result.sources_succeeded > 0:
                            status = "partial_success"
                        else:
                            status = "failed"
                else:
                    if sources_failed_count > 0:
                        if sources_succeeded > 0:
                            status = "partial_success"
                        else:
                            status = "failed"

                if status in ("success", "partial_success"):
                    providers_succeeded += 1
                else:
                    providers_failed += 1

            except Exception as e:
                status = "failed"
                providers_failed += 1
                err_msg = str(e)
                errors_list = [{"source": src, "message": err_msg}]
                sources_checked = 1
                sources_succeeded = 0
                sources_failed_count = 1
                logger.error(f"Failed running provider {src}: {err_msg}", exc_info=True)

            completed_time = datetime.now(UTC)
            error_summary_str = json.dumps(errors_list) if errors_list else None

            p_run = ProviderRun(
                source=src,
                started_at=run_started,
                completed_at=completed_time,
                status=status,
                sources_checked=sources_checked,
                sources_succeeded=sources_succeeded,
                sources_failed=sources_failed_count,
                jobs_received=jobs_rcvd,
                jobs_created=jobs_cre,
                jobs_updated=jobs_upd,
                error_summary=error_summary_str
            )
            db.add(p_run)
            db.commit()

            provider_results.append({
                "source": src,
                "status": status,
                "sources_checked": sources_checked,
                "sources_succeeded": sources_succeeded,
                "sources_failed": sources_failed_count,
                "jobs_received": jobs_rcvd,
                "jobs_created": jobs_cre,
                "jobs_updated": jobs_upd,
                "errors": errors_list
            })

    if enabled_sources:
        await asyncio.gather(*(run_one(src) for src in enabled_sources))

        # Post-sync duplicate grouping
        resolve_duplicates(db)

    completed_at = datetime.now(UTC)

    # Save overall run log
    overall_status = "success"
    if providers_failed > 0:
        if providers_succeeded > 0:
            overall_status = "partial_success"
        else:
            overall_status = "failed"

    all_run = ProviderRun(
        source="all",
        started_at=started_at,
        completed_at=completed_at,
        status=overall_status,
        sources_checked=len(enabled_sources),
        sources_succeeded=providers_succeeded,
        sources_failed=providers_failed,
        jobs_received=total_received,
        jobs_created=total_created,
        jobs_updated=total_updated,
        error_summary=None
    )
    db.add(all_run)
    db.commit()

    return {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "total_jobs_received": total_received,
        "jobs_created": total_created,
        "jobs_updated": total_updated,
        "providers_succeeded": providers_succeeded,
        "providers_failed": providers_failed,
        "provider_results": provider_results
    }

async def search_and_sync_greenhouse(db: Session) -> dict:
    """
    Crawls Greenhouse boards (backward compatibility wrapper).
    """
    res = await refresh_all_job_sources(db, sources=["greenhouse"], force=True)
    for r in res["provider_results"]:
        if r["source"] == "greenhouse":
            errors = []
            for err in r["errors"]:
                errors.append({"board": err.get("board") or "greenhouse", "message": err.get("message")})
            return {
                "source": "greenhouse",
                "boards_checked": r["sources_checked"],
                "boards_succeeded": r["sources_succeeded"],
                "boards_failed": r["sources_failed"],
                "jobs_received": r["jobs_received"],
                "jobs_created": r["jobs_created"],
                "jobs_updated": r["jobs_updated"],
                "errors": errors
            }
    return {
        "source": "greenhouse",
        "boards_checked": 0,
        "boards_succeeded": 0,
        "boards_failed": 0,
        "jobs_received": 0,
        "jobs_created": 0,
        "jobs_updated": 0,
        "errors": []
    }

def recalculate_all_job_matches(db: Session) -> int:
    """
    Recalculates matches for all jobs in the database.
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
