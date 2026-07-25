import httpx
import logging
from datetime import datetime, UTC
from typing import List, Dict, Any
from app.providers.base import JobProvider, ProviderFetchResult
from app.providers.lever_sites import LEVER_SITES

logger = logging.getLogger(__name__)

class LeverProvider(JobProvider):
    provider_name = "lever"

    def __init__(self, sites: List[Dict[str, Any]] = None):
        self.sites = sites or LEVER_SITES

    async def fetch_jobs(self) -> ProviderFetchResult:
        normalized_jobs = []
        errors = []
        enabled_sites = [site for site in self.sites if site.get("enabled", True)]
        sources_checked = len(enabled_sites)
        sources_succeeded = 0
        sources_failed = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            for site in enabled_sites:
                company = site["company_name"]
                site_name = site["site_name"]
                region = site.get("region", "global")
                
                # Select correct Lever API hostname
                if region == "eu":
                    url = f"https://api.eu.lever.co/v0/postings/{site_name}?mode=json"
                else:
                    url = f"https://api.lever.co/v0/postings/{site_name}?mode=json"

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
                                errors.append({"site": site_name, "message": err_msg})
                    except (httpx.RequestError, httpx.TimeoutException) as e:
                        err_msg = f"Network failure: {str(e)}"
                        if attempt == 1:
                            errors.append({"site": site_name, "message": err_msg})

                if succeeded and isinstance(response_data, list):
                    sources_succeeded += 1
                    for job in response_data:
                        categories = job.get("categories", {})
                        location = categories.get("location", "Unknown")
                        employment_type = categories.get("commitment", "")
                        
                        # Build combined description (description + lists + additional)
                        desc_parts = []
                        if "description" in job:
                            desc_parts.append(job["description"])
                        for lst in job.get("lists", []):
                            if isinstance(lst, dict):
                                desc_parts.append(f"<h3>{lst.get('title', '')}</h3>\n{lst.get('content', '')}")
                        if "additional" in job:
                            desc_parts.append(job["additional"])
                        description = "\n".join(desc_parts)

                        # Posted date parsing
                        posted_date = None
                        created_at_ts = job.get("createdAt")
                        if created_at_ts:
                            try:
                                posted_date = datetime.fromtimestamp(created_at_ts / 1000.0, UTC).isoformat()
                            except Exception:
                                pass

                        # workplaceType mapping
                        workplace = job.get("workplaceType", "").lower()
                        remote_status = "unknown"
                        if workplace in ("remote", "hybrid", "onsite"):
                            remote_status = workplace
                        elif workplace == "on-site":
                            remote_status = "onsite"

                        # Extract salary if present
                        salary = None
                        salary_info = job.get("salary")
                        if salary_info:
                            # If it's a dict, e.g. {"amount": 100000, "currency": "USD"}
                            if isinstance(salary_info, dict):
                                amt = salary_info.get("amount")
                                curr = salary_info.get("currency", "USD")
                                if amt:
                                    salary = f"{curr} {amt}"
                            else:
                                salary = str(salary_info)

                        normalized = {
                            "external_id": str(job.get("id")),
                            "title": job.get("title", ""),
                            "company_name": company,
                            "location": location,
                            "remote_status": remote_status,
                            "employment_type": employment_type,
                            "salary": salary,
                            "description": description,
                            "source": self.provider_name,
                            "source_board": site_name,
                            "original_url": job.get("hostedUrl", ""),
                            "posted_date": posted_date
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
