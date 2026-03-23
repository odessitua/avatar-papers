import re
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import arxiv

logger = logging.getLogger(__name__)


def _build_query(
    keywords: List[str],
    search_field: str,
    categories: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Build an arXiv query string with optional category and date filters.

    Date range is passed directly to the API via submittedDate so
    the server pre-filters results instead of relying on client-side
    pagination through all newer papers.

    Example output:
      (abs:"Talking Face" OR abs:"Lip Sync") AND (cat:cs.CV OR cat:cs.MM)
      AND submittedDate:[20220101 TO 20220331]
    """
    kw_parts = [f'{search_field}:"{kw}"' for kw in keywords]
    query = " OR ".join(kw_parts)

    if categories:
        cat_parts = [f"cat:{cat}" for cat in categories]
        cat_clause = " OR ".join(cat_parts)
        query = f"({query}) AND ({cat_clause})"

    if date_from or date_to:
        d_from = date_from.replace("-", "") if date_from else "000001"
        d_to = date_to.replace("-", "") if date_to else "999912"
        query = f"({query}) AND submittedDate:[{d_from} TO {d_to}]"

    return query


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract bare arxiv_id from entry URL, stripping version suffix.

    Example: 'http://arxiv.org/abs/2602.12345v1' -> '2602.12345'
    """
    raw = entry_id.rsplit("/abs/", maxsplit=1)[-1]
    return re.sub(r"v\d+$", "", raw)


def _format_authors(authors: list) -> str:
    names = [a.name for a in authors]
    if len(names) <= 2:
        return ", ".join(names)
    return f"{names[0]} et al."


def search_papers(
    keywords: Dict[str, List[str]],
    max_results: int = 200,
    sort_by: str = "submitted",
    search_field: str = "abs",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    categories: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """Search arXiv for papers matching keywords, return list of paper dicts."""

    sort_criterion = (
        arxiv.SortCriterion.SubmittedDate
        if sort_by == "submitted"
        else arxiv.SortCriterion.LastUpdatedDate
    )

    dt_from: Optional[datetime] = None
    dt_to: Optional[datetime] = None
    if date_from:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    if date_to:
        dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )

    client = arxiv.Client(page_size=100, delay_seconds=5.0, num_retries=5)
    all_papers: List[Dict[str, str]] = []
    seen_ids: set = set()

    for topic_idx, (topic, kws) in enumerate(keywords.items()):
        if topic_idx > 0:
            time.sleep(5)

        query = _build_query(kws, search_field, categories, date_from, date_to)
        logger.info("Topic '%s': query = %s", topic, query[:200])

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_criterion,
            sort_order=arxiv.SortOrder.Descending,
        )

        topic_count = 0
        try:
            for result in client.results(search):
                published = result.published.replace(tzinfo=timezone.utc)

                if dt_to and published > dt_to:
                    continue
                if dt_from and published < dt_from:
                    break

                arxiv_id = _extract_arxiv_id(result.entry_id)
                if arxiv_id in seen_ids:
                    continue
                seen_ids.add(arxiv_id)

                paper = {
                    "arxiv_id": arxiv_id,
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "title": result.title.replace("\n", " ").strip(),
                    "date": published.strftime("%Y-%m-%d"),
                    "authors": _format_authors(result.authors),
                    "topic": topic,
                    "code_url": "",
                    "downloaded": "0",
                    "processed": "0",
                }
                all_papers.append(paper)
                topic_count += 1
        except arxiv.HTTPError as exc:
            logger.warning(
                "Topic '%s': arXiv HTTP %s — collected %d papers before error",
                topic, exc, topic_count,
            )

        logger.info(
            "Topic '%s': found %d papers (after date filter)", topic, topic_count
        )

    logger.info("Total unique papers found: %d", len(all_papers))
    return all_papers
