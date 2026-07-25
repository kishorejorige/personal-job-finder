import httpx
import logging
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser
from typing import List, Dict, Any
from app.providers.base import JobProvider, ProviderFetchResult
from app.providers.company_career_sites import COMPANY_CAREER_SITES
from app.services.job_parser import detect_remote_status

logger = logging.getLogger(__name__)

# URL Safety Check: only allow http/https, reject javascript:, data:, file:
def is_safe_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https")

# HTML Parser Node tree structure to support generic CSS-like selector queries
class HTMLNode:
    def __init__(self, tag: str, attrs: list, parent=None):
        self.tag = tag.lower()
        self.attrs = {k.lower(): v for k, v in attrs}
        self.parent = parent
        self.children = []
        self.text = ""

    def get_attr(self, name: str) -> str:
        return self.attrs.get(name.lower(), "")

    def match_selector(self, selector: str) -> bool:
        if not selector:
            return False
        
        # Simple class selector: e.g. "div.job-card" or ".job-title"
        if "." in selector:
            parts = selector.split(".")
            tag_part = parts[0].lower()
            class_part = parts[1].lower()
            
            # Verify tag part
            if tag_part and self.tag != tag_part:
                return False
            
            # Verify class part
            classes = self.attrs.get("class", "").lower().split()
            if class_part not in classes:
                return False
            return True
        else:
            # Tag only: e.g. "a" or "h3"
            return self.tag == selector.lower()

    def find_all(self, selector: str) -> List['HTMLNode']:
        results = []
        if self.match_selector(selector):
            results.append(self)
        for child in self.children:
            results.extend(child.find_all(selector))
        return results

    def find(self, selector: str) -> 'HTMLNode':
        if self.match_selector(selector):
            return self
        for child in self.children:
            found = child.find(selector)
            if found:
                return found
        return None

class SimpleTreeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = HTMLNode("root", [])
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = HTMLNode(tag, attrs, self.current)
        self.current.children.append(node)
        # Skip self-closing tags
        if tag not in ("img", "br", "hr", "input", "meta", "link"):
            self.current = node

    def handle_endtag(self, tag):
        if self.current.parent and self.current.tag == tag.lower():
            self.current = self.current.parent

    def handle_data(self, data):
        if self.current:
            self.current.text += data

class CompanyCareersProvider(JobProvider):
    provider_name = "company_careers"

    def __init__(self, sites: List[Dict[str, Any]] = None):
        self.sites = sites or COMPANY_CAREER_SITES

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
                url = site["careers_url"]
                adapter = site["adapter"]

                response_data = None
                succeeded = False

                for attempt in range(2):
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            response_data = response.text
                            succeeded = True
                            break
                        else:
                            err_msg = f"HTTP error {response.status_code}"
                            if attempt == 1:
                                errors.append({"site": company, "message": err_msg})
                    except (httpx.RequestError, httpx.TimeoutException) as e:
                        err_msg = f"Network failure: {str(e)}"
                        if attempt == 1:
                            errors.append({"site": company, "message": err_msg})

                if not succeeded:
                    sources_failed += 1
                    continue

                # Run specific adapter logic
                try:
                    site_jobs = []
                    if adapter == "json_ld":
                        site_jobs = self._parse_json_ld(response_data, company, url)
                    elif adapter == "rss":
                        site_jobs = self._parse_rss(response_data, company, url)
                    elif adapter == "generic_html":
                        selectors = site.get("selectors", {})
                        site_jobs = self._parse_generic_html(response_data, company, url, selectors)
                    else:
                        raise ValueError(f"Unknown adapter {adapter}")

                    # Filter and normalize URL safety
                    safe_jobs = []
                    for job in site_jobs:
                        orig_url = job.get("original_url")
                        if not orig_url or is_safe_url(orig_url):
                            safe_jobs.append(job)
                        else:
                            logger.warning(f"Rejected unsafe URL: {orig_url} in job {job.get('title')}")

                    normalized_jobs.extend(safe_jobs)
                    sources_succeeded += 1
                except Exception as e:
                    sources_failed += 1
                    logger.error(f"Error parsing site {company} with adapter {adapter}: {str(e)}")
                    errors.append({"site": company, "message": f"Adapter error ({adapter}): {str(e)}"})

        return ProviderFetchResult(
            source=self.provider_name,
            jobs=normalized_jobs,
            sources_checked=sources_checked,
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            errors=errors
        )

    def _parse_json_ld(self, html_content: str, company: str, base_url: str) -> List[Dict[str, Any]]:
        jobs = []
        # Find all JSON-LD script blocks
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        scripts = re.findall(pattern, html_content, flags=re.DOTALL | re.IGNORECASE)

        for script_text in scripts:
            try:
                data = json.loads(script_text.strip())
                # Normalize structure if list or graph
                postings = []
                if isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        postings.append(data)
                    elif "@graph" in data:
                        for g in data["@graph"]:
                            if g.get("@type") == "JobPosting":
                                postings.append(g)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            postings.append(item)

                for post in postings:
                    title = post.get("title", "")
                    desc = post.get("description", "")
                    
                    # Company
                    hiring_org = post.get("hiringOrganization")
                    org_name = company
                    if isinstance(hiring_org, dict):
                        org_name = hiring_org.get("name", company)

                    # Location
                    loc_val = "Unknown"
                    job_loc = post.get("jobLocation")
                    if isinstance(job_loc, dict):
                        address = job_loc.get("address")
                        if isinstance(address, dict):
                            parts = []
                            for field in ("addressLocality", "addressRegion", "addressCountry"):
                                if address.get(field):
                                    parts.append(address.get(field))
                            if parts:
                                loc_val = ", ".join(parts)
                        elif isinstance(address, str):
                            loc_val = address

                    # Remote status
                    remote_status = detect_remote_status(title, loc_val, desc)
                    loc_type = post.get("jobLocationType")
                    if isinstance(loc_type, str) and loc_type.upper() == "TELECOMMUTE":
                        remote_status = "remote"

                    # Original URL
                    job_url = post.get("url") or base_url

                    # External ID
                    identifier = post.get("identifier")
                    ext_id = None
                    if isinstance(identifier, dict):
                        ext_id = identifier.get("value")
                    elif isinstance(identifier, str):
                        ext_id = identifier
                    
                    if not ext_id:
                        ext_id = job_url

                    # Salary
                    salary = None
                    base_sal = post.get("baseSalary")
                    if isinstance(base_sal, dict):
                        val = base_sal.get("value")
                        curr = base_sal.get("currency", "USD")
                        if isinstance(val, dict):
                            min_val = val.get("minValue")
                            max_val = val.get("maxValue")
                            if min_val and max_val:
                                salary = f"{curr} {min_val} - {max_val}"
                            elif val.get("value"):
                                salary = f"{curr} {val.get('value')}"
                        elif val:
                            salary = f"{curr} {val}"

                    normalized = {
                        "external_id": str(ext_id),
                        "title": title,
                        "company_name": org_name,
                        "location": loc_val,
                        "remote_status": remote_status,
                        "employment_type": post.get("employmentType"),
                        "salary": salary,
                        "description": desc,
                        "source": self.provider_name,
                        "source_board": None,
                        "original_url": job_url,
                        "posted_date": post.get("datePosted")
                    }
                    jobs.append(normalized)
            except Exception as e:
                logger.warning(f"Error parsing script tag JSON-LD: {str(e)}")

        return jobs

    def _parse_rss(self, xml_content: str, company: str, base_url: str) -> List[Dict[str, Any]]:
        jobs = []
        root = ET.fromstring(xml_content.strip())
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []

        for item in items:
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            pubdate_elem = item.find("pubDate")
            guid_elem = item.find("guid")

            raw_title = title_elem.text if title_elem is not None else ""
            original_url = link_elem.text if link_elem is not None else base_url
            description = desc_elem.text if desc_elem is not None else ""
            posted_date = pubdate_elem.text if pubdate_elem is not None else None
            
            guid_val = guid_elem.text if guid_elem is not None else None
            external_id = guid_val or original_url

            if not raw_title:
                continue

            remote_status = detect_remote_status(raw_title, "", description)

            normalized = {
                "external_id": str(external_id),
                "title": raw_title,
                "company_name": company,
                "location": "Unknown",
                "remote_status": remote_status,
                "employment_type": None,
                "salary": None,
                "description": description,
                "source": self.provider_name,
                "source_board": None,
                "original_url": original_url,
                "posted_date": posted_date
            }
            jobs.append(normalized)
        return jobs

    def _parse_generic_html(self, html_content: str, company: str, base_url: str, selectors: dict) -> List[Dict[str, Any]]:
        jobs = []
        job_item_sel = selectors.get("job_item_selector")
        title_sel = selectors.get("title_selector")
        location_sel = selectors.get("location_selector")
        url_sel = selectors.get("url_selector")

        if not job_item_sel or not title_sel:
            raise ValueError("Generic HTML adapter requires both job_item_selector and title_selector")

        parser = SimpleTreeParser()
        parser.feed(html_content)
        
        # Find all job card nodes
        item_nodes = parser.root.find_all(job_item_sel)

        for node in item_nodes:
            # Title
            title_node = node.find(title_sel)
            title = title_node.text.strip() if title_node else ""
            if not title:
                continue

            # Location
            location = "Unknown"
            if location_sel:
                loc_node = node.find(location_sel)
                if loc_node:
                    location = loc_node.text.strip()

            # URL
            original_url = base_url
            if url_sel:
                url_node = node.find(url_sel)
                if url_node:
                    href = url_node.get_attr("href")
                    if href:
                        original_url = urljoin(base_url, href)
            else:
                # If no url_selector, search for any "a" child node with href
                link_node = node.find("a")
                if link_node:
                    href = link_node.get_attr("href")
                    if href:
                        original_url = urljoin(base_url, href)

            remote_status = detect_remote_status(title, location, "")

            # Create an ID based on fingerprint if not present
            ext_id = original_url

            normalized = {
                "external_id": ext_id,
                "title": title,
                "company_name": company,
                "location": location,
                "remote_status": remote_status,
                "employment_type": None,
                "salary": None,
                "description": f"Job opportunity at {company}. Check original page for details.",
                "source": self.provider_name,
                "source_board": None,
                "original_url": original_url,
                "posted_date": None
            }
            jobs.append(normalized)

        return jobs
