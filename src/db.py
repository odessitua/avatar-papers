"""SQLite mirror of papers.csv with normalised tags for ad-hoc SQL queries.

The database is rebuilt from scratch on every ``sync`` run, so the CSV
remains the single source of truth.
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from src.csv_manager import parse_tags

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id          TEXT PRIMARY KEY,
    url               TEXT,
    title             TEXT,
    date              TEXT,
    authors           TEXT,
    topic             TEXT,
    code_url          TEXT,
    score             INTEGER,
    confluence_en_url TEXT,
    confluence_ru_url TEXT
);
CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_tags (
    paper_id TEXT    NOT NULL REFERENCES papers(arxiv_id),
    tag_id   INTEGER NOT NULL REFERENCES tags(id),
    PRIMARY KEY (paper_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_paper_tags_tag ON paper_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_papers_date    ON papers(date);
CREATE INDEX IF NOT EXISTS idx_papers_score   ON papers(score);
"""


class PapersDB:
    """Thin wrapper around SQLite for the papers database."""

    def __init__(self, db_path: str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def close(self) -> None:
        self._conn.close()

    def rebuild(
        self, df: pd.DataFrame, analysis_dir: str
    ) -> int:
        """Drop and recreate all tables from the CSV DataFrame + analysis tags.

        Returns the number of papers that had tags extracted.
        """
        cur = self._conn.cursor()
        cur.executescript(
            "DROP TABLE IF EXISTS paper_tags;"
            "DROP TABLE IF EXISTS tags;"
            "DROP TABLE IF EXISTS papers;"
        )
        cur.executescript(_SCHEMA)

        analysis_path = Path(analysis_dir)
        tagged_count = 0

        for _, row in df.iterrows():
            score_raw = row.get("score", "")
            try:
                score_int: Optional[int] = int(float(str(score_raw))) if score_raw else None
            except (ValueError, TypeError):
                score_int = None

            cur.execute(
                "INSERT OR REPLACE INTO papers "
                "(arxiv_id, url, title, date, authors, topic, code_url, score, "
                " confluence_en_url, confluence_ru_url) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    row.get("arxiv_id", ""),
                    row.get("url", ""),
                    row.get("title", ""),
                    row.get("date", ""),
                    row.get("authors", ""),
                    row.get("topic", ""),
                    row.get("code_url", ""),
                    score_int,
                    row.get("confluence_en_url", ""),
                    row.get("confluence_ru_url", ""),
                ),
            )

            md_file = analysis_path / f"{row['arxiv_id']}.md"
            tags = parse_tags(md_file)
            if tags:
                tagged_count += 1
                for tag_name in tags:
                    cur.execute(
                        "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                        (tag_name,),
                    )
                    tag_id = cur.execute(
                        "SELECT id FROM tags WHERE name=?", (tag_name,)
                    ).fetchone()[0]
                    cur.execute(
                        "INSERT OR IGNORE INTO paper_tags (paper_id, tag_id) VALUES (?,?)",
                        (row["arxiv_id"], tag_id),
                    )

        self._conn.commit()
        logger.info(
            "SQLite DB rebuilt: %d papers, %d with tags", len(df), tagged_count
        )
        return tagged_count
