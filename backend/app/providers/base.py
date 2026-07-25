from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderFetchResult:
    source: str
    jobs: list[dict[str, Any]]
    sources_checked: int
    sources_succeeded: int
    sources_failed: int
    errors: list[dict[str, Any]] = field(default_factory=list)


class JobProvider:
    provider_name: str

    async def fetch_jobs(self) -> ProviderFetchResult:
        """
        Fetches jobs from the provider.
        Returns a ProviderFetchResult.
        """
        raise NotImplementedError("Subclasses must implement fetch_jobs")
