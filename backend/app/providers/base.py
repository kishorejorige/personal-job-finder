from typing import List, Dict, Any

class JobProvider:
    provider_name: str

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetches jobs from the provider.
        Returns a list of normalized job dicts.
        """
        raise NotImplementedError("Subclasses must implement fetch_jobs")
