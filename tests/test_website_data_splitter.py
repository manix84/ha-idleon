"""Tests for the websiteData splitting helper."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from custom_components.idleon.idleon_data.website_data import load_website_data_part

ROOT = Path(__file__).parents[1]


def test_website_data_splitter_writes_top_level_files(tmp_path: Path) -> None:
    """Test websiteData is split into deterministic top-level files."""
    source = tmp_path / "websiteData.json"
    output_dir = tmp_path / "websiteData"
    stale_file = output_dir / "stale.json"
    stale_type_file = output_dir / "stale.d.ts"
    output_dir.mkdir()
    stale_file.write_text("{}\n")
    stale_type_file.write_text("export type Stale = unknown;\n")
    source.write_text(
        json.dumps(
            {
                "classes": ["0", "Beginner", "Journeyman"],
                "mapNames": {"0": "Blunder_Hills"},
                "weird key!": {"value": 1},
            }
        )
    )
    types_source = tmp_path / "websiteData.d.json.ts"
    types_source.write_text(
        """
// Auto-generated
// Do not edit manually

declare module "@website-data" {
  export const classes: string[];
  export const mapNames: Record<string, string>;
  export const missingFromJson: number[];
  export const weird key!: { value: number };
}
"""
    )

    result = subprocess.run(
        [
            str(ROOT / "scripts/split-website-data"),
            "--source",
            str(source),
            "--output-dir",
            str(output_dir),
            "--types-source",
            str(types_source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Wrote 6 websiteData files" in result.stdout
    assert json.loads((output_dir / "classes.json").read_text()) == [
        "0",
        "Beginner",
        "Journeyman",
    ]
    assert json.loads((output_dir / "mapNames.json").read_text()) == {
        "0": "Blunder_Hills"
    }
    assert json.loads((output_dir / "weird-key.json").read_text()) == {"value": 1}
    assert (
        "export type WebsiteDataClasses = string[];"
        in (output_dir / "classes.d.ts").read_text()
    )
    assert (
        "export type WebsiteDataMapNames = Record<string, string>;"
        in (output_dir / "mapNames.d.ts").read_text()
    )

    manifest = json.loads((output_dir / "_manifest.json").read_text())
    assert manifest["files"]["classes"] == {
        "json": "classes.json",
        "type": "classes.d.ts",
    }
    assert manifest["files"]["weird key!"] == {
        "json": "weird-key.json",
        "type": None,
    }
    assert load_website_data_part("classes", base_path=output_dir) == [
        "0",
        "Beginner",
        "Journeyman",
    ]
    assert not stale_file.exists()
    assert not stale_type_file.exists()
