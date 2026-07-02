from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    openai_api_key: str
    openai_model: str
    openai_timeout_seconds: float
    openai_max_output_tokens: int | None
    allowed_user_ids: set[int]
    data_dir: Path
    enable_web_search: bool


def load_config() -> Config:
    load_dotenv()

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    allowed_raw = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").strip()
    allowed_user_ids = {
        int(item.strip())
        for item in allowed_raw.split(",")
        if item.strip()
    }

    data_dir = Path(os.getenv("BOT_DATA_DIR", ".data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    max_output_raw = os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "").strip()

    return Config(
        telegram_bot_token=telegram_bot_token,
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5").strip() or "gpt-5",
        openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "240")),
        openai_max_output_tokens=int(max_output_raw) if max_output_raw else None,
        allowed_user_ids=allowed_user_ids,
        data_dir=data_dir,
        enable_web_search=os.getenv("ENABLE_WEB_SEARCH", "true").strip().lower()
        in {"1", "true", "yes", "y"},
    )
