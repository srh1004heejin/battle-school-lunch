from __future__ import annotations

import pytest

from app.settings import Settings


def test_settings_from_env_requires_api_key() -> None:
    with pytest.raises(RuntimeError, match="NEIS_API_KEY"):
        Settings.from_env({})


def test_settings_from_env_reads_copilot_timeout() -> None:
    settings = Settings.from_env(
        {
            "NEIS_API_KEY": "test-key",
            "GITHUB_COPILOT_TIMEOUT_SECONDS": "240",
        }
    )

    assert settings.github_copilot_timeout_seconds == 240
