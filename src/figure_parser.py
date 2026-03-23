import json
import logging
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

ARXIV_HTML_BASE = "https://arxiv.org/html"


class _FigureHTMLParser(HTMLParser):
    """Extract <figure> blocks with images and captions from arXiv HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.in_figure = False
        self.in_figcaption = False
        self.figures: List[Dict] = []
        self._current: Dict = {}
        self._caption_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = dict(attrs)
        if tag == "figure":
            self.in_figure = True
            self._current = {"id": a.get("id", ""), "images": []}
        elif tag == "img" and self.in_figure:
            src = a.get("src", "")
            alt = a.get("alt", "")
            if src and not src.startswith("data:"):
                self._current["images"].append({"src": src, "alt": alt})
        elif tag == "figcaption":
            self.in_figcaption = True
            self._caption_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_figcaption:
            self._caption_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "figcaption":
            self.in_figcaption = False
            if self.in_figure:
                raw = " ".join("".join(self._caption_parts).split())
                self._current["caption"] = raw
        elif tag == "figure" and self.in_figure:
            self.in_figure = False
            if self._current.get("images"):
                self.figures.append(self._current)


def _find_html_version(arxiv_id: str) -> Optional[str]:
    """Return the arXiv HTML page URL if it exists, else None."""
    for version in ("v1", "v2", "v3"):
        url = f"{ARXIV_HTML_BASE}/{arxiv_id}{version}"
        try:
            resp = requests.head(
                url, timeout=10, allow_redirects=True,
                headers={"User-Agent": "avatar-papers-collector/1.0"},
            )
            if resp.status_code == 200:
                return url
        except requests.RequestException:
            pass
    return None


def parse_figures(arxiv_id: str) -> Optional[List[Dict]]:
    """Fetch arXiv HTML and extract figures with absolute image URLs.

    Returns a list of dicts: {index, url, caption} or None if no HTML version.
    """
    html_url = _find_html_version(arxiv_id)
    if not html_url:
        logger.debug("No HTML version for %s", arxiv_id)
        return None

    try:
        resp = requests.get(
            html_url, timeout=30,
            headers={"User-Agent": "avatar-papers-collector/1.0"},
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch HTML for %s: %s", arxiv_id, exc)
        return None

    parser = _FigureHTMLParser()
    parser.feed(resp.text)

    page_url = html_url.rstrip("/")
    figures: List[Dict] = []

    for idx, fig in enumerate(parser.figures, start=1):
        img = fig["images"][0]
        src = (img["src"] or "").strip()
        if src.startswith("http"):
            abs_url = src
        elif src.startswith(arxiv_id):
            abs_url = f"{ARXIV_HTML_BASE}/{src}"
        else:
            abs_url = f"{page_url}/{src.lstrip('/')}"

        figures.append({
            "index": idx,
            "url": abs_url,
            "caption": fig.get("caption", ""),
        })

    logger.info("Parsed %d figures from HTML for %s", len(figures), arxiv_id)
    return figures


def save_figures_meta(
    arxiv_id: str,
    figures: List[Dict],
    output_dir: str,
) -> Path:
    """Save figures metadata to JSON file."""
    out_path = Path(output_dir) / f"{arxiv_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(figures, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def load_figures_meta(arxiv_id: str, figures_dir: str) -> Optional[List[Dict]]:
    """Load previously saved figures metadata."""
    path = Path(figures_dir) / f"{arxiv_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
