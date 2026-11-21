"""Tests for config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from fundwatch.config import ConfigError, load_config


def test_valid_config_loading(tmp_path: Path) -> None:
    cfg = {
        "poll_interval_minutes": 25,
        "feeds": [{"name": "TestFeed", "url": "https://example.com/feed"}],
        "notifiers": [{"type": "telegram", "enabled": False}],
    }
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(cfg))

    settings = load_config(config_path=cfg_file, enforce_secrets=True)
    assert settings.poll_interval_minutes == 25
    assert len(settings.feeds) == 1
    assert settings.feeds[0].name == "TestFeed"


def test_poll_interval_minimum_enforced(tmp_path: Path) -> None:
    cfg = {
        "poll_interval_minutes": 10,  # Below required 15 min
    }
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(cfg))

    with pytest.raises(ConfigError, match="poll_interval_minutes must be at least 15"):
        load_config(config_path=cfg_file, enforce_secrets=False)


def test_missing_secrets_enforcement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    cfg = {
        "poll_interval_minutes": 20,
        "notifiers": [{"type": "telegram", "enabled": True}],
    }
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(cfg))

    with pytest.raises(ConfigError, match="missing required secrets"):
        load_config(config_path=cfg_file, enforce_secrets=True)
