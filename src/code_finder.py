import logging
import re
import time
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

GITHUB_SEARCH_API = "https://api.github.com/search/repositories"
GITHUB_RATE_LIMIT_DELAY = 6.5

AGGREGATOR_PATTERNS = [
    r"arxiv[_-]?daily",
    r"daily[_-]?arxiv",
    r"papers[_-]?with[_-]?code",
    r"awesome[_-]",
    r"reading[_-]?papers",
    r"paper[_-]?list",
    r"cv[_-]?arxiv",
    r"ai4(physics|chem)",
    r"paper.+design.+using",
]
_AGGREGATOR_RE = re.compile("|".join(AGGREGATOR_PATTERNS), re.IGNORECASE)


def _is_aggregator(repo: dict) -> bool:
    """Detect arxiv aggregator / paper-list repositories."""
    full_name = repo.get("full_name", "")
    description = repo.get("description", "") or ""
    return bool(_AGGREGATOR_RE.search(full_name) or _AGGREGATOR_RE.search(description))


def find_code_url(arxiv_id: str, delay: float = 1.0) -> Optional[str]:
    """Search GitHub for the paper's own code repository.

    Filters out arxiv aggregator repos. Returns the URL of the most-starred
    genuine repository or None.
    """
    actual_delay = max(delay, GITHUB_RATE_LIMIT_DELAY)
    url = _search_github(arxiv_id)
    time.sleep(actual_delay)
    return url


def _search_github(arxiv_id: str) -> Optional[str]:
    """Query GitHub search API and filter out aggregator repos."""
    try:
        resp = requests.get(
            GITHUB_SEARCH_API,
            params={
                "q": f"{arxiv_id}",
                "sort": "stars",
                "order": "desc",
                "per_page": 10,
            },
            timeout=15,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "avatar-papers-collector/1.0",
            },
        )

        if resp.status_code == 403:
            logger.warning("GitHub rate limit hit, skipping %s", arxiv_id)
            return None

        resp.raise_for_status()
        items: List[dict] = resp.json().get("items", [])

        for repo in items:
            if _is_aggregator(repo):
                continue
            url = repo.get("html_url", "")
            if url:
                logger.info("Found code for %s: %s", arxiv_id, url)
                return url

        return None

    except requests.RequestException as exc:
        logger.warning("GitHub search failed for %s: %s", arxiv_id, exc)
        return None
