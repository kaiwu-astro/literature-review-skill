from __future__ import annotations

from pathlib import Path

import pytest

import config_loader


def test_load_config_uses_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLR_API_TIMEOUT", raising=False)
    monkeypatch.delenv("SLR_RATE_LIMIT", raising=False)
    monkeypatch.delenv("ADS_API_TOKEN", raising=False)

    cfg = tmp_path / "config.yaml"
    cfg.write_text("api:\n  semantic_scholar:\n    timeout: 10\n", encoding="utf-8")
    monkeypatch.setattr(config_loader, "_CONFIG_PATH", cfg)
    config_loader.reload_config()

    first = config_loader.load_config()
    cfg.write_text("api:\n  semantic_scholar:\n    timeout: 99\n", encoding="utf-8")
    second = config_loader.load_config()

    assert first["api"]["semantic_scholar"]["timeout"] == 10
    assert second["api"]["semantic_scholar"]["timeout"] == 10


def test_load_config_force_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLR_API_TIMEOUT", raising=False)
    monkeypatch.delenv("SLR_RATE_LIMIT", raising=False)
    monkeypatch.delenv("ADS_API_TOKEN", raising=False)

    cfg = tmp_path / "config.yaml"
    cfg.write_text("api:\n  semantic_scholar:\n    timeout: 10\n", encoding="utf-8")
    monkeypatch.setattr(config_loader, "_CONFIG_PATH", cfg)
    config_loader.reload_config()

    config_loader.load_config()
    cfg.write_text("api:\n  semantic_scholar:\n    timeout: 99\n", encoding="utf-8")
    loaded = config_loader.load_config(force_reload=True)

    assert loaded["api"]["semantic_scholar"]["timeout"] == 99


def test_env_override_applies_timeout_and_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    config_loader.reload_config()
    monkeypatch.setenv("SLR_API_TIMEOUT", "42")
    monkeypatch.setenv("SLR_RATE_LIMIT", "77")
    monkeypatch.setenv("ADS_API_TOKEN", "token-x")

    cfg = config_loader._apply_env_overrides({})

    assert cfg["api"]["semantic_scholar"]["timeout"] == 42
    assert cfg["api"]["openalex"]["timeout"] == 42
    assert cfg["api"]["ads"]["timeout"] == 42
    assert cfg["api"]["semantic_scholar"]["rate_limit"] == 77
    assert cfg["api"]["ads"]["token"] == "token-x"


def test_missing_config_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing.yaml"
    monkeypatch.setattr(config_loader, "_CONFIG_PATH", missing)
    config_loader.reload_config()

    with pytest.raises(FileNotFoundError):
        config_loader.load_config(force_reload=True)
