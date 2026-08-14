from __future__ import annotations

import pytest

from app.settings import Settings


def test_settings_from_env_requires_api_key() -> None:
    with pytest.raises(RuntimeError, match="NEIS_API_KEY"):
        Settings.from_env({})
