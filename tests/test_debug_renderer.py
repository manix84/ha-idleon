"""Tests for parsed data debug rendering."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_debug_renderer_writes_json_and_html(tmp_path: Path) -> None:
    """Test parsed debug output can be generated from sanitized fixtures."""
    result = subprocess.run(
        [
            str(ROOT / "scripts/render-debug-parsed-data"),
            str(ROOT / "tests/fixtures/wrapped_idleon_export_sample.json"),
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    json_path = tmp_path / "parsed-data.json"
    html_path = tmp_path / "parsed-data.html"

    assert "parsed-data.json" in result.stdout
    assert json_path.exists()
    assert html_path.exists()

    rendered = json.loads(json_path.read_text())
    assert rendered[0]["parsed"]["character_count"] == 2
    assert rendered[0]["parsed"]["characters"][0]["name"] == "Alpha Archer"
    assert rendered[0]["parsed"]["characters"][0]["current_activity"] == (
        "Fighting: Green Mushroom"
    )

    html = html_path.read_text()
    assert "HA Idleon Parsed Data Debug" in html
    assert "Alpha Archer" in html
