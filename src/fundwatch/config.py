"""Configuration loading and validation for fundwatch."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from fundwatch.models import Settings


class ConfigError(Exception):
    """Raised when configuration or required secrets are invalid or missing."""


def validate_secrets(settings: Settings) -> None:
    """Validate that all enabled components have their required secrets present."""
    missing: list[str] = []

    for notifier in settings.notifiers:
        if not notifier.enabled:
            continue
        ntype = notifier.type.lower()
        if ntype == "telegram":
            if not settings.telegram_bot_token:
                missing.append("TELEGRAM_BOT_TOKEN for Telegram notifier")
            if not settings.telegram_chat_id:
                missing.append("TELEGRAM_CHAT_ID for Telegram notifier")
        elif ntype == "slack":
            if not settings.slack_webhook_url:
                missing.append("SLACK_WEBHOOK_URL for Slack notifier")
        elif ntype == "ntfy":
            if not settings.ntfy_server:
                missing.append("NTFY_SERVER for ntfy notifier")
            if not notifier.topic:
                missing.append("topic in config for ntfy notifier")
        elif ntype == "email":
            if not settings.smtp_host:
                missing.append("SMTP_HOST for email notifier")
            if not settings.smtp_user:
                missing.append("SMTP_USER for email notifier")
            if not settings.smtp_password:
                missing.append("SMTP_PASSWORD for email notifier")
            if not settings.email_to:
                missing.append("EMAIL_TO for email notifier")
        else:
            raise ConfigError(f"Unknown notifier type: {notifier.type}")

    if settings.llm_extraction.enabled and not settings.anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY for LLM extraction")

    if missing:
        formatted = "\n  - " + "\n  - ".join(missing)
        raise ConfigError(f"Configuration validation failed: missing required secrets:{formatted}")


def load_config(
    config_path: str | Path | None = None,
    env_path: str | Path | None = None,
    enforce_secrets: bool = True,
) -> Settings:
    """Load config.yaml, overlay environment variables from .env / os.environ, and validate."""
    if env_path is not None:
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    # Determine config file path
    if config_path is None:
        cfg_env = os.environ.get("CONFIG_PATH", "config.yaml")
        path = Path(cfg_env)
    else:
        path = Path(config_path)

    raw_data: dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    raw_data = loaded
                elif loaded is not None:
                    raise ConfigError(f"Invalid YAML content in {path}: expected dictionary")
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML from {path}: {e}") from e

    # Overlay environment variables
    if "db_path" not in raw_data:
        raw_data["db_path"] = os.environ.get("DB_PATH", "./data/fundwatch.db")
    elif "DB_PATH" in os.environ and config_path is None:
        raw_data["db_path"] = os.environ["DB_PATH"]

    if "log_level" not in raw_data:
        raw_data["log_level"] = os.environ.get("LOG_LEVEL", "INFO").upper()
    elif "LOG_LEVEL" in os.environ and config_path is None:
        raw_data["log_level"] = os.environ["LOG_LEVEL"].upper()

    if "TELEGRAM_BOT_TOKEN" in os.environ:
        raw_data["telegram_bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]
    if "TELEGRAM_CHAT_ID" in os.environ:
        raw_data["telegram_chat_id"] = os.environ["TELEGRAM_CHAT_ID"]
    if "SLACK_WEBHOOK_URL" in os.environ:
        raw_data["slack_webhook_url"] = os.environ["SLACK_WEBHOOK_URL"]
    if "NTFY_SERVER" in os.environ:
        raw_data["ntfy_server"] = os.environ["NTFY_SERVER"]
    if "SMTP_HOST" in os.environ:
        raw_data["smtp_host"] = os.environ["SMTP_HOST"]
    if "SMTP_PORT" in os.environ:
        try:
            raw_data["smtp_port"] = int(os.environ["SMTP_PORT"])
        except ValueError:
            pass
    if "SMTP_USER" in os.environ:
        raw_data["smtp_user"] = os.environ["SMTP_USER"]
    if "SMTP_PASSWORD" in os.environ:
        raw_data["smtp_password"] = os.environ["SMTP_PASSWORD"]
    if "SMTP_FROM" in os.environ:
        raw_data["smtp_from"] = os.environ["SMTP_FROM"]
    elif "EMAIL_FROM" in os.environ:
        raw_data["smtp_from"] = os.environ["EMAIL_FROM"]
    if "EMAIL_TO" in os.environ:
        raw_data["email_to"] = os.environ["EMAIL_TO"]
    if "ANTHROPIC_API_KEY" in os.environ:
        raw_data["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]
    if "HUNTER_API_KEY" in os.environ:
        raw_data["hunter_api_key"] = os.environ["HUNTER_API_KEY"]
    if "RESUME_PATH" in os.environ:
        raw_data["resume_path"] = os.environ["RESUME_PATH"]
    if "CANDIDATE_NAME" in os.environ:
        raw_data["candidate_name"] = os.environ["CANDIDATE_NAME"]
    if "CANDIDATE_TITLE" in os.environ:
        raw_data["candidate_title"] = os.environ["CANDIDATE_TITLE"]
    if "CANDIDATE_EMAIL" in os.environ:
        raw_data["candidate_email"] = os.environ["CANDIDATE_EMAIL"]
    if "CANDIDATE_PHONE" in os.environ:
        raw_data["candidate_phone"] = os.environ["CANDIDATE_PHONE"]
    if "CANDIDATE_PORTFOLIO" in os.environ:
        raw_data["candidate_portfolio"] = os.environ["CANDIDATE_PORTFOLIO"]
    if "CANDIDATE_GITHUB" in os.environ:
        raw_data["candidate_github"] = os.environ["CANDIDATE_GITHUB"]
    if "CANDIDATE_LINKEDIN" in os.environ:
        raw_data["candidate_linkedin"] = os.environ["CANDIDATE_LINKEDIN"]
    if "FIND_FOUNDER_EMAILS" in os.environ:
        raw_data["find_founder_emails"] = os.environ["FIND_FOUNDER_EMAILS"].lower() in {
            "true",
            "1",
            "yes",
        }

    try:
        settings = Settings(**raw_data)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}") from e

    if enforce_secrets:
        validate_secrets(settings)

    return settings
