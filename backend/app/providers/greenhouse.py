import httpx
import logging
from typing import List, Dict, Any
from app.providers.base import JobProvider, ProviderFetchResult
from app.providers.greenhouse_boards import GREENHOUSE_BOARDS

logger = logging.getLogger(__name__)

class GreenhouseProvider(JobProvider):
    provider_name = "greenhouse"

    def __init__(self, boards: List[Dict[str, str]] = None):
        self.boards = boards or GREENHOUSE_BOARDS

    async def fetch_jobs(self) -> ProviderFetchResult:
        """
        Fetches public jobs from configured Greenhouse boards.
        Returns a ProviderFetchResult.
        """
        normalized_jobs = []
        errors = []
        sources_checked = len(self.boards)
        sources_succeeded = 0
        sources_failed = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            for board in self.boards:
                company = board["company_name"]
                token = board["board_token"]
                url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

                response_data = None
                succeeded = False

                # Try up to 2 times (1 retry for temporary errors)
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
                                errors.append({"board": token, "message": err_msg})
                    except (httpx.RequestError, httpx.TimeoutException) as e:
                        err_msg = f"Network failure: {str(e)}"
                        if attempt == 1:
                            errors.append({"board": token, "message": err_msg})

                if succeeded and response_data and "jobs" in response_data:
                    sources_succeeded += 1
                    for job in response_data["jobs"]:
                        loc_data = job.get("location")
                        location_name = loc_data.get("name") if loc_data else "Unknown"

                        normalized = {
                            "external_id": str(job.get("id")),
                            "title": job.get("title", ""),
                            "company_name": company,
                            "location": location_name,
                            "original_url": job.get("absolute_url", ""),
                            "description": job.get("content", ""),  # HTML is cleaned in the job_parser service
                            "posted_date": job.get("updated_at"),
                            "source": self.provider_name,
                            "source_board": token
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
