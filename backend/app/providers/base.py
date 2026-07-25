from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class ProviderFetchResult:
    source: str
    jobs: List[Dict[str, Any]]
    sources_checked: int
    sources_succeeded: int
    sources_failed: int
    errors: List[Dict[str, Any]] = field(default_factory=list)

class JobProvider:
    provider_name: str

    async def fetch_jobs(self) -> ProviderFetchResult:
        """
        Fetches jobs from the provider.
        Returns a ProviderFetchResult.
        """
        raise NotImplementedError("Subclasses must implement fetch_jobs")
