"""LLM-based paper analyzer via OpenRouter (OpenAI-compatible API).

Pipeline:
  1. Extract text from local PDF (pymupdf).
  2. Load figures captions from papers/figures/{arxiv_id}.json (if any).
  3. Send a single prompt to LLM (Claude Sonnet 4.6 by default) -> EN markdown.
  4. Send the EN markdown back to LLM for RU translation -> RU markdown.
  5. Save both files; caller updates CSV (processed=1, score, code_url) via sync.
"""
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # type: ignore[import-untyped]
from openai import OpenAI  # type: ignore[import-untyped]
from openai import APIError, APITimeoutError, RateLimitError  # type: ignore[import-untyped]


logger = logging.getLogger(__name__)


PROMPT_TEMPLATE_PATH = Path("prompts/analyze_paper.md")


def _load_prompt_template() -> str:
    if not PROMPT_TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Prompt template not found: {PROMPT_TEMPLATE_PATH}"
        )
    return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")


def extract_pdf_text(pdf_path: Path, max_chars: int = 120000) -> str:
    """Extract plain text from a PDF, normalised and truncated."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF missing: {pdf_path}")
    parts: List[str] = []
    with fitz.open(str(pdf_path)) as doc:
        for page in doc:
            txt = page.get_text("text") or ""
            parts.append(txt.strip())
    raw = "\n\n".join(p for p in parts if p)
    # Collapse repeated blank lines, drop excessive whitespace
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    if len(raw) > max_chars:
        head = raw[: int(max_chars * 0.85)]
        tail = raw[-int(max_chars * 0.15):]
        raw = (
            head
            + "\n\n[... TRUNCATED MIDDLE — paper too long for context ...]\n\n"
            + tail
        )
    return raw


def load_figures(figures_path: Path) -> List[Dict]:
    """Return list of {index, url, caption} or empty list if file missing."""
    if not figures_path.exists():
        return []
    try:
        data = json.loads(figures_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Bad figures JSON %s: %s", figures_path, e)
        return []
    if not isinstance(data, list):
        return []
    return data


def _format_figures_block(figures: List[Dict]) -> str:
    """Format figures list as markdown bullets for the prompt."""
    if not figures:
        return "(no figures available)"
    lines: List[str] = []
    for f in figures:
        idx = f.get("index", "?")
        url = f.get("url", "")
        cap = (f.get("caption") or "").strip()
        lines.append(f"- index={idx} | url={url}\n  caption: {cap}")
    return "\n".join(lines)


def build_analysis_messages(
    template: str,
    arxiv_id: str,
    title: str,
    url: str,
    date: str,
    authors: str,
    code_url: str,
    pdf_text: str,
    figures: List[Dict],
) -> List[Dict]:
    """Build chat messages for the EN analysis call."""
    figures_block = _format_figures_block(figures)
    user = f"""You are an expert ML researcher producing structured Markdown analyses of academic papers.

Follow the analysis instructions and template below. Output ONLY the final Markdown content
(no preamble, no code fences around the whole document — just the Markdown itself).

=== ANALYSIS INSTRUCTIONS AND TEMPLATE ===
{template}

=== PAPER METADATA ===
- arxiv_id: {arxiv_id}
- title: {title}
- url: {url}
- date: {date}
- authors: {authors}
- code_url (from CSV): {code_url or "(empty — discover from paper if present)"}

=== AVAILABLE FIGURES (pick ONE that best illustrates the model architecture/pipeline) ===
{figures_block}

When you fill in the `![architecture]({{url}})` line, use the `url` value of the figure
whose caption best matches "architecture", "pipeline", "framework overview" or "model structure".
If none of the figures look architectural, omit the architecture image line entirely.

=== PAPER TEXT (extracted from PDF) ===
{pdf_text}

=== END OF PAPER TEXT ===

Now produce the full Markdown analysis following the template exactly. Remember:
- Use Unicode/plain-text formulas (no LaTeX `$...$`).
- The `## Recommendation: {{score}}/10` line must contain ONLY the score number, no explanation.
- Output the Markdown only, no surrounding fences.
"""
    return [{"role": "user", "content": user}]


def build_translation_messages(en_markdown: str) -> List[Dict]:
    """Build chat messages for the EN -> RU translation call."""
    user = f"""Translate the following English Markdown analysis of an academic paper into Russian.

Strict rules:
- Preserve the Markdown structure 1:1: headings, lists, tables, code blocks, image links, hyperlinks.
- Translate ONLY natural language text. Do NOT translate:
  - arxiv_id, URLs, hyperlink targets
  - tag values in the `## Tags` section (keep them as-is in English)
  - method names, model names, dataset names, metric names (e.g. SadTalker, HDTF, FID, Sync-C)
  - inline code, formulas, variable names
- Keep the `## Recommendation: N/10` line exactly as-is.
- Translate the Tags SECTION HEADING but keep the actual tag values untranslated (still hyphenated, English).
- Output the Russian Markdown only, no preamble, no code fences around the whole document.

=== ENGLISH MARKDOWN ===
{en_markdown}
"""
    return [{"role": "user", "content": user}]


class LLMClient:
    """Thin wrapper around OpenAI SDK pointed at OpenRouter."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "anthropic/claude-sonnet-4.6",
        max_tokens: int = 8000,
        temperature: float = 0.3,
    ) -> None:
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is empty")
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/avatar-papers",
                "X-Title": "Avatar Papers Analyzer",
            },
        )
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def chat(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        retries: int = 3,
        retry_delay: float = 5.0,
    ) -> Tuple[str, Dict]:
        """Call chat completion. Returns (content, usage_dict)."""
        last_err: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=model or self.model,
                    messages=messages,
                    max_tokens=max_tokens or self.max_tokens,
                    temperature=(
                        temperature
                        if temperature is not None
                        else self.temperature
                    ),
                )
                choice = resp.choices[0]
                content = choice.message.content or ""
                usage = getattr(resp, "usage", None)
                usage_dict = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(usage, "completion_tokens", 0),
                    "total_tokens": getattr(usage, "total_tokens", 0),
                }
                return content.strip(), usage_dict
            except (RateLimitError, APITimeoutError, APIError) as e:
                last_err = e
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s",
                    attempt, retries, e,
                )
                if attempt < retries:
                    time.sleep(retry_delay * attempt)
        raise RuntimeError(f"LLM call failed after {retries} attempts: {last_err}")


def _strip_code_fence(text: str) -> str:
    """Remove leading/trailing ```markdown ... ``` fence if model wrapped it."""
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1:]
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


def analyze_paper(
    arxiv_id: str,
    paper_meta: Dict,
    originals_dir: Path,
    figures_dir: Path,
    analysis_dir: Path,
    analysis_ru_dir: Path,
    client: LLMClient,
    translate_model: Optional[str] = None,
    pdf_max_chars: int = 120000,
    skip_translation: bool = False,
) -> Dict:
    """Analyze a single paper end-to-end. Returns stats dict.

    paper_meta should contain: title, url, date, authors, code_url.
    """
    pdf_path = originals_dir / f"{arxiv_id}.pdf"
    figures_path = figures_dir / f"{arxiv_id}.json"
    en_path = analysis_dir / f"{arxiv_id}.md"
    ru_path = analysis_ru_dir / f"{arxiv_id}.md"

    en_path.parent.mkdir(parents=True, exist_ok=True)
    ru_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Analyzing %s — extracting PDF text", arxiv_id)
    pdf_text = extract_pdf_text(pdf_path, max_chars=pdf_max_chars)
    figures = load_figures(figures_path)
    template = _load_prompt_template()

    messages = build_analysis_messages(
        template,
        arxiv_id=arxiv_id,
        title=paper_meta.get("title", ""),
        url=paper_meta.get("url", ""),
        date=paper_meta.get("date", ""),
        authors=paper_meta.get("authors", ""),
        code_url=paper_meta.get("code_url", ""),
        pdf_text=pdf_text,
        figures=figures,
    )

    logger.info(
        "Analyzing %s — calling %s (pdf_chars=%d, figures=%d)",
        arxiv_id, client.model, len(pdf_text), len(figures),
    )
    en_md, en_usage = client.chat(messages)
    en_md = _strip_code_fence(en_md)
    en_path.write_text(en_md, encoding="utf-8")
    logger.info(
        "Analyzing %s — EN saved (%d chars, %d→%d tokens)",
        arxiv_id, len(en_md),
        en_usage["prompt_tokens"], en_usage["completion_tokens"],
    )

    ru_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    if not skip_translation:
        logger.info("Analyzing %s — translating to RU", arxiv_id)
        ru_messages = build_translation_messages(en_md)
        ru_md, ru_usage = client.chat(
            ru_messages, model=translate_model
        )
        ru_md = _strip_code_fence(ru_md)
        ru_path.write_text(ru_md, encoding="utf-8")
        logger.info(
            "Analyzing %s — RU saved (%d chars, %d→%d tokens)",
            arxiv_id, len(ru_md),
            ru_usage["prompt_tokens"], ru_usage["completion_tokens"],
        )

    return {
        "arxiv_id": arxiv_id,
        "en_chars": len(en_md),
        "en_usage": en_usage,
        "ru_usage": ru_usage,
    }
