import os

import yaml
from typing import Dict, List, Optional


class Config:
    """Loads and provides access to project configuration."""

    def __init__(self, config_path: str = "config.yaml") -> None:
        with open(config_path, encoding="utf-8") as f:
            self._data: Dict = yaml.safe_load(f)

    @property
    def keywords(self) -> Dict[str, List[str]]:
        return self._data.get("keywords", {})

    @property
    def arxiv_max_results(self) -> int:
        return self._data.get("arxiv", {}).get("max_results_per_topic", 200)

    @property
    def arxiv_sort_by(self) -> str:
        return self._data.get("arxiv", {}).get("sort_by", "submitted")

    @property
    def arxiv_search_field(self) -> str:
        return self._data.get("arxiv", {}).get("search_field", "abs")

    @property
    def arxiv_categories(self) -> List[str]:
        return self._data.get("arxiv", {}).get("categories", [])

    @property
    def arxiv_date_from(self) -> Optional[str]:
        return self._data.get("arxiv", {}).get("date_from")

    @property
    def arxiv_date_to(self) -> Optional[str]:
        return self._data.get("arxiv", {}).get("date_to")

    def set_date_from(self, value: str) -> None:
        self._data.setdefault("arxiv", {})["date_from"] = value

    def set_date_to(self, value: str) -> None:
        self._data.setdefault("arxiv", {})["date_to"] = value

    @property
    def csv_file(self) -> str:
        return self._data.get("paths", {}).get("csv_file", "data/papers.csv")

    @property
    def db_file(self) -> str:
        return self._data.get("paths", {}).get("db_file", "data/papers.db")

    @property
    def originals_dir(self) -> str:
        return self._data.get("paths", {}).get("originals_dir", "papers/originals")

    @property
    def analysis_dir(self) -> str:
        return self._data.get("paths", {}).get("analysis_dir", "papers/analysis")

    @property
    def analysis_ru_dir(self) -> str:
        return self._data.get("paths", {}).get("analysis_ru_dir", "papers/analysis_ru")

    @property
    def figures_dir(self) -> str:
        return self._data.get("paths", {}).get("figures_dir", "papers/figures")

    @property
    def code_search_enabled(self) -> bool:
        return self._data.get("code_search", {}).get("enabled", True)

    @property
    def code_search_delay(self) -> float:
        return self._data.get("code_search", {}).get("delay", 1.0)

    @property
    def download_delay(self) -> float:
        return self._data.get("download", {}).get("delay", 3.0)

    @property
    def download_timeout(self) -> int:
        return self._data.get("download", {}).get("timeout", 120)

    @property
    def confluence_url(self) -> str:
        return os.environ.get("CONFLUENCE_URL", "")

    @property
    def confluence_token(self) -> str:
        return os.environ.get("CONFLUENCE_TOKEN", "")

    @property
    def confluence_email(self) -> str:
        return os.environ.get("CONFLUENCE_EMAIL", "")

    @property
    def confluence_space_key(self) -> str:
        return self._data.get("confluence", {}).get("space_key", "")

    @property
    def confluence_parent_page_id(self) -> str:
        return self._data.get("confluence", {}).get("parent_page_id", "")

    @property
    def confluence_papers_page_title(self) -> str:
        return self._data.get("confluence", {}).get("papers_page_title", "Papers")

    @property
    def confluence_ru_page_title(self) -> str:
        return self._data.get("confluence", {}).get("ru_page_title", "RU")

    @property
    def confluence_prompt_page_title(self) -> str:
        return self._data.get("confluence", {}).get(
            "prompt_page_title", "Analysis Prompt"
        )

    @property
    def confluence_keywords_page_title(self) -> str:
        return self._data.get("confluence", {}).get(
            "keywords_page_title", "Search Keywords"
        )

    @property
    def publish_state_file(self) -> str:
        return self._data.get("paths", {}).get(
            "publish_state", "data/publish_state.json"
        )

    @property
    def slack_webhook_url(self) -> str:
        """Slack Incoming Webhook URL for weekly reports (from env)."""
        return os.environ.get("SLACK_WEBHOOK_URL", "")

    @property
    def slack_bot_token(self) -> str:
        """Slack Bot User OAuth Token (xoxb-...) for chat.postMessage (from env)."""
        return os.environ.get("SLACK_BOT_TOKEN", "")

    @property
    def slack_channel(self) -> str:
        """Slack channel ID (C...) or name (#channel) for weekly reports (from env)."""
        return os.environ.get("SLACK_CHANNEL", "")

    @property
    def openrouter_api_key(self) -> str:
        """OpenRouter API key (from env)."""
        return os.environ.get("OPENROUTER_API_KEY", "")

    @property
    def openrouter_base_url(self) -> str:
        return self._data.get("openrouter", {}).get(
            "base_url", "https://openrouter.ai/api/v1"
        )

    @property
    def llm_model(self) -> str:
        """OpenRouter model slug for paper analysis."""
        return self._data.get("openrouter", {}).get(
            "model", "anthropic/claude-sonnet-4.6"
        )

    @property
    def llm_translate_model(self) -> str:
        """OpenRouter model slug for RU translation (defaults to llm_model)."""
        return self._data.get("openrouter", {}).get(
            "translate_model", self.llm_model
        )

    @property
    def llm_max_tokens(self) -> int:
        return int(self._data.get("openrouter", {}).get("max_tokens", 8000))

    @property
    def llm_temperature(self) -> float:
        return float(self._data.get("openrouter", {}).get("temperature", 0.3))

    @property
    def pdf_max_chars(self) -> int:
        """Truncate extracted PDF text to this many characters before sending to LLM."""
        return int(self._data.get("openrouter", {}).get("pdf_max_chars", 120000))
