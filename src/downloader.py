import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def download_pdf(
    arxiv_id: str,
    output_dir: str,
    delay: float = 3.0,
    timeout: int = 120,
) -> bool:
    """Download a single PDF from arXiv. Returns True on success."""
    output_path = Path(output_dir) / f"{arxiv_id}.pdf"

    if output_path.exists() and output_path.stat().st_size > 0:
        logger.debug("Already exists: %s", arxiv_id)
        return True

    urls = [
        f"https://arxiv.org/pdf/{arxiv_id}",
        f"https://arxiv.org/pdf/{arxiv_id}v1",
    ]

    try:
        resp = None
        for url in urls:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "avatar-papers-collector/1.0"},
                allow_redirects=True,
            )
            if resp.status_code != 404:
                break
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type and len(resp.content) < 1000:
            logger.warning("Unexpected response for %s: %s", arxiv_id, content_type)
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(resp.content)
        logger.info("Downloaded: %s (%.1f KB)", arxiv_id, len(resp.content) / 1024)
        time.sleep(delay)
        return True
    except requests.RequestException as exc:
        logger.error("Failed to download %s: %s", arxiv_id, exc)
        return False
