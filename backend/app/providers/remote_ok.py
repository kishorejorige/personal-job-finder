import httpx
import logging
from typing import List, Dict, Any
from app.providers.base import JobProvider, ProviderFetchResult

logger = logging.getLogger(__name__)

class RemoteOkProvider(JobProvider):
    provider_name = "remote_ok"

    async def fetch_jobs(self) -> ProviderFetchResult:
        normalized_jobs = []
        errors = []
        sources_checked = 1
        sources_succeeded = 0
        sources_failed = 0

        # Remote OK requires a clear User-Agent header or returns 403
        headers = {
            "User-Agent": "PersonalJobFinder/1.0 (contact: support@personaljobfinder.local)"
        }
        url = "https://remoteok.com/api"

        response_data = None
        succeeded = False

        # Try up to 2 times (1 retry for temporary errors)
        for attempt in range(2):
            try:
                response = await httpx.AsyncClient(timeout=15.0).get(url, headers=headers)
                if response.status_code == 200:
                    response_data = response.json()
                    succeeded = True
                    break
                elif response.status_code == 429:
                    err_msg = "Rate limited by Remote OK (HTTP 429)"
                    if attempt == 1:
                        errors.append({"source": "remote_ok", "message": err_msg})
                else:
                    err_msg = f"HTTP error {response.status_code} from Remote OK"
                    if attempt == 1:
                        errors.append({"source": "remote_ok", "message": err_msg})
            except (httpx.RequestError, httpx.TimeoutException) as e:
                err_msg = f"Network failure: {str(e)}"
                if attempt == 1:
                    errors.append({"source": "remote_ok", "message": err_msg})

        if succeeded and isinstance(response_data, list):
            sources_succeeded += 1
            for item in response_data:
                # First element in Remote OK response is usually a legal/info text dict, e.g. {"legal": "..."}
                if not isinstance(item, dict) or "legal" in item or "id" not in item:
                    continue
                
                # Verify that it is indeed a job listing (must have position and company)
                job_id = item.get("id")
                position = item.get("position")
                company = item.get("company")
                if not job_id or not position or not company:
                    continue

                # Salary parsing
                salary = None
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                if salary_min or salary_max:
                    salary = f"${salary_min or 0} - ${salary_max or 0}"
                
                # Tags mapping to skills
                skills = item.get("tags", [])
                if not isinstance(skills, list):
                    skills = []

                normalized = {
                    "external_id": str(job_id),
                    "title": position,
                    "company_name": company,
                    "location": item.get("location", "Remote"),
                    "remote_status": "remote", # remote_ok jobs are remote
                    "employment_type": None, # feed does not explicitly have commitment
                    "salary": salary,
                    "description": item.get("description", ""),
                    "skills": skills,
                    "source": self.provider_name,
                    "source_board": None,
                    "original_url": item.get("url", ""),
                    "posted_date": item.get("date")
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
