import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd  # type: ignore[import-untyped]
from atlassian import Confluence  # type: ignore[import-untyped]

from src.config import Config
from src.csv_manager import PapersTable, parse_tags
from src.md_to_confluence import (
    build_index_html,
    build_keywords_html,
    build_papers_table_html,
    build_weekly_page_html,
    format_weekly_title,
    md_to_confluence_storage,
)
from src.publish_state import PublishState

logger = logging.getLogger(__name__)


def _sanitize_label(label: str) -> str:
    """Make label safe for Confluence (e.g. replace '.' with '-')."""
    return label.replace(".", "-").strip()


class ConfluencePublisher:
    """Publishes papers table and weekly analyses to Confluence.

    Confluence page hierarchy:
        Papers (index — year links + reference links)
        ├── Analysis Prompt
        ├── Search Keywords
        ├── 2026 (year page — papers table)
        │   ├── Feb 16 - Feb 22 (EN weekly)
        │   ├── Feb 16 - Feb 22 (RU) (RU weekly)
        │   └── ...
        └── ...
        RU (index — year links)
        ├── 2026 (RU) (year page — papers table with RU links)
        └── ...
    """

    def __init__(self, config: Config, force: bool = False) -> None:
        self.config = config
        self.space = config.confluence_space_key
        self.confluence = self._connect(config)
        self._base_url = config.confluence_url.rstrip("/")
        self._force = force
        self.state = PublishState(config.publish_state_file)

        self._papers_page_id: Optional[str] = None
        self._ru_page_id: Optional[str] = None
        self._prompt_page_url: Optional[str] = None
        self._keywords_page_url: Optional[str] = None

    @staticmethod
    def _connect(config: Config) -> Confluence:
        url = config.confluence_url
        token = config.confluence_token
        email = config.confluence_email

        if not url or not token:
            raise ValueError(
                "CONFLUENCE_URL and CONFLUENCE_TOKEN must be set in .env"
            )

        if email:
            logger.info("Connecting to Confluence (Basic auth): %s", url)
            return Confluence(url=url, username=email, password=token, cloud=True)

        logger.info("Connecting to Confluence (Bearer token): %s", url)
        return Confluence(url=url, token=token)

    def _page_url(self, page_id: str) -> str:
        """Get the full web URL for a Confluence page via API."""
        page = self.confluence.get_page_by_id(page_id)
        webui = page.get("_links", {}).get("webui", f"/pages/{page_id}")
        return f"{self._base_url}{webui}"

    # ── structure ───────────────────────────────────────────────

    def ensure_structure(self) -> None:
        """Create top-level Papers and RU pages + reference pages."""
        parent_id = self.config.confluence_parent_page_id

        self._papers_page_id = self._find_or_create(
            self.config.confluence_papers_page_title,
            parent_id,
            body="<p>Papers index</p>",
        )
        logger.info("Papers page ID: %s", self._papers_page_id)

        self._ru_page_id = self._find_or_create(
            self.config.confluence_ru_page_title,
            self._papers_page_id,
            body="<p>RU index</p>",
        )
        logger.info("RU page ID: %s", self._ru_page_id)

        self._ensure_reference_pages()

    def _ensure_reference_pages(self) -> None:
        """Create Prompt and Keywords pages once (content is not updated)."""
        prompt_title = self.config.confluence_prompt_page_title
        prompt_page = self.confluence.get_page_by_title(self.space, prompt_title)
        if prompt_page:
            prompt_id = str(prompt_page["id"])
        else:
            prompt_md = Path("prompts/analyze_paper.md").read_text(encoding="utf-8")
            prompt_html = md_to_confluence_storage(prompt_md)
            prompt_id = self._find_or_create(
                prompt_title, self._papers_page_id, body=prompt_html
            )
            logger.info("Created Prompt page: %s", prompt_title)

        self._prompt_page_url = self._page_url(prompt_id)

        kw_title = self.config.confluence_keywords_page_title
        kw_page = self.confluence.get_page_by_title(self.space, kw_title)
        if kw_page:
            kw_id = str(kw_page["id"])
        else:
            kw_html = build_keywords_html(self.config.keywords)
            kw_id = self._find_or_create(
                kw_title, self._papers_page_id, body=kw_html
            )
            logger.info("Created Keywords page: %s", kw_title)

        self._keywords_page_url = self._page_url(kw_id)

    # ── main publish entry point ────────────────────────────────

    def publish(self, table: PapersTable) -> None:
        """Publish everything that needs publishing."""
        self.ensure_structure()

        years = sorted(table.df["date"].str[:4].unique(), reverse=True)
        year_stats: Dict[str, Tuple[int, int, str]] = {}

        for year in years:
            year_df = table.df[table.df["date"].str.startswith(year)]
            en_page_id, ru_page_id = self._publish_year(year, year_df, table)
            en_url = self._page_url(en_page_id)

            total = len(year_df)
            analyzed = int((year_df["processed"] == "1").sum())
            year_stats[year] = (total, analyzed, en_url)

        self._publish_index(year_stats)
        self.state.save()

    # ── year-level ──────────────────────────────────────────────

    def _publish_year(
        self,
        year: str,
        year_df: "pd.DataFrame",
        table: PapersTable,
    ) -> Tuple[str, str]:
        """Publish/update a year page and its weekly children.

        Returns (en_year_page_id, ru_year_page_id).
        """
        en_year_title = year
        ru_year_title = f"{year} (RU)"

        weeks = _group_by_week(year_df)
        canonical_weeks = [
            (ws, we, ids) for (ws, we), ids in weeks.items() if ws[:4] == year
        ]
        current_year = datetime.utcnow().strftime("%Y")
        is_current = (year == current_year)

        # Fast path: skip past, fully-locked years entirely (no API calls).
        # Year content is rebuilt locally and compared with stored hash;
        # if unchanged, nothing to send to Confluence.
        if not self._force and not is_current:
            year_state = self.state.get_year_state(year)
            cached_en = year_state.get("en_page_id")
            cached_ru = year_state.get("ru_page_id")
            cached_hash = year_state.get("hash")
            all_locked = bool(canonical_weeks) and all(
                self.state.is_week_locked(year, ws, we)
                for ws, we, _ in canonical_weeks
            )
            if all_locked and cached_en and cached_ru and cached_hash:
                fresh_year_df = table.df[table.df["date"].str.startswith(year)]
                table_html = build_papers_table_html(
                    fresh_year_df, week_urls={}
                )
                if PublishState.content_hash(table_html) == cached_hash:
                    logger.info(
                        "Year skipped (all weeks locked, table unchanged): %s",
                        year,
                    )
                    return cached_en, cached_ru

        en_year_id = self._find_or_create(
            en_year_title, self._papers_page_id, body="<p>Loading...</p>"
        )
        ru_year_id = self._find_or_create(
            ru_year_title, self._ru_page_id, body="<p>Loading...</p>"
        )

        for w_start, w_end, arxiv_ids in canonical_weeks:
            full_arxiv_ids = arxiv_ids
            if w_start[:4] != w_end[:4]:
                full_arxiv_ids = table.df[
                    (table.df["date"] >= w_start)
                    & (table.df["date"] <= w_end)
                ]["arxiv_id"].tolist()
            self._publish_week(
                year, w_start, w_end, full_arxiv_ids,
                en_year_id, ru_year_id, table,
            )

        fresh_year_df = table.df[table.df["date"].str.startswith(year)]

        week_urls: Dict[str, str] = {}
        current_year = datetime.utcnow().strftime("%Y")
        if year == current_year:
            today = datetime.utcnow().date()
            monday = today - timedelta(days=today.weekday())
            target_weeks = [
                (monday.strftime("%Y-%m-%d"),
                 (monday + timedelta(days=6)).strftime("%Y-%m-%d")),
                ((monday - timedelta(days=7)).strftime("%Y-%m-%d"),
                 (monday - timedelta(days=1)).strftime("%Y-%m-%d")),
            ]
            for w_start, w_end in target_weeks:
                key = f"{w_start}_{w_end}"
                week_state = self.state._data.get("weekly", {}).get(
                    f"{year}/{key}", {}
                )
                en_pid = week_state.get("en_page_id")
                if en_pid:
                    week_urls[key] = self._page_url(en_pid)

        table_html = build_papers_table_html(
            fresh_year_df, week_urls=week_urls
        )
        content_hash = PublishState.content_hash(table_html)
        old_hash = self.state.get_year_hash(year)

        if self._force or content_hash != old_hash:
            self._update_page(en_year_id, en_year_title, table_html)
            self._update_page(ru_year_id, ru_year_title, table_html)
            self.state.set_year(year, en_year_id, ru_year_id, content_hash)
            logger.info("Updated year table: %s", year)
        else:
            logger.info("Year table unchanged, skipped: %s", year)

        return en_year_id, ru_year_id

    # ── week-level ──────────────────────────────────────────────

    def _publish_week(
        self,
        year: str,
        w_start: str,
        w_end: str,
        arxiv_ids: List[str],
        en_year_page_id: str,
        ru_year_page_id: str,
        table: PapersTable,
    ) -> None:
        """Publish/update a single weekly EN+RU page pair."""
        if not self._force and self.state.is_week_locked(year, w_start, w_end):
            logger.debug("Week locked, skipped: %s %s-%s", year, w_start, w_end)
            return

        all_papers = table.df[table.df["arxiv_id"].isin(arxiv_ids)]
        processed = all_papers[all_papers["processed"] == "1"]

        if processed.empty:
            return

        week_title = format_weekly_title(w_start, w_end)
        en_title = week_title
        ru_title = f"{week_title} (RU)"

        en_html = build_weekly_page_html(
            processed, self.config.analysis_dir, w_start, w_end
        )
        en_page_id = self._find_or_create(
            en_title, en_year_page_id, body=en_html
        )
        self._update_page(en_page_id, en_title, en_html)
        en_page_url = self._page_url(en_page_id)
        logger.info("Published EN weekly: %s", en_title)

        ru_html = build_weekly_page_html(
            processed, self.config.analysis_ru_dir, w_start, w_end
        )
        ru_page_id = self._find_or_create(
            ru_title, ru_year_page_id, body=ru_html
        )
        self._update_page(ru_page_id, ru_title, ru_html)
        ru_page_url = self._page_url(ru_page_id)
        logger.info("Published RU weekly: %s", ru_title)

        labels = self._collect_paper_tags(
            processed["arxiv_id"].tolist(), self.config.analysis_dir
        )
        if labels:
            self._set_page_labels(en_page_id, labels)
            logger.info(
                "Set %d labels on EN weekly page: %s", len(labels), week_title
            )

        for arxiv_id in processed["arxiv_id"]:
            anchor = f"#paper-{arxiv_id.replace('.', '-')}"
            table.df.loc[
                table.df["arxiv_id"] == arxiv_id, "confluence_en_url"
            ] = f"{en_page_url}{anchor}"
            table.df.loc[
                table.df["arxiv_id"] == arxiv_id, "confluence_ru_url"
            ] = f"{ru_page_url}{anchor}"

        week_ended = datetime.strptime(w_end, "%Y-%m-%d")
        week_is_past = (datetime.utcnow() - week_ended).days > 7
        all_done = len(processed) == len(all_papers) and week_is_past
        self.state.set_week(
            year, w_start, w_end, en_page_id, ru_page_id, locked=all_done
        )
        if all_done:
            logger.info("All papers processed & week past — locked: %s", week_title)

        table.save()

    # ── index page ──────────────────────────────────────────────

    def _publish_index(
        self,
        year_stats: Dict[str, Tuple[int, int, str]],
    ) -> None:
        """Update the main Papers index page with year links."""
        html = build_index_html(
            year_stats,
            prompt_url=self._prompt_page_url,
            keywords_url=self._keywords_page_url,
        )
        content_hash = PublishState.content_hash(html)

        if self._force or content_hash != self.state.get_index_hash():
            self._update_page(
                self._papers_page_id,
                self.config.confluence_papers_page_title,
                html,
            )
            self.state.set_index_hash(content_hash)
            logger.info("Updated Papers index page")
        else:
            logger.info("Papers index unchanged, skipped")

    # ── low-level helpers ───────────────────────────────────────

    def _find_or_create(
        self, title: str, parent_id: str, body: str = ""
    ) -> str:
        """Return page ID, creating the page if it doesn't exist.

        Also verifies the existing page's parent matches the expected one —
        avoids overwriting a same-titled page under a different parent.
        """
        page = self.confluence.get_page_by_title(self.space, title)
        if page:
            page_id = str(page["id"])
            full = self.confluence.get_page_by_id(page_id, expand="ancestors")
            ancestors = full.get("ancestors", []) if full else []
            ancestor_ids = {str(a["id"]) for a in ancestors}
            if str(parent_id) in ancestor_ids:
                return page_id
            logger.warning(
                "Page '%s' (id=%s) exists under a different parent; "
                "will create a new one under %s",
                title, page_id, parent_id,
            )

        logger.info("Creating page: '%s'", title)
        result = self.confluence.create_page(
            space=self.space,
            title=title,
            body=body,
            parent_id=parent_id,
            representation="storage",
            editor="v2",
        )
        return str(result["id"])

    def _update_page(self, page_id: str, title: str, body: str) -> None:
        self.confluence.update_page(
            page_id=page_id,
            title=title,
            body=body,
            representation="storage",
        )

    def _collect_paper_tags(
        self, arxiv_ids: List[str], analysis_dir: str
    ) -> List[str]:
        """Collect unique tags from all papers' analysis files."""
        analysis_path = Path(analysis_dir)
        all_tags: set = set()
        for arxiv_id in arxiv_ids:
            md_file = analysis_path / f"{arxiv_id}.md"
            if md_file.exists():
                all_tags.update(parse_tags(md_file))
        return sorted(all_tags)

    def _set_page_labels(self, page_id: str, labels: List[str]) -> None:
        """Add Confluence labels to a page (existing labels are kept)."""
        for label in labels:
            safe = _sanitize_label(label)
            if not safe:
                continue
            try:
                self.confluence.set_page_label(page_id, safe)
            except Exception:
                logger.warning("Failed to set label '%s' on page %s", safe, page_id)


def _group_by_week(
    df: "pd.DataFrame",
) -> Dict[Tuple[str, str], List[str]]:
    """Group paper arxiv_ids by ISO week (Monday–Sunday).

    Returns {(week_monday, week_sunday): [arxiv_id, ...]}.
    """
    weeks: Dict[Tuple[str, str], List[str]] = {}

    for _, row in df.iterrows():
        d = datetime.strptime(row["date"], "%Y-%m-%d")
        monday = d - timedelta(days=d.weekday())
        sunday = monday + timedelta(days=6)
        key = (monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d"))
        weeks.setdefault(key, []).append(row["arxiv_id"])

    return dict(sorted(weeks.items()))
