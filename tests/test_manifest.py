"""Tests for the integration manifest."""

import json
from pathlib import Path

from custom_components.de_ev.const import DOMAIN, VERSION


def test_manifest_matches_constants() -> None:
    """The manifest is installable and consistent with the constants."""
    manifest_path = (
        Path(__file__).parents[1] / "custom_components" / DOMAIN / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["domain"] == DOMAIN
    assert manifest["version"] == VERSION
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == ["tinytuya>=1.20.0"]
