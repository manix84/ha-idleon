"""Tests for parsed data debug rendering."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_debug_renderer_writes_json_and_html(tmp_path: Path) -> None:
    """Test parsed debug output can be generated from sanitized fixtures."""
    clean_reference = tmp_path / "cleanData.json"
    clean_reference.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "name": "Clean Archer",
                        "level": 101,
                        "class": 20,
                        "currentMap": 7,
                        "AFKtarget": "mushG",
                        "timeAway": 3600,
                        "inventory": [],
                    }
                ]
            }
        )
    )
    result = subprocess.run(
        [
            str(ROOT / "scripts/render-debug-parsed-data"),
            str(ROOT / "tests/fixtures/wrapped_idleon_export_sample.json"),
            "--clean-reference",
            str(clean_reference),
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
    assert rendered[0]["generated_at"]
    assert rendered[0]["toolbox_summary"] == {
        "parser_section_count": 97,
        "sections_with_matched_raw_fields": 3,
    }
    assert rendered[0]["parsed"]["character_count"] == 2
    assert rendered[0]["parsed"]["characters"][0]["name"] == "Alpha Archer"
    assert rendered[0]["parsed"]["characters"][0]["current_activity"] == (
        "Fighting: Green Mushroom"
    )
    assert rendered[0]["toolbox_sections"]["character"]["source_path"] == (
        "character.ts"
    )
    assert (
        "CharacterClass"
        in rendered[0]["toolbox_sections"]["character"]["matched_raw_fields"]
    )
    clean_character = rendered[0]["clean_reference"]["characters"][0]
    assert clean_character["class"] == "Bowman"
    assert clean_character["raw_class"] == 20

    html = html_path.read_text()
    assert "HA Idleon Parsed Data Debug" in html
    assert "Debug Metadata" in html
    assert "Alpha Archer" in html
    assert "Raw Class" in html
    assert "IdleonToolbox Parser Sections" in html
