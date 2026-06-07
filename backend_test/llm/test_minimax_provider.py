from __future__ import annotations

from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import config
from llm.model_factory import build_chat_model


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    config.get_settings.cache_clear()
    config._env_file_values.cache_clear()
    yield
    config.get_settings.cache_clear()
    config._env_file_values.cache_clear()


def _write_env(tmp_path: Path, content: str) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    return env_file


def test_get_settings_resolves_minimax_defaults_from_temp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = _write_env(
        tmp_path,
        "\n".join(
            [
                "LLM_PROVIDER=minimax",
                "LLM_API_KEY=test-minimax-key",
                "EMBEDDING_PROVIDER=bailian",
                "EMBEDDING_API_KEY=test-embedding-key",
            ]
        ),
    )
    monkeypatch.setattr(config, "_resolve_env_file_path", lambda: env_file)

    settings = config.get_settings()

    assert settings.llm_provider == "minimax"
    assert settings.llm_model == "MiniMax-M2.7"
    assert settings.llm_api_key == "test-minimax-key"
    assert settings.llm_base_url == "https://api.minimaxi.com/v1"


def test_get_settings_normalizes_minimax_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = _write_env(
        tmp_path,
        "\n".join(
            [
                "LLM_PROVIDER=minimaxi",
                "LLM_API_KEY=test-minimax-key",
            ]
        ),
    )
    monkeypatch.setattr(config, "_resolve_env_file_path", lambda: env_file)

    settings = config.get_settings()

    assert settings.llm_provider == "minimax"


def test_build_chat_model_returns_chat_openai_for_minimax(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = _write_env(
        tmp_path,
        "\n".join(
            [
                "LLM_PROVIDER=minimax",
                "LLM_API_KEY=test-minimax-key",
                "LLM_MODEL=MiniMax-M2.7",
                "LLM_BASE_URL=https://api.minimaxi.com/v1",
            ]
        ),
    )
    monkeypatch.setattr(config, "_resolve_env_file_path", lambda: env_file)

    model = build_chat_model()

    assert model.model_name == "MiniMax-M2.7"
    assert str(model.openai_api_base) == "https://api.minimaxi.com/v1"


def test_build_chat_model_rejects_missing_minimax_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = _write_env(
        tmp_path,
        "\n".join(
            [
                "LLM_PROVIDER=minimax",
                "LLM_MODEL=MiniMax-M2.7",
                "LLM_BASE_URL=https://api.minimaxi.com/v1",
            ]
        ),
    )
    monkeypatch.setattr(config, "_resolve_env_file_path", lambda: env_file)

    with pytest.raises(RuntimeError, match="Missing API key for provider minimax"):
        build_chat_model()
