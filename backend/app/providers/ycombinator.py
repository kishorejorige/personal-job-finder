import logging
from typing import Any

from app.providers.base import JobProvider, ProviderFetchResult

logger = logging.getLogger(__name__)

YCOMBINATOR_CONFIG = {
    "enabled": False,  # Disabled by default until genuine YC Jobs adapter is implemented
}


class YCombinatorProvider(JobProvider):
    provider_name = "ycombinator"

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or YCOMBINATOR_CONFIG

    async def fetch_jobs(self) -> ProviderFetchResult:
        logger.info("Y Combinator Jobs provider is currently pending implementation.")
        return ProviderFetchResult(
            source=self.provider_name,
            jobs=[],
            sources_checked=1,
            sources_succeeded=0,
            sources_failed=0,
            errors=[
                {
                    "source": self.provider_name,
                    "message": "Genuine YC Jobs adapter is pending implementation.",
                }
            ],
        )
