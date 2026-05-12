import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import markdown
import pandas as pd  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)

# Emoji per topic (config keyword key). Used in papers table.
TOPIC_EMOJI = {
    "talking_head": "🗣️",
    "lip_sync": "👄",
    "portrait_animation": "🖼️",
    "face_reenactment": "🎭",
    "image_animation": "🎬",
    "face_reconstruction": "🧊",
}


_IMG_RE = re.compile(r'<img\s+[^>]*src="([^"]+)"[^>]*/?>') 

# ── markdown source validation ──────────────────────────────────────

_AI_GARBAGE_PATTERNS = [
    re.compile(r"</think>", re.IGNORECASE),
    re.compile(r"<think>", re.IGNORECASE),
    re.compile(r"<｜tool", re.IGNORECASE),
    re.compile(r"tool▁call", re.IGNORECASE),
    re.compile(r"<\|im_end\|>", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"```\s*(?:StrReplace|Read|Shell|Write)\b"),
    re.compile(r"</?assistant\b", re.IGNORECASE),
]

_CONFLUENCE_ALLOWED_TAGS = {
    "p", "br", "hr", "a", "em", "strong", "b", "i", "u", "s",
    "sub", "sup", "span", "div", "pre", "code", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "colgroup", "col",
    "img",
    "ac:image", "ac:structured-macro", "ac:parameter",
    "ac:plain-text-body", "ac:rich-text-body", "ac:link",
    "ri:url", "ri:attachment", "ri:page", "ri:space",
}

_HTML_TAG_RE = re.compile(r"</?([a-zA-Z][a-zA-Z0-9:\-]*)")


def validate_md_source(md_text: str, label: str = "") -> List[str]:
    """Check markdown source for AI artifacts. Returns list of warnings."""
    warnings: List[str] = []
    for pattern in _AI_GARBAGE_PATTERNS:
        m = pattern.search(md_text)
        if m:
            pos = m.start()
            line_no = md_text[:pos].count("\n") + 1
            snippet = md_text[pos:pos + 60].replace("\n", "\\n")
            warnings.append(
                f"[{label}] AI artifact at line {line_no}: '{snippet}...'"
            )
    return warnings


def validate_confluence_html(html: str, label: str = "") -> List[str]:
    """Check generated HTML for tags not in Confluence Storage Format whitelist."""
    warnings: List[str] = []
    seen: set = set()
    for m in _HTML_TAG_RE.finditer(html):
        tag = m.group(1).lower()
        if tag not in _CONFLUENCE_ALLOWED_TAGS and tag not in seen:
            seen.add(tag)
            pos = m.start()
            snippet = html[pos:pos + 80].replace("\n", "\\n")
            warnings.append(
                f"[{label}] Unknown tag <{tag}> at pos {pos}: '{snippet}...'"
            )
    return warnings

# Block macros (ac:image) must not sit inside <p>; Fabric rejects create/update otherwise.
_AC_IMAGE_IN_P_RE = re.compile(
    r"<p>\s*(<ac:image\b[^>]*>.*?</ac:image>)\s*</p>",
    re.DOTALL,
)


def md_to_confluence_storage(md_text: str) -> str:
    """Convert markdown text to Confluence Storage Format (XHTML)."""
    html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="xhtml",
    )
    html = _IMG_RE.sub(_img_to_ac_image, html)
    html = _AC_IMAGE_IN_P_RE.sub(r"\1", html)
    return html


def _xml_attr(url: str) -> str:
    """Escape for double-quoted XML/HTML attribute values (e.g. ri:value)."""
    return url.replace("&", "&amp;").replace('"', "&quot;")


def _img_to_ac_image(match: re.Match) -> str:
    """Replace <img src=\"...\"> with Confluence ac:image for external URLs."""
    url = match.group(1)
    if url.startswith("http"):
        safe = _xml_attr(url)
        return (
            f'<ac:image ac:width="700">'
            f'<ri:url ri:value="{safe}" />'
            f"</ac:image>"
        )
    return match.group(0)


def build_keywords_html(keywords: dict) -> str:
    """Build HTML representation of the search keywords config."""
    sections: List[str] = []
    for topic, kw_list in keywords.items():
        items = "".join(f"<li>{_escape(kw)}</li>" for kw in kw_list)
        sections.append(
            f"<h3>{_escape(topic)}</h3>"
            f"<ul>{items}</ul>"
        )
    return "<h2>Search Keywords</h2>" + "".join(sections)


def format_weekly_title(w_start: str, w_end: str) -> str:
    """Format week range.

    Same year: 'Feb 16 - Feb 22, 2024'.
    Year-spanning: 'Dec 29, 2025 - Jan 04, 2026' (avoids title collision
    when the same week appears under two different year parents).
    """
    start = datetime.strptime(w_start, "%Y-%m-%d")
    end = datetime.strptime(w_end, "%Y-%m-%d")
    if start.year == end.year:
        return (
            f"{start.strftime('%b %d')} - {end.strftime('%b %d')}, "
            f"{start.strftime('%Y')}"
        )
    return (
        f"{start.strftime('%b %d, %Y')} - {end.strftime('%b %d, %Y')}"
    )


def build_index_html(
    year_stats: Dict[str, Tuple[int, int, str]],
    prompt_url: Optional[str] = None,
    keywords_url: Optional[str] = None,
) -> str:
    """Build the main Papers index page with year links.

    year_stats: {year: (total_papers, analyzed_papers, page_url)}
    """
    ref_links: List[str] = []
    if prompt_url:
        ref_links.append(f'<a href="{prompt_url}">Analysis Prompt</a>')
    if keywords_url:
        ref_links.append(f'<a href="{keywords_url}">Search Keywords</a>')

    parts: List[str] = []
    if ref_links:
        parts.append(f'<p>{" | ".join(ref_links)}</p>')

    parts.append(
        '<table style="table-layout: fixed; width: 40%;">'
        "<thead><tr>"
        "<th>Year</th><th>Papers</th><th>Analyzed</th>"
        "</tr></thead><tbody>"
    )
    for year in sorted(year_stats.keys(), reverse=True):
        total, analyzed, url = year_stats[year]
        parts.append(
            f'<tr><td><a href="{url}">{year}</a></td>'
            f"<td>{total}</td><td>{analyzed}</td></tr>"
        )
    parts.append("</tbody></table>")
    return "".join(parts)


def _compute_week_links(
    df: pd.DataFrame,
    week_urls: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Build 'Current week' / 'Last week' links with stats.

    week_urls maps 'YYYY-MM-DD_YYYY-MM-DD' to page URL.
    """
    if week_urls is None or df.empty:
        return []

    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())
    current_start = monday.strftime("%Y-%m-%d")
    current_end = (monday + timedelta(days=6)).strftime("%Y-%m-%d")
    last_start = (monday - timedelta(days=7)).strftime("%Y-%m-%d")
    last_end = (monday - timedelta(days=1)).strftime("%Y-%m-%d")

    links: List[str] = []
    for label, w_start, w_end in [
        ("Current week", current_start, current_end),
        ("Last week", last_start, last_end),
    ]:
        key = f"{w_start}_{w_end}"
        url = week_urls.get(key)
        if not url:
            continue
        week_df = df[(df["date"] >= w_start) & (df["date"] <= w_end)]
        count = len(week_df)
        if count == 0:
            continue
        scores = pd.to_numeric(week_df["score"], errors="coerce").dropna()
        avg = f", avg {scores.mean():.1f}/10" if len(scores) > 0 else ""
        links.append(f'<a href="{url}">{label}</a> ({count}{avg})')
    return links


def build_papers_table_html(
    df: pd.DataFrame,
    base_url: str = "",
    prompt_url: Optional[str] = None,
    keywords_url: Optional[str] = None,
    week_urls: Optional[Dict[str, str]] = None,
) -> str:
    """Build an HTML table from the papers DataFrame for Confluence."""
    rows: List[str] = []
    for _, r in df.iterrows():
        title_link = f'<a href="{r["url"]}">{_escape(r["title"])}</a>'

        code_cell = ""
        if r.get("code_url"):
            code_cell = f'<a href="{r["code_url"]}">💻</a>'

        score = r.get("score", "")
        score_cell = f"{score}/10" if score else ""

        analysis_cell = _build_analysis_links(
            r.get("confluence_en_url", ""),
            r.get("confluence_ru_url", ""),
        )

        rows.append(
            "<tr>"
            f"<td>{r['date']}</td>"
            f"<td>{title_link}</td>"
            f"<td>{_escape(r.get('authors', ''))}</td>"
            f"<td>{_topic_with_emoji(r.get('topic', ''))}</td>"
            f"<td>{score_cell}</td>"
            f"<td>{code_cell}</td>"
            f"<td>{analysis_cell}</td>"
            "</tr>"
        )

    header = (
        "<tr>"
        "<th>Date</th>"
        "<th>Title</th>"
        "<th>Authors</th>"
        "<th>Topic</th>"
        "<th>Score</th>"
        "<th>Code</th>"
        "<th>Analysis</th>"
        "</tr>"
    )

    ref_links: List[str] = []
    if prompt_url:
        ref_links.append(f'<a href="{prompt_url}">Analysis Prompt</a>')
    if keywords_url:
        ref_links.append(f'<a href="{keywords_url}">Search Keywords</a>')
    week_link_items = _compute_week_links(df, week_urls)
    ref_links.extend(week_link_items)
    ref_line = " | ".join(ref_links)
    header_html = f"<p>Total papers: {len(df)}"
    if ref_line:
        header_html += f" &nbsp;|&nbsp; {ref_line}"
    header_html += "</p>"

    # Column widths (%). Title widest; Date/Authors/Topic small; Score/Code/Analysis tiny.
    colgroup = (
        '<colgroup>'
        '<col style="width: 11%" />'  # Date
        '<col style="width: 50%" />'  # Title
        '<col style="width: 15%" />'  # Authors
        '<col style="width: 5%" />'   # Topic
        '<col style="width: 5%" />'   # Score
        '<col style="width: 5%" />'   # Code
        '<col style="width: 9%" />'   # Analysis
        '</colgroup>'
    )
    return (
        f"{header_html}"
        f'<table style="table-layout: fixed; width: 100%;">{colgroup}'
        f"<thead>{header}</thead>"
        f'<tbody>{"".join(rows)}</tbody>'
        f"</table>"
    )


def _build_analysis_links(en_url: str, ru_url: str) -> str:
    """Build EN / RU links cell for the table."""
    parts: List[str] = []
    if en_url:
        parts.append(f'<a href="{en_url}">EN</a>')
    if ru_url:
        parts.append(f'<a href="{ru_url}">RU</a>')
    return " / ".join(parts) if parts else ""


def build_weekly_page_html(
    papers_df: pd.DataFrame,
    analysis_dir: str,
    week_start: str,
    week_end: str,
) -> str:
    """Build a weekly page with TOC and all analyses for the given period."""
    analysis_path = Path(analysis_dir)
    toc_items: List[str] = []
    sections: List[str] = []

    for _, row in papers_df.iterrows():
        arxiv_id = str(row["arxiv_id"]).strip()
        anchor = f"paper-{arxiv_id.replace('.', '-')}"
        score = row.get("score", "")
        score_badge = f" [{score}/10]" if score else ""
        title = _escape(row["title"])

        toc_items.append(
            f'<li><a href="#{anchor}">{title}</a>{score_badge}</li>'
        )

        md_file = analysis_path / f"{arxiv_id}.md"
        anchor_macro = (
            f'<ac:structured-macro ac:name="anchor">'
            f'<ac:parameter ac:name="">{anchor}</ac:parameter>'
            f"</ac:structured-macro>"
        )
        heading = (
            f'{anchor_macro}'
            f'<h1><a href="{row["url"]}">{title}</a></h1>'
        )
        if md_file.exists():
            md_content = md_file.read_text(encoding="utf-8")
            md_warnings = validate_md_source(md_content, label=arxiv_id)
            if md_warnings:
                for w in md_warnings:
                    logger.warning("Skipping paper (bad md): %s", w)
                sections.append(
                    heading
                    + f"<p><em>Analysis skipped: source file contains "
                    f"invalid content ({arxiv_id}.md)</em></p>"
                )
            else:
                html_content = md_to_confluence_storage(md_content)
                html_warnings = validate_confluence_html(
                    html_content, label=arxiv_id
                )
                for w in html_warnings:
                    logger.warning("Confluence HTML issue: %s", w)
                sections.append(heading)
                first_h1_removed = _remove_first_h1(html_content)
                sections.append(first_h1_removed)
        else:
            sections.append(
                heading
                + f"<p><em>Analysis file not found: {arxiv_id}.md</em></p>"
            )

        sections.append("<hr/>")

    toc_html = (
        f"<p><strong>Period:</strong> {week_start} — {week_end} | "
        f"<strong>Papers:</strong> {len(papers_df)}</p>"
        f"<h2>Contents</h2>"
        f'<ol>{"".join(toc_items)}</ol>'
        f"<hr/>"
    )

    return toc_html + "\n".join(sections)


def _remove_first_h1(html: str) -> str:
    """Remove the first <h1>...</h1> tag to avoid duplicate titles."""
    return re.sub(r"<h1[^>]*>.*?</h1>", "", html, count=1, flags=re.DOTALL)


def _topic_with_emoji(topic: str) -> str:
    """Return only emoji for table display; unknown topic as-is."""
    if not topic:
        return ""
    return TOPIC_EMOJI.get(topic, topic)


def _escape(text: str) -> str:
    """Escape special characters for XHTML."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
