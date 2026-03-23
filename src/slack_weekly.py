"""
Publish weekly paper reports to Slack.

Supports two methods:
- Incoming Webhook: set SLACK_WEBHOOK_URL in .env (needs channel admin to add it).
- Slack App Bot: set SLACK_BOT_TOKEN and SLACK_CHANNEL in .env (create app at
  api.slack.com/apps, add Bot with chat:write, install, invite bot to channel).
"""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

from src.csv_manager import parse_tags
from src.md_to_confluence import TOPIC_EMOJI

logger = logging.getLogger(__name__)

# Slack message limit (conservative for block text).
MAX_TEXT_LEN = 2800


def _week_bounds(which: str) -> Tuple[str, str]:
    """Return (monday, sunday) for 'current' or 'last' week (ISO Mon–Sun)."""
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())
    if which == "current":
        start = monday
        end = monday + timedelta(days=6)
    else:
        start = monday - timedelta(days=7)
        end = monday - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _topic_emoji(topic: str) -> str:
    """Return topic emoji or empty string."""
    return TOPIC_EMOJI.get(topic, "")


def _extract_tags(md_path: Path, limit: int = 6) -> List[str]:
    """Extract first N tags from analysis markdown, formatted for Slack."""
    tags = parse_tags(md_path)
    return [t.replace(" ", "-").lower() for t in tags[:limit]]


def _extract_summary(md_path: Path) -> str:
    """Extract the Summary section text from analysis markdown (single paragraph)."""
    if not md_path.exists():
        return ""
    text = md_path.read_text(encoding="utf-8")
    match = re.search(
        r"##\s*Summary\s*\n+(.*?)(?=\n##\s|\n---|\n\n\n|\Z)",
        text,
        re.DOTALL,
    )
    if not match:
        return ""
    summary = match.group(1).strip()
    summary = re.sub(r"\n+", " ", summary)
    return summary[:500] + ("..." if len(summary) > 500 else "")


def _extract_score(md_path: Path) -> Optional[str]:
    """Extract Recommendation score (e.g. 8/10) from analysis markdown."""
    if not md_path.exists():
        return None
    text = md_path.read_text(encoding="utf-8")
    match = re.search(r"##\s*Recommendation:\s*(\d+)/10", text)
    return match.group(1) if match else None


def _numeric_score(row: pd.Series, analysis_dir: Path) -> Optional[int]:
    """Resolve paper score from CSV or analysis file. Returns None if missing/invalid."""
    raw = row.get("score")
    if not raw and analysis_dir:
        raw = _extract_score(analysis_dir / f"{row['arxiv_id']}.md")
    if raw is None or raw == "":
        return None
    try:
        return int(float(str(raw).strip()))
    except (ValueError, TypeError):
        return None


def build_weekly_report(
    week_df: pd.DataFrame,
    analysis_dir: Path,
    w_start: str,
    w_end: str,
) -> str:
    """Build a plain-text weekly report for Slack (title, link, score, summary per paper)."""
    lines: List[str] = []
    lines.append(f"*Papers: {w_start} — {w_end}* ({len(week_df)} papers)\n")

    for _, row in week_df.iterrows():
        arxiv_id = row["arxiv_id"]
        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        topic = (row.get("topic") or "").strip()
        score = row.get("score") or _extract_score(analysis_dir / f"{arxiv_id}.md")
        summary = _extract_summary(analysis_dir / f"{arxiv_id}.md")
        md_path = analysis_dir / f"{arxiv_id}.md"
        tags = _extract_tags(md_path)

        emoji = _topic_emoji(topic)
        prefix = f"{emoji} " if emoji else ""
        link = f"<{url}|{title}>" if url else title
        score_str = f" [{score}/10]" if score else ""
        lines.append(f"• {prefix}{link}{score_str}")
        if tags:
            lines.append(f"  `{'` `'.join(tags)}`")
        if summary:
            lines.append(f"  {summary}")
        lines.append("")

    body = "\n".join(lines).strip()
    if len(body) > MAX_TEXT_LEN:
        body = body[: MAX_TEXT_LEN - 3] + "..."
    return body


def build_weekly_report_blocks(
    week_df: pd.DataFrame,
    analysis_dir: Path,
    w_start: str,
    w_end: str,
    min_score: int = 0,
    confluence_week_url: Optional[str] = None,
) -> List[Dict]:
    """Build Slack Block Kit blocks for the weekly report.

    Header is a link to Confluence weekly page if confluence_week_url is set.
    Paper titles are links to arXiv (article URLs).
    """
    subtitle = f"_{len(week_df)} papers_"
    if min_score > 0:
        subtitle += f" (score ≥ {min_score})"
    subtitle += "\n"
    header_text = f"Papers: {w_start} — {w_end}"
    if confluence_week_url and confluence_week_url.strip():
        header_mrkdwn = f"*<{confluence_week_url.strip()}|{header_text}>*"
        header_block: Dict = {"type": "section", "text": {"type": "mrkdwn", "text": header_mrkdwn}}
    else:
        header_block = {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True},
        }
    blocks: List[Dict] = [
        header_block,
        {"type": "section", "text": {"type": "mrkdwn", "text": subtitle}},
        {"type": "divider"},
    ]

    for _, row in week_df.iterrows():
        arxiv_id = row["arxiv_id"]
        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        topic = (row.get("topic") or "").strip()
        score = row.get("score") or _extract_score(analysis_dir / f"{arxiv_id}.md")
        summary = _extract_summary(analysis_dir / f"{arxiv_id}.md")
        md_path = analysis_dir / f"{arxiv_id}.md"
        tags = _extract_tags(md_path)

        emoji = _topic_emoji(topic)
        prefix = f"{emoji} " if emoji else ""
        link = f"<{url}|{title}>" if url else title
        score_str = f" [{score}/10]" if score else ""
        parts = [f"*{prefix}{link}*{score_str}"]
        if tags:
            parts.append("`" + "` `".join(tags) + "`")
        if summary:
            parts.append(summary)
        text = "\n".join(parts)
        if len(text) > 2900:
            text = text[:2897] + "..."
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})

    return blocks


def send_weekly_to_slack(
    webhook_url: str,
    week_df: pd.DataFrame,
    analysis_dir: Path,
    w_start: str,
    w_end: str,
    use_blocks: bool = True,
    min_score: int = 0,
    confluence_week_url: Optional[str] = None,
) -> bool:
    """Build the weekly report and POST it to the Slack webhook. Returns True on success."""
    if not webhook_url.strip():
        logger.error("SLACK_WEBHOOK_URL is not set")
        return False

    if week_df.empty:
        logger.warning("No papers in week %s — %s, nothing to send", w_start, w_end)
        return False

    analysis_path = Path(analysis_dir)
    if use_blocks:
        blocks = build_weekly_report_blocks(
            week_df,
            analysis_path,
            w_start,
            w_end,
            min_score=min_score,
            confluence_week_url=confluence_week_url,
        )
        payload: Dict = {"blocks": blocks}
        fallback = build_weekly_report(week_df, analysis_path, w_start, w_end)
        payload["text"] = fallback[:4000]
    else:
        body = build_weekly_report(week_df, analysis_path, w_start, w_end)
        payload = {"text": body}

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        logger.info("Slack weekly report sent: %s — %s (%d papers)", w_start, w_end, len(week_df))
        return True
    except requests.RequestException as e:
        logger.exception("Failed to send Slack report: %s", e)
        return False


def send_weekly_via_slack_api(
    bot_token: str,
    channel: str,
    week_df: pd.DataFrame,
    analysis_dir: Path,
    w_start: str,
    w_end: str,
    min_score: int = 0,
    confluence_week_url: Optional[str] = None,
) -> bool:
    """Post weekly report via Slack API (chat.postMessage). Use when you have a Bot token."""
    if not bot_token.strip() or not channel.strip():
        logger.error("SLACK_BOT_TOKEN and SLACK_CHANNEL must be set")
        return False

    if week_df.empty:
        logger.warning("No papers in week %s — %s, nothing to send", w_start, w_end)
        return False

    blocks = build_weekly_report_blocks(
        week_df,
        analysis_dir,
        w_start,
        w_end,
        min_score=min_score,
        confluence_week_url=confluence_week_url,
    )
    fallback = build_weekly_report(week_df, analysis_dir, w_start, w_end)

    payload: Dict = {
        "channel": channel.strip(),
        "text": fallback[:4000],
        "blocks": blocks,
    }

    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
            timeout=30,
            headers={
                "Authorization": f"Bearer {bot_token.strip()}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            logger.error("Slack API error: %s", data.get("error", "unknown"))
            return False
        logger.info("Slack weekly report sent: %s — %s (%d papers)", w_start, w_end, len(week_df))
        return True
    except requests.RequestException as e:
        logger.exception("Failed to send Slack report: %s", e)
        return False


def run_slack_weekly(
    table: pd.DataFrame,
    analysis_dir: str,
    webhook_url: str = "",
    bot_token: str = "",
    channel: str = "",
    week: str = "last",
    min_score: int = 7,
    confluence_week_url: Optional[str] = None,
) -> bool:
    """
    Build and send the weekly report to Slack.

    Uses SLACK_WEBHOOK_URL if set; otherwise SLACK_BOT_TOKEN + SLACK_CHANNEL.
    week: 'last' (previous Mon–Sun) or 'current' (this week).
    min_score: only include papers with score >= this (default 7).
    """
    w_start, w_end = _week_bounds(week)
    week_df = table[
        (table["date"] >= w_start) & (table["date"] <= w_end)
    ].sort_values("date", ascending=False)

    analysis_path = Path(analysis_dir)
    if min_score > 0:
        scores = week_df.apply(
            lambda r: _numeric_score(r, analysis_path), axis=1
        )
        week_df = week_df[scores.notna() & (scores >= min_score)].copy()
        if week_df.empty:
            logger.warning(
                "No papers with score >= %d in week %s — %s",
                min_score, w_start, w_end,
            )
            return False

    if webhook_url.strip():
        return send_weekly_to_slack(
            webhook_url,
            week_df,
            analysis_path,
            w_start,
            w_end,
            use_blocks=True,
            min_score=min_score,
            confluence_week_url=confluence_week_url,
        )
    if bot_token.strip() and channel.strip():
        return send_weekly_via_slack_api(
            bot_token,
            channel,
            week_df,
            analysis_path,
            w_start,
            w_end,
            min_score=min_score,
            confluence_week_url=confluence_week_url,
        )
    logger.error(
        "Set either SLACK_WEBHOOK_URL or (SLACK_BOT_TOKEN and SLACK_CHANNEL) in .env"
    )
    return False
