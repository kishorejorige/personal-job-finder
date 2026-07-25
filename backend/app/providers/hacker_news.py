import httpx
import logging
import re
from typing import List, Dict, Any
from app.providers.base import JobProvider, ProviderFetchResult
from app.services.job_parser import detect_remote_status

logger = logging.getLogger(__name__)

HACKER_NEWS_CONFIG = {
    "enabled": True,
    "max_pages": 3,
    "country": "India",
    "remote_only": False,
}

class HackerNewsProvider(JobProvider):
    provider_name = "hacker_news"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or HACKER_NEWS_CONFIG

    async def fetch_jobs(self) -> ProviderFetchResult:
        normalized_jobs = []
        errors = []
        sources_checked = 1
        sources_succeeded = 0
        sources_failed = 0

        if not self.config.get("enabled", True):
            return ProviderFetchResult(
                source=self.provider_name,
                jobs=[],
                sources_checked=0,
                sources_succeeded=0,
                sources_failed=0,
                errors=[]
            )

        max_pages = self.config.get("max_pages", 3)
        country_filter = self.config.get("country")
        remote_only_filter = self.config.get("remote_only", False)

        succeeded_pages = 0
        async with httpx.AsyncClient(timeout=10.0) as client:
            for page in range(max_pages):
                url = f"https://hn.algolia.com/api/v1/search_by_date?tags=job&page={page}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        hits = data.get("hits", [])
                        succeeded_pages += 1
                        
                        for hit in hits:
                            object_id = hit.get("objectID")
                            if not object_id:
                                continue
                            
                            raw_title = hit.get("title", "")
                            job_text = hit.get("job_text") or raw_title
                            original_url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
                            posted_date = hit.get("created_at")

                            # Parse company and job title from the raw_title
                            # E.g. "Bloomy (YC S26) is hiring a founding engineer"
                            # E.g. "DrDroid (YC W23) Is Hiring"
                            company = "Unknown"
                            title = raw_title
                            yc_batch = None

                            # Try to extract YC batch
                            batch_match = re.search(r'\((YC\s+[A-Z]\d{2})\)', raw_title, re.IGNORECASE)
                            if batch_match:
                                yc_batch = batch_match.group(1)

                            # Clean/extract company and job title
                            # Matches "Company (YC Batch) is hiring a Title" or "Company (YC Batch) Is Hiring"
                            hiring_match = re.split(r'\s+(?:is hiring|Is Hiring|hiring|—|\:)\s*', raw_title, maxsplit=1)
                            if len(hiring_match) == 2:
                                company_part = hiring_match[0]
                                title_part = hiring_match[1]
                                
                                # Strip batch from company part
                                company = re.sub(r'\s*\((YC\s+[A-Z]\d{2})\)', '', company_part, flags=re.IGNORECASE).strip()
                                title = title_part.strip()
                            else:
                                # Try extracting from URL slug
                                url_match = re.search(r'ycombinator\.com/companies/([^/]+)', original_url)
                                if url_match:
                                    slug = url_match.group(1)
                                    company = slug.replace("-", " ").title()
                                    # Clean title from batch
                                    title = re.sub(r'\s*\((YC\s+[A-Z]\d{2})\)', '', raw_title, flags=re.IGNORECASE).strip()
                                else:
                                    # Fallback: check if we have parentheses for batch
                                    batch_split = re.split(r'\s*\((YC\s+[A-Z]\d{2})\)', raw_title, flags=re.IGNORECASE, maxsplit=1)
                                    if len(batch_split) > 1:
                                        company = batch_split[0].strip()
                                        title = batch_split[-1].strip() or "Job Posting"

                            # Normalize workplace and location
                            remote_status = detect_remote_status(raw_title, "", job_text)
                            
                            # Filter by remote_only
                            if remote_only_filter and remote_status != "remote":
                                continue

                            # Detect location
                            location = "Unknown"
                            # Try to extract city/state/country from parenthesis or title
                            loc_match = re.search(r'\(([^)]+)\)$', raw_title)
                            if loc_match:
                                potential_loc = loc_match.group(1)
                                if "YC" not in potential_loc:
                                    location = potential_loc
                            
                            # If location is unknown, check if description mentions location
                            if location == "Unknown":
                                if "onsite in " in job_text.lower():
                                    onsite_match = re.search(r'onsite in\s+([a-zA-Z\s,]+)', job_text, re.IGNORECASE)
                                    if onsite_match:
                                        location = onsite_match.group(1).strip()
                            
                            # Filter by country if configured
                            if country_filter:
                                search_area = f"{raw_title} {location} {job_text}".lower()
                                if country_filter.lower() not in search_area:
                                    continue

                            # Parse salary if explicitly displayed (e.g. $100K - $120K)
                            salary = None
                            salary_match = re.search(r'\$[0-9]{2,3}[kK]\s*-\s*\$[0-9]{2,3}[kK]', job_text)
                            if salary_match:
                                salary = salary_match.group(0)
                            else:
                                salary_match_alt = re.search(r'\$[0-9,]{5,7}', job_text)
                                if salary_match_alt:
                                    salary = salary_match_alt.group(0)

                            display_company = f"{company} ({yc_batch})" if yc_batch else company

                            normalized = {
                                "external_id": str(object_id),
                                "title": title,
                                "company_name": display_company,
                                "location": location if location != "Unknown" else None,
                                "remote_status": remote_status,
                                "employment_type": None, # Do not invent employment type
                                "salary": salary,
                                "description": job_text,
                                "source": self.provider_name,
                                "source_board": None,
                                "original_url": original_url,
                                "posted_date": posted_date
                            }
                            normalized_jobs.append(normalized)
                    else:
                        errors.append({"source": self.provider_name, "message": f"HN jobs API HTTP error {response.status_code}"})
                except Exception as e:
                    errors.append({"source": self.provider_name, "message": str(e)})

        if succeeded_pages > 0:
            sources_succeeded = 1
        else:
            sources_failed = 1

        return ProviderFetchResult(
            source=self.provider_name,
            jobs=normalized_jobs,
            sources_checked=sources_checked,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            errors=errors
        )
