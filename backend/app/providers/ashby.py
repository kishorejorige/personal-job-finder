import httpx
import logging
from typing import List, Dict, Any
from app.providers.base import JobProvider, ProviderFetchResult
from app.providers.ashby_boards import ASHBY_BOARDS

logger = logging.getLogger(__name__)

class AshbyProvider(JobProvider):
    provider_name = "ashby"

    def __init__(self, boards: List[Dict[str, Any]] = None):
        self.boards = boards or ASHBY_BOARDS

    async def fetch_jobs(self) -> ProviderFetchResult:
        normalized_jobs = []
        errors = []
        enabled_boards = [board for board in self.boards if board.get("enabled", True)]
        sources_checked = len(enabled_boards)
        sources_succeeded = 0
        sources_failed = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            for board in enabled_boards:
                company = board["company_name"]
                board_name = board["job_board_name"]
                url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}?includeCompensation=true"

                response_data = None
                succeeded = False

                # Retry up to 2 times (1 retry for temporary errors)
                for attempt in range(2):
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            response_data = response.json()
                            succeeded = True
                            break
                        else:
                            err_msg = f"HTTP error {response.status_code}"
                            if attempt == 1:
                                errors.append({"board": board_name, "message": err_msg})
                    except (httpx.RequestError, httpx.TimeoutException) as e:
                        err_msg = f"Network failure: {str(e)}"
                        if attempt == 1:
                            errors.append({"board": board_name, "message": err_msg})

                if succeeded and isinstance(response_data, dict) and "jobs" in response_data:
                    sources_succeeded += 1
                    for job in response_data["jobs"]:
                        job_id = job.get("id") or job.get("uuid")
                        if not job_id:
                            continue

                        # Location and Remote Status mapping
                        location = job.get("location", "Unknown")
                        
                        # Determine remote status
                        remote_status = "unknown"
                        is_remote_val = job.get("isRemote")
                        if isinstance(is_remote_val, bool):
                            remote_status = "remote" if is_remote_val else "onsite"
                        
                        workplace = job.get("workplaceType", "").lower()
                        if workplace in ("remote", "hybrid", "onsite"):
                            remote_status = workplace

                        # Extract compensation summary
                        salary = None
                        comp = job.get("compensation")
                        if isinstance(comp, dict):
                            salary = comp.get("compensationTierSummary")

                        # description
                        description = job.get("descriptionHtml") or job.get("descriptionPlain") or ""

                        # original job URL
                        original_url = job.get("jobUrl") or job.get("applyUrl")
                        if not original_url:
                            original_url = f"https://jobs.ashbyhq.com/{board_name}/{job_id}"

                        normalized = {
                            "external_id": str(job_id),
                            "title": job.get("title", ""),
                            "company_name": company,
                            "location": location,
                            "remote_status": remote_status,
                            "employment_type": job.get("employmentType"),
                            "salary": salary,
                            "description": description,
                            "source": self.provider_name,
                            "source_board": board_name,
                            "original_url": original_url,
                            "posted_date": job.get("publishedAt")
                        }
                        normalized_jobs.append(normalized)
                else:
                    if not succeeded:
                        sources_failed += 1

        return ProviderFetchResult(
            source=self.provider_name,
            jobs=normalized_jobs,
            sources_checked=sources_checked,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            errors=errors
        )
