"""Tests for the websiteData splitting helper."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_website_data_splitter_writes_top_level_files(tmp_path: Path) -> None:
    """Test websiteData is split into deterministic top-level files."""
    source = tmp_path / "websiteData.json"
    output_dir = tmp_path / "websiteData"
    stale_file = output_dir / "stale.json"
    output_dir.mkdir()
    stale_file.write_text("{}\n")
    source.write_text(
        json.dumps(
            {
                "classes": ["0", "Beginner", "Journeyman"],
                "mapNames": {"0": "Blunder_Hills"},
                "weird key!": {"value": 1},
            }
        )
    )

    result = subprocess.run(
        [
            str(ROOT / "scripts/split-website-data"),
            "--source",
            str(source),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Wrote 3 websiteData files" in result.stdout
    assert json.loads((output_dir / "classes.json").read_text()) == [
        "0",
        "Beginner",
        "Journeyman",
    ]
    assert json.loads((output_dir / "mapNames.json").read_text()) == {
        "0": "Blunder_Hills"
    }
    assert json.loads((output_dir / "weird-key.json").read_text()) == {"value": 1}
    assert not stale_file.exists()
