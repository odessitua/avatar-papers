import csv
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

CSV_COLUMNS: List[str] = [
    "arxiv_id",
    "url",
    "title",
    "date",
    "authors",
    "topic",
    "code_url",
    "downloaded",
    "processed",
    "score",
    "confluence_en_url",
    "confluence_ru_url",
]

_SCORE_RE = re.compile(r"^##\s+Recommendation:\s*(\d{1,2})\s*/\s*10", re.MULTILINE)
_CODE_RE = re.compile(
    r"^\-\s*\*\*Code:\*\*\s*(https?://\S+)",
    re.MULTILINE,
)
_TAGS_RE = re.compile(
    r"^##\s+Tags\s*\n\s*\n(.+?)(?:\n\s*\n|$)",
    re.MULTILINE,
)
_LABEL_CLEAN_RE = re.compile(r"[^a-z0-9\-_.]")


class PapersTable:
    """Manages the CSV table of papers with deduplication and updates."""

    def __init__(self, csv_path: str) -> None:
        self.csv_path = Path(csv_path)
        self._load()

    def _load(self) -> None:
        if self.csv_path.exists() and self.csv_path.stat().st_size > 0:
            self.df = pd.read_csv(self.csv_path, dtype=str)
            for col in CSV_COLUMNS:
                if col not in self.df.columns:
                    self.df[col] = ""
            extra = [c for c in self.df.columns if c not in CSV_COLUMNS]
            if extra:
                logger.warning("Dropping unexpected CSV columns: %s", extra)
                self.df = self.df.drop(columns=extra)
        else:
            self.df = pd.DataFrame(columns=CSV_COLUMNS)
        self.df = self.df.fillna("")

    def save(self) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.df = self.df.sort_values("date", ascending=False).reset_index(drop=True)
        self.df[CSV_COLUMNS].to_csv(
            self.csv_path, index=False, quoting=csv.QUOTE_ALL
        )
        logger.info("Saved %d papers to %s", len(self.df), self.csv_path)

    def add_papers(self, papers: List[Dict[str, str]]) -> int:
        """Add new papers, update existing ones. Returns count of newly added."""
        existing_ids = set(self.df["arxiv_id"].tolist())
        new_rows: List[Dict[str, str]] = []

        for paper in papers:
            aid = paper["arxiv_id"]
            if aid in existing_ids:
                mask = self.df["arxiv_id"] == aid
                for field in ("title", "date", "authors"):
                    if paper.get(field):
                        self.df.loc[mask, field] = paper[field]
            else:
                new_rows.append(paper)
                existing_ids.add(aid)

        if new_rows:
            new_df = pd.DataFrame(new_rows, columns=CSV_COLUMNS).fillna("")
            self.df = pd.concat([self.df, new_df], ignore_index=True)

        logger.info("Added %d new papers, updated existing", len(new_rows))
        return len(new_rows)

    def get_not_downloaded(self) -> pd.DataFrame:
        return self.df[self.df["downloaded"] != "1"]

    def mark_downloaded(self, arxiv_id: str) -> None:
        self.df.loc[self.df["arxiv_id"] == arxiv_id, "downloaded"] = "1"

    def get_code_url(self, arxiv_id: str) -> str:
        rows = self.df.loc[self.df["arxiv_id"] == arxiv_id, "code_url"]
        if rows.empty:
            return ""
        return rows.iloc[0]

    def update_code_url(self, arxiv_id: str, code_url: str) -> None:
        self.df.loc[self.df["arxiv_id"] == arxiv_id, "code_url"] = code_url

    def get_without_code_url(self) -> pd.DataFrame:
        return self.df[self.df["code_url"].isin(["", None])]

    def sync_processed(self, analysis_dir: str) -> int:
        """Scan analysis directory, mark papers as processed, extract scores."""
        analysis_path = Path(analysis_dir)
        if not analysis_path.exists():
            return 0

        updated = 0
        for _, row in self.df.iterrows():
            aid = row["arxiv_id"]
            md_file = analysis_path / f"{aid}.md"
            if not md_file.exists():
                continue

            mask = self.df["arxiv_id"] == aid

            if row["processed"] != "1":
                self.df.loc[mask, "processed"] = "1"
                updated += 1

            if not row.get("score"):
                score = _parse_score(md_file)
                if score:
                    self.df.loc[mask, "score"] = score

            if not row.get("code_url"):
                code_url = _parse_code_url(md_file)
                if code_url:
                    self.df.loc[mask, "code_url"] = code_url

        if updated:
            logger.info("Marked %d papers as processed", updated)
        return updated

    def get_papers_for_period(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> pd.DataFrame:
        """Get processed papers within a date range."""
        mask = self.df["processed"] == "1"
        if date_from:
            mask = mask & (self.df["date"] >= date_from)
        if date_to:
            mask = mask & (self.df["date"] <= date_to)
        return self.df[mask]


def _parse_score(md_file: Path) -> str:
    """Extract the recommendation score (N/10) from an analysis .md file."""
    try:
        text = md_file.read_text(encoding="utf-8")
        match = _SCORE_RE.search(text)
        if match:
            return match.group(1)
    except OSError:
        pass
    return ""


def _parse_code_url(md_file: Path) -> str:
    """Extract the code URL from the '- **Code:** ...' line in analysis .md."""
    try:
        text = md_file.read_text(encoding="utf-8")
        match = _CODE_RE.search(text)
        if match:
            return match.group(1).rstrip(")")
    except OSError:
        pass
    return ""


def parse_tags(md_file: Path) -> List[str]:
    """Extract tags from '## Tags' section and sanitize for Confluence labels.

    Confluence labels must be lowercase, no spaces, alphanumeric/hyphens/underscores/dots.
    """
    try:
        text = md_file.read_text(encoding="utf-8")
        match = _TAGS_RE.search(text)
        if not match:
            return []
        raw_tags = [t.strip() for t in match.group(1).split(",")]
        labels: List[str] = []
        for tag in raw_tags:
            label = tag.lower().replace(" ", "-")
            label = _LABEL_CLEAN_RE.sub("", label)
            if label:
                labels.append(label)
        return labels
    except OSError:
        return []
