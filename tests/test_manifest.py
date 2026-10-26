"""Tests for the integration manifest."""

import json
import tomllib
from pathlib import Path

from custom_components.de_ev.const import DOMAIN

ROOT = Path(__file__).parents[1]


def test_manifest_matches_constants() -> None:
    """The manifest is installable and consistent with the constants."""
    manifest_path = ROOT / "custom_components" / DOMAIN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    assert "http" in manifest["dependencies"]
    assert "frontend" in manifest["after_dependencies"]
    assert manifest["requirements"] == ["tinytuya>=1.20.0"]


def test_manifest_version_matches_project() -> None:
    """The manifest and the Python package share the same version."""
    manifest_path = ROOT / "custom_components" / DOMAIN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert manifest["version"] == project["project"]["version"]
