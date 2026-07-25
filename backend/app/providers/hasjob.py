import httpx
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from app.providers.base import JobProvider, ProviderFetchResult
from app.services.job_parser import detect_remote_status

logger = logging.getLogger(__name__)

HASJOB_CONFIG = {
    "enabled": True,
    "location": "India",
}

class HasjobProvider(JobProvider):
    provider_name = "hasjob"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or HASJOB_CONFIG

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

        url = "https://hasjob.co/feed"
        response_data = None
        succeeded = False

        # Try up to 2 times (1 retry for temporary errors)
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url)
                if response.status_code == 200:
                    response_data = response.text
                    succeeded = True
                    break
                else:
                    err_msg = f"HTTP error {response.status_code} from Hasjob RSS"
                    if attempt == 1:
                        errors.append({"source": "hasjob", "message": err_msg})
            except (httpx.RequestError, httpx.TimeoutException) as e:
                err_msg = f"Network failure: {str(e)}"
                if attempt == 1:
                    errors.append({"source": "hasjob", "message": err_msg})

        if succeeded and response_data:
            try:
                root = ET.fromstring(response_data)
                channel = root.find("channel")
                items = channel.findall("item") if channel is not None else []
                sources_succeeded += 1

                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    pubdate_elem = item.find("pubDate")
                    guid_elem = item.find("guid")

                    raw_title = title_elem.text if title_elem is not None else ""
                    original_url = link_elem.text if link_elem is not None else ""
                    description = desc_elem.text if desc_elem is not None else ""
                    posted_date = pubdate_elem.text if pubdate_elem is not None else None
                    
                    # Guid or link hash for external_id
                    guid_val = guid_elem.text if guid_elem is not None else None
                    external_id = guid_val or original_url.split("/")[-1] or original_url

                    if not raw_title:
                        continue

                    # Parse company and job title
                    # Hasjob titles are usually format: "Software Engineer at Hasgeek" or "Software Engineer (Remote) at Hasgeek"
                    company = "Unknown"
                    title = raw_title
                    parts = re.split(r'\s+at\s+', raw_title, flags=re.IGNORECASE, maxsplit=1)
                    if len(parts) == 2:
                        title = parts[0].strip()
                        company = parts[1].strip()

                    # Remote Status
                    remote_status = detect_remote_status(raw_title, "", description)

                    # Try to extract location from categories or description
                    location = "Unknown"
                    category_elems = item.findall("category")
                    categories = [cat.text for cat in category_elems if cat.text]
                    if categories:
                        location = ", ".join(categories)

                    # Filter by location configuration if specified
                    loc_filter = self.config.get("location")
                    if loc_filter:
                        search_area = f"{raw_title} {location} {description}".lower()
                        if loc_filter.lower() not in search_area:
                            continue

                    normalized = {
                        "external_id": str(external_id),
                        "title": title,
                        "company_name": company,
                        "location": location,
                        "remote_status": remote_status,
                        "employment_type": None,
                        "salary": None,
                        "description": description,
                        "source": self.provider_name,
                        "source_board": None,
                        "original_url": original_url,
                        "posted_date": posted_date
                    }
                    normalized_jobs.append(normalized)
            except Exception as e:
                sources_failed += 1
                logger.error(f"Error parsing Hasjob RSS XML: {str(e)}")
                errors.append({"source": "hasjob", "message": f"RSS Parse error: {str(e)}"})
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
