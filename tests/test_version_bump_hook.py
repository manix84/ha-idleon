"""Tests for the smart version bump hook."""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]


def _load_hook() -> ModuleType:
    """Load the version bump hook module."""
    path = ROOT / "scripts/version-bump-hook"
    loader = SourceFileLoader("version_bump_hook", str(path))
    spec = importlib.util.spec_from_file_location(
        "version_bump_hook",
        path,
        loader=loader,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bump_version_patch_and_minor() -> None:
    """Test semantic version bumping."""
    hook = _load_hook()

    assert hook._bump_version("0.1.0", "patch") == "0.1.1"
    assert hook._bump_version("0.1.0", "minor") == "0.2.0"


def test_select_bump_skips_docs_only_changes() -> None:
    """Test docs-only changes do not bump the version."""
    hook = _load_hook()
    hook._version_already_staged = lambda: False

    assert hook._select_bump((Path("README.md"),), "auto") == "skip"
    assert hook._select_bump((Path("docs/manual-testing.md"),), "auto") == "skip"


def test_select_bump_uses_patch_for_internal_changes() -> None:
    """Test internal implementation changes bump patch."""
    hook = _load_hook()
    hook._version_already_staged = lambda: False

    assert (
        hook._select_bump(
            (Path("custom_components/idleon/idleon_data/parser.py"),),
            "auto",
        )
        == "patch"
    )


def test_select_bump_uses_minor_for_public_surface_changes() -> None:
    """Test public integration surface changes bump minor."""
    hook = _load_hook()
    hook._version_already_staged = lambda: False

    assert (
        hook._select_bump((Path("custom_components/idleon/sensor.py"),), "auto")
        == "minor"
    )
    assert (
        hook._select_bump(
            (Path("custom_components/idleon/translations/en.json"),),
            "auto",
        )
        == "minor"
    )


def test_select_bump_allows_docs_in_version_files() -> None:
    """Test docs changes in version-bearing files can still bump."""
    hook = _load_hook()
    hook._version_already_staged = lambda: False

    assert (
        hook._select_bump(
            (
                Path(".pre-commit-config.yaml"),
                Path("README.md"),
            ),
            "auto",
        )
        == "patch"
    )


def test_select_bump_skips_when_version_already_staged() -> None:
    """Test staged version bumps are not bumped again."""
    hook = _load_hook()
    hook._version_already_staged = lambda: True

    assert (
        hook._select_bump(
            (Path("custom_components/idleon/sensor.py"),),
            "auto",
        )
        == "skip"
    )


def test_select_bump_respects_override() -> None:
    """Test explicit hook override wins."""
    hook = _load_hook()

    assert hook._select_bump((Path("README.md"),), "patch") == "patch"
    assert (
        hook._select_bump((Path("custom_components/idleon/sensor.py"),), "skip")
        == "skip"
    )


def test_release_notes_use_commit_subject(tmp_path: Path) -> None:
    """Test generated release notes use the commit subject."""
    hook = _load_hook()
    message_path = tmp_path / "COMMIT_EDITMSG"
    message_path.write_text("Add better character sensors\n\n# comment\n")

    assert hook._release_notes_from_commit_message(message_path) == (
        "Add better character sensors.",
    )


def test_release_notes_strip_conventional_commit_prefix(tmp_path: Path) -> None:
    """Test conventional commit subjects become readable release notes."""
    hook = _load_hook()
    message_path = tmp_path / "COMMIT_EDITMSG"
    message_path.write_text("fix(parser): handle wrapped saves\n")

    assert hook._release_notes_from_commit_message(message_path) == (
        "Handle wrapped saves.",
    )


def test_release_notes_use_commit_body_bullets(tmp_path: Path) -> None:
    """Test explicit commit body bullets become release notes."""
    hook = _load_hook()
    message_path = tmp_path / "COMMIT_EDITMSG"
    message_path.write_text(
        "Improve parser\n\n"
        "- add skill summaries\n"
        "* expose equipment counts.\n"
        "# ignored comment\n"
    )

    assert hook._release_notes_from_commit_message(message_path) == (
        "Add skill summaries.",
        "Expose equipment counts.",
    )


def test_update_whatsnew_uses_release_notes(tmp_path: Path) -> None:
    """Test What's New entries are created from release notes."""
    hook = _load_hook()
    hook.ROOT = tmp_path
    whatsnew = tmp_path / "WHATSNEW.md"
    whatsnew.write_text("# What's New\n\n## 🚀 0.1.0\n\n- Initial release.\n")

    hook._update_whatsnew("0.1.1", ("Add useful release notes.",))

    assert whatsnew.read_text().startswith(
        "# What's New\n\n## 🚀 0.1.1\n\n- Add useful release notes.\n\n## 🚀 0.1.0"
    )
