from __future__ import annotations

from pathlib import Path
import json

from openapi_spec_validator import validate


def test_external_openapi_spec_is_valid() -> None:
    path = Path(__file__).resolve().parents[3] / "data" / "openapi.json"
    validate(json.loads(path.read_text(encoding="utf-8")))


def test_internal_openapi_spec_is_valid() -> None:
    path = Path(__file__).resolve().parents[3] / "src" / "openapi.json"
    validate(json.loads(path.read_text(encoding="utf-8")))
