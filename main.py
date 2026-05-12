import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union
from dotenv import load_dotenv  # type: ignore[import-untyped]

from src.config import Config
from src.arxiv_search import search_papers
from src.csv_manager import PapersTable
from src.downloader import download_pdf
from src.figure_parser import parse_figures, save_figures_meta, load_figures_meta
from src.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def cmd_search(config: Config, table: PapersTable, topic: str = None) -> None:
    """Search arXiv and update CSV table with new papers."""
    keywords = config.keywords
    if topic:
        if topic not in keywords:
            logger.error("Unknown topic '%s'. Available: %s", topic, list(keywords.keys()))
            return
        keywords = {topic: keywords[topic]}
        logger.info("Searching only topic: %s", topic)
    papers = search_papers(
        keywords=keywords,
        max_results=config.arxiv_max_results,
        sort_by=config.arxiv_sort_by,
        search_field=config.arxiv_search_field,
        date_from=config.arxiv_date_from,
        date_to=config.arxiv_date_to,
        categories=config.arxiv_categories,
    )
    new_count = table.add_papers(papers)
    table.save()
    logger.info("Search complete: %d total found, %d new added", len(papers), new_count)


def cmd_download(config: Config, table: PapersTable) -> None:
    """Download PDFs for papers not yet downloaded."""
    not_downloaded = table.get_not_downloaded()
    total = len(not_downloaded)
    if total == 0:
        logger.info("All papers already downloaded")
        return

    logger.info("Downloading %d PDFs...", total)
    success_count = 0
    for idx, (_, row) in enumerate(not_downloaded.iterrows(), 1):
        arxiv_id = row["arxiv_id"]
        ok = download_pdf(
            arxiv_id,
            config.originals_dir,
            delay=config.download_delay,
            timeout=config.download_timeout,
        )
        if ok:
            table.mark_downloaded(arxiv_id)
            success_count += 1
        if idx % 10 == 0:
            logger.info("Download progress: %d/%d", idx, total)
            table.save()

    table.save()
    logger.info("Download complete: %d/%d succeeded", success_count, total)

    _parse_all_figures(config, table)


def _parse_all_figures(
    config: Config, table: PapersTable, force: bool = False
) -> None:
    """Parse figures from arXiv HTML. If force=True, overwrite existing JSON."""
    figures_dir = config.figures_dir
    downloaded = table.df[table.df["downloaded"] == "1"]
    to_parse = []
    for _, row in downloaded.iterrows():
        if row.get("processed") == "1":
            continue
        if force or load_figures_meta(row["arxiv_id"], figures_dir) is None:
            to_parse.append(row["arxiv_id"])

    if not to_parse:
        logger.info("All figures already parsed")
        return

    logger.info("Parsing figures for %d papers...", len(to_parse))
    parsed = 0
    for idx, arxiv_id in enumerate(to_parse, 1):
        figures = parse_figures(arxiv_id)
        if figures:
            save_figures_meta(arxiv_id, figures, figures_dir)
            parsed += 1
        if idx % 20 == 0:
            logger.info("Figures progress: %d/%d", idx, len(to_parse))

    logger.info("Figures parsed: %d/%d had HTML versions", parsed, len(to_parse))


def cmd_reparse_figures(config: Config, table: PapersTable) -> None:
    """Re-parse figures from arXiv HTML for all downloaded papers, overwriting existing JSON."""
    _parse_all_figures(config, table, force=True)


def cmd_collect(config: Config, table: PapersTable) -> None:
    """Full pipeline: search + download."""
    cmd_search(config, table)
    cmd_download(config, table)


def cmd_sync(config: Config, table: PapersTable) -> None:
    """Sync 'processed' flag by scanning analysis directory, then rebuild DB."""
    updated = table.sync_processed(config.analysis_dir)
    table.save()
    logger.info("Sync complete: %d papers marked as processed", updated)

    _rebuild_db(config, table)


def _rebuild_db(config: Config, table: PapersTable) -> None:
    """Rebuild SQLite database from current CSV + analysis files."""
    from src.db import PapersDB

    db = PapersDB(config.db_file)
    try:
        tagged = db.rebuild(table.df, config.analysis_dir)
        logger.info("SQLite DB rebuilt: %s (%d tagged papers)", config.db_file, tagged)
    finally:
        db.close()



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avatar Papers — arXiv paper collector and publisher"
    )
    parser.add_argument(
        "command",
        choices=[
            "search", "download", "collect", "sync", "publish", "update",
            "reparse-figures", "slack-weekly", "analyze",
        ],
        help="Command to run",
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config file"
    )
    parser.add_argument(
        "--date-from", help="Override date_from filter (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--date-to", help="Override date_to filter (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-publish all pages (ignore locks and hashes)",
    )
    parser.add_argument(
        "--min-score", type=int, default=7,
        help="Minimum score for slack-weekly report (default: 7)",
    )
    parser.add_argument(
        "--week", default="last",
        help=(
            "Which week to report (used with slack-weekly): "
            "'current', 'last', or integer N for N weeks ago "
            "(0=current, 1=last, 2=two weeks ago, ...). Default: last."
        ),
    )
    parser.add_argument(
        "--topic", default=None,
        help="Search only this topic (used with search command)",
    )
    parser.add_argument(
        "--arxiv-id", action="append", default=None,
        help="Restrict 'analyze' to specific arxiv_id(s); repeatable",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of papers to analyze in one run (default: no limit)",
    )
    parser.add_argument(
        "--reanalyze", action="store_true",
        help="Re-analyze papers even if their .md already exists",
    )
    parser.add_argument(
        "--no-translate", action="store_true",
        help="Skip RU translation step in 'analyze'",
    )
    parser.add_argument(
        "--model", default=None,
        help="Override LLM model slug for 'analyze' (e.g. anthropic/claude-sonnet-4.6)",
    )
    args = parser.parse_args()

    load_dotenv()
    setup_logging()

    config = Config(args.config)
    if args.date_from:
        config.set_date_from(args.date_from)
    if args.date_to:
        config.set_date_to(args.date_to)

    table = PapersTable(config.csv_file)

    if args.command == "search":
        cmd_search(config, table, topic=args.topic)
    elif args.command == "download":
        cmd_download(config, table)
    elif args.command == "collect":
        cmd_collect(config, table)
    elif args.command == "sync":
        cmd_sync(config, table)
    elif args.command == "publish":
        cmd_publish(config, table, force=args.force)
    elif args.command == "update":
        cmd_update(config, table)
    elif args.command == "reparse-figures":
        cmd_reparse_figures(config, table)
    elif args.command == "slack-weekly":
        cmd_slack_weekly(config, table, week=args.week, min_score=args.min_score)
    elif args.command == "analyze":
        cmd_analyze(
            config, table,
            arxiv_ids=args.arxiv_id,
            limit=args.limit,
            reanalyze=args.reanalyze,
            translate=not args.no_translate,
            model=args.model,
        )


def cmd_update(config: Config, table: PapersTable) -> None:
    """Auto-detect date range, search new papers, and download PDFs.

    Looks at the most recent paper date in CSV and searches from there
    (minus 3-day overlap to catch late arXiv submissions) to today.
    If CSV is empty, searches the last 14 days.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if not table.df.empty:
        latest = table.df["date"].max()
        dt_latest = datetime.strptime(latest, "%Y-%m-%d")
        date_from = (dt_latest - timedelta(days=3)).strftime("%Y-%m-%d")
    else:
        date_from = (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d")

    logger.info("Update: searching %s — %s", date_from, today)
    config.set_date_from(date_from)
    config.set_date_to(today)

    cmd_search(config, table)
    cmd_download(config, table)
    if config.openrouter_api_key.strip():
        cmd_analyze(config, table)
    else:
        logger.info("OPENROUTER_API_KEY not set — skipping analyze step")
    cmd_sync(config, table)

    from src.confluence_publisher import ConfluencePublisher
    publisher = ConfluencePublisher(config)
    publisher.publish(table)
    logger.info("Update complete")


def cmd_publish(config: Config, table: PapersTable, force: bool = False) -> None:
    """Publish papers table and weekly analyses to Confluence."""
    from src.confluence_publisher import ConfluencePublisher

    publisher = ConfluencePublisher(config, force=force)
    publisher.publish(table)
    logger.info("Publish complete")


def _confluence_week_url(config: Config, w_start: str, w_end: str) -> str:
    """Build Confluence URL for the weekly page if it exists in publish state."""
    base = (config.confluence_url or "").strip().rstrip("/")
    space = (config.confluence_space_key or "").strip()
    if not base or not space:
        return ""
    try:
        from src.publish_state import PublishState
        state = PublishState(config.publish_state_file)
        year = w_start[:4]
        key = f"{year}/{w_start}_{w_end}"
        en_id = state._data.get("weekly", {}).get(key, {}).get("en_page_id")
        if en_id:
            return f"{base}/spaces/{space}/pages/{en_id}"
    except Exception:
        pass
    return ""


def cmd_slack_weekly(
    config: Config,
    table: PapersTable,
    week: Union[str, int] = "last",
    min_score: int = 7,
) -> None:
    """Send weekly papers report (new papers + analysis summaries) to Slack."""
    from src.slack_weekly import _week_bounds, run_slack_weekly

    has_webhook = bool(config.slack_webhook_url.strip())
    has_bot = bool(config.slack_bot_token.strip()) and bool(config.slack_channel.strip())
    if not has_webhook and not has_bot:
        logger.error(
            "Set either SLACK_WEBHOOK_URL (Incoming Webhook) or "
            "SLACK_BOT_TOKEN + SLACK_CHANNEL (Slack App Bot) in .env. "
            "See USAGE.md for setup."
        )
        return
    w_start, w_end = _week_bounds(week)
    confluence_week_url = _confluence_week_url(config, w_start, w_end)
    ok = run_slack_weekly(
        table.df,
        config.analysis_dir,
        webhook_url=config.slack_webhook_url,
        bot_token=config.slack_bot_token,
        channel=config.slack_channel,
        week=week,
        min_score=min_score,
        confluence_week_url=confluence_week_url or None,
    )
    if not ok:
        logger.error("Slack weekly report failed")
    else:
        logger.info("Slack weekly report sent successfully")


def cmd_analyze(
    config: Config,
    table: PapersTable,
    arxiv_ids: list = None,
    limit: int = None,
    reanalyze: bool = False,
    translate: bool = True,
    model: str = None,
) -> None:
    """Analyze papers via OpenRouter LLM and save EN+RU markdown."""
    from src.llm_analyzer import LLMClient, analyze_paper

    api_key = config.openrouter_api_key
    if not api_key.strip():
        logger.error(
            "OPENROUTER_API_KEY is not set in .env — get one at https://openrouter.ai"
        )
        return

    df = table.df
    if arxiv_ids:
        ids_set = {str(x).strip() for x in arxiv_ids}
        candidates = df[df["arxiv_id"].isin(ids_set)]
    else:
        candidates = df[(df["downloaded"] == "1") & (df["processed"] != "1")]

    originals_dir = Path(config.originals_dir)
    figures_dir = Path(config.figures_dir)
    analysis_dir = Path(config.analysis_dir)
    analysis_ru_dir = Path(config.analysis_ru_dir)

    selected = []
    for _, row in candidates.sort_values("date", ascending=False).iterrows():
        aid = row["arxiv_id"]
        pdf_exists = (originals_dir / f"{aid}.pdf").exists()
        if not pdf_exists:
            logger.warning("Skip %s: PDF missing", aid)
            continue
        en_exists = (analysis_dir / f"{aid}.md").exists()
        if en_exists and not reanalyze:
            logger.debug("Skip %s: analysis already exists", aid)
            continue
        selected.append(row)
        if limit and len(selected) >= limit:
            break

    if not selected:
        logger.info("Nothing to analyze")
        return

    logger.info(
        "Analyze: %d paper(s) selected (model=%s, translate=%s)",
        len(selected), model or config.llm_model, translate,
    )

    client = LLMClient(
        api_key=api_key,
        base_url=config.openrouter_base_url,
        model=model or config.llm_model,
        max_tokens=config.llm_max_tokens,
        temperature=config.llm_temperature,
    )

    total_in = total_out = 0
    failed: list = []
    for row in selected:
        aid = row["arxiv_id"]
        try:
            stats = analyze_paper(
                arxiv_id=aid,
                paper_meta={
                    "title": row.get("title", ""),
                    "url": row.get("url", ""),
                    "date": row.get("date", ""),
                    "authors": row.get("authors", ""),
                    "code_url": row.get("code_url", ""),
                },
                originals_dir=originals_dir,
                figures_dir=figures_dir,
                analysis_dir=analysis_dir,
                analysis_ru_dir=analysis_ru_dir,
                client=client,
                translate_model=config.llm_translate_model,
                pdf_max_chars=config.pdf_max_chars,
                skip_translation=not translate,
            )
            total_in += stats["en_usage"]["prompt_tokens"] + stats["ru_usage"]["prompt_tokens"]
            total_out += stats["en_usage"]["completion_tokens"] + stats["ru_usage"]["completion_tokens"]
        except Exception as e:
            logger.exception("Failed to analyze %s: %s", aid, e)
            failed.append(aid)

    table.sync_processed(config.analysis_dir)
    table.save()

    logger.info(
        "Analyze done: %d ok, %d failed | tokens in=%d out=%d",
        len(selected) - len(failed), len(failed), total_in, total_out,
    )
    if failed:
        logger.warning("Failed: %s", ", ".join(failed))


if __name__ == "__main__":
    main()
