import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class PublishState:
    """Tracks what has been published to Confluence.

    Stores page IDs, lock flags for weekly pages, and content hashes
    for year tables to avoid redundant API calls.
    """

    def __init__(self, path: str = "data/publish_state.json") -> None:
        self._path = Path(path)
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupted publish state, starting fresh")
        return {"weekly": {}, "years": {}, "index_hash": ""}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── weekly pages ────────────────────────────────────────────

    def _week_key(self, year: str, w_start: str, w_end: str) -> str:
        return f"{year}/{w_start}_{w_end}"

    def is_week_locked(self, year: str, w_start: str, w_end: str) -> bool:
        key = self._week_key(year, w_start, w_end)
        return self._data.get("weekly", {}).get(key, {}).get("locked", False)

    def set_week(
        self,
        year: str,
        w_start: str,
        w_end: str,
        en_page_id: str,
        ru_page_id: str,
        locked: bool,
    ) -> None:
        key = self._week_key(year, w_start, w_end)
        self._data.setdefault("weekly", {})[key] = {
            "en_page_id": en_page_id,
            "ru_page_id": ru_page_id,
            "locked": locked,
        }

    # ── year tables ─────────────────────────────────────────────

    def get_year_hash(self, year: str) -> str:
        return self._data.get("years", {}).get(year, {}).get("hash", "")

    def get_year_state(self, year: str) -> Dict[str, Any]:
        """Return cached year state ({en_page_id, ru_page_id, hash}) or empty dict."""
        return self._data.get("years", {}).get(year, {})

    def set_year(
        self,
        year: str,
        en_page_id: str,
        ru_page_id: str,
        content_hash: str,
    ) -> None:
        self._data.setdefault("years", {})[year] = {
            "en_page_id": en_page_id,
            "ru_page_id": ru_page_id,
            "hash": content_hash,
        }

    # ── index page ──────────────────────────────────────────────

    def get_index_hash(self) -> str:
        return self._data.get("index_hash", "")

    def set_index_hash(self, h: str) -> None:
        self._data["index_hash"] = h

    # ── helpers ─────────────────────────────────────────────────

    @staticmethod
    def content_hash(html: str) -> str:
        return hashlib.md5(html.encode("utf-8")).hexdigest()
