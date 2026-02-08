"""Tests for vault module."""

from pathlib import Path

import pytest

from second_brain_kit.vault import Note, VaultManager, parse_note

# ── Helpers ─────────────────────────────────────────────────────────


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


SAMPLE_NOTE = """\
---
title: Test Note
tags:
  - python
  - ai
type: til
---
# Hello

Body text here.
"""

NO_FRONTMATTER = """\
# Just a heading

Some plain markdown.
"""


# ── Note dataclass ──────────────────────────────────────────────────


class TestNote:
    def test_tags_from_list(self) -> None:
        note = Note(path=Path("x.md"), frontmatter={"tags": ["a", "b"]})
        assert note.tags == ["a", "b"]

    def test_tags_from_csv_string(self) -> None:
        note = Note(path=Path("x.md"), frontmatter={"tags": "a, b, c"})
        assert note.tags == ["a", "b", "c"]

    def test_tags_missing(self) -> None:
        note = Note(path=Path("x.md"))
        assert note.tags == []

    def test_title_from_frontmatter(self) -> None:
        note = Note(path=Path("x.md"), frontmatter={"title": "My Title"})
        assert note.title == "My Title"

    def test_title_fallback_to_stem(self) -> None:
        note = Note(path=Path("my-note.md"))
        assert note.title == "my-note"

    def test_to_markdown_with_frontmatter(self) -> None:
        note = Note(
            path=Path("x.md"),
            frontmatter={"title": "T", "tags": ["a"]},
            body="Body\n",
        )
        md = note.to_markdown()
        assert md.startswith("---\n")
        assert "title: T" in md
        assert "Body\n" in md

    def test_to_markdown_no_frontmatter(self) -> None:
        note = Note(path=Path("x.md"), body="Just text")
        assert note.to_markdown() == "Just text"


# ── parse_note ──────────────────────────────────────────────────────


class TestParseNote:
    def test_with_frontmatter(self, tmp_path: Path) -> None:
        p = _write(tmp_path / "note.md", SAMPLE_NOTE)
        note = parse_note(p)
        assert note.frontmatter["title"] == "Test Note"
        assert note.tags == ["python", "ai"]
        assert "Body text here." in note.body

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        p = _write(tmp_path / "plain.md", NO_FRONTMATTER)
        note = parse_note(p)
        assert note.frontmatter == {}
        assert "Just a heading" in note.body

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        bad = "---\n[invalid: yaml: ::\n---\nBody\n"
        p = _write(tmp_path / "bad.md", bad)
        note = parse_note(p)
        assert note.frontmatter == {}
        assert "Body" in note.body


# ── VaultManager ────────────────────────────────────────────────────


@pytest.fixture()
def vault(tmp_path: Path) -> VaultManager:
    _write(tmp_path / "note1.md", SAMPLE_NOTE)
    _write(
        tmp_path / "sub" / "note2.md",
        "---\ntags:\n  - rust\n---\nRust note body\n",
    )
    _write(tmp_path / "plain.md", NO_FRONTMATTER)
    return VaultManager(tmp_path)


class TestVaultManager:
    def test_init_bad_path(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            VaultManager(Path("/nonexistent/vault"))

    # ── read ────────────────────────────────────────────────────

    def test_read_note(self, vault: VaultManager) -> None:
        note = vault.read_note("note1.md")
        assert note.frontmatter["title"] == "Test Note"

    def test_read_note_not_found(self, vault: VaultManager) -> None:
        with pytest.raises(FileNotFoundError):
            vault.read_note("missing.md")

    def test_read_note_not_markdown(self, vault: VaultManager, tmp_path: Path) -> None:
        _write(tmp_path / "data.json", "{}")
        with pytest.raises(ValueError, match="Not a markdown"):
            vault.read_note("data.json")

    # ── write / create ──────────────────────────────────────────

    def test_create_note(self, vault: VaultManager) -> None:
        note = vault.create_note(
            "new/created.md",
            body="New content\n",
            frontmatter={"tags": ["test"]},
        )
        assert note.path.is_file()
        reread = vault.read_note("new/created.md")
        assert reread.tags == ["test"]
        assert "New content" in reread.body

    def test_create_note_no_overwrite(self, vault: VaultManager) -> None:
        with pytest.raises(FileExistsError):
            vault.create_note("note1.md", body="overwrite attempt")

    def test_create_note_overwrite(self, vault: VaultManager) -> None:
        vault.create_note("note1.md", body="replaced", overwrite=True)
        reread = vault.read_note("note1.md")
        assert reread.body == "replaced"

    def test_write_note_roundtrip(self, vault: VaultManager) -> None:
        note = vault.read_note("note1.md")
        note.frontmatter["new_key"] = "hello"
        vault.write_note(note)
        reread = vault.read_note("note1.md")
        assert reread.frontmatter["new_key"] == "hello"

    # ── list ────────────────────────────────────────────────────

    def test_list_all(self, vault: VaultManager) -> None:
        notes = vault.list_notes()
        names = {n.path.name for n in notes}
        assert names == {"note1.md", "note2.md", "plain.md"}

    def test_list_subfolder(self, vault: VaultManager) -> None:
        notes = vault.list_notes("sub")
        assert len(notes) == 1
        assert notes[0].path.name == "note2.md"

    def test_list_missing_folder(self, vault: VaultManager) -> None:
        assert vault.list_notes("nonexistent") == []

    # ── search ──────────────────────────────────────────────────

    def test_search_by_filename(self, vault: VaultManager) -> None:
        results = vault.search("note1")
        assert any(n.path.name == "note1.md" for n in results)

    def test_search_by_body(self, vault: VaultManager) -> None:
        results = vault.search("Rust note")
        assert any("Rust" in n.body for n in results)

    def test_search_by_tag(self, vault: VaultManager) -> None:
        results = vault.search("python")
        assert any("python" in n.tags for n in results)

    def test_search_no_match(self, vault: VaultManager) -> None:
        assert vault.search("zzzznotfound") == []

    def test_search_case_insensitive(self, vault: VaultManager) -> None:
        results = vault.search("RUST")
        assert len(results) >= 1

    # ── find_by_tags ────────────────────────────────────────────

    def test_find_by_single_tag(self, vault: VaultManager) -> None:
        results = vault.find_by_tags(["python"])
        assert len(results) == 1
        assert results[0].path.name == "note1.md"

    def test_find_by_multiple_tags(self, vault: VaultManager) -> None:
        results = vault.find_by_tags(["python", "ai"])
        assert len(results) == 1

    def test_find_by_tags_strips_hash(self, vault: VaultManager) -> None:
        results = vault.find_by_tags(["#rust"])
        assert len(results) == 1

    def test_find_by_tags_no_match(self, vault: VaultManager) -> None:
        assert vault.find_by_tags(["nonexistent"]) == []

    # ── all_tags ────────────────────────────────────────────────

    def test_all_tags(self, vault: VaultManager) -> None:
        tags = vault.all_tags()
        assert "python" in tags
        assert "ai" in tags
        assert "rust" in tags
        assert tags["python"] == 1

    def test_all_tags_empty_vault(self, tmp_path: Path) -> None:
        _write(tmp_path / "empty.md", "No frontmatter here")
        v = VaultManager(tmp_path)
        assert v.all_tags() == {}


# ── auto_tag ────────────────────────────────────────────────────────


class TestAutoTag:
    @pytest.fixture()
    def vault_for_tag(self, tmp_path: Path) -> VaultManager:
        _write(
            tmp_path / "existing.md",
            "---\ntags:\n  - python\n  - web\n---\nSome content\n",
        )
        return VaultManager(tmp_path)

    @pytest.mark.asyncio()
    async def test_auto_tag_success(self, vault_for_tag: VaultManager) -> None:
        from unittest.mock import AsyncMock

        from second_brain_kit.claude_runner import ClaudeResponse

        runner = AsyncMock()
        runner.run.return_value = ClaudeResponse(
            text='["machine-learning", "data-science"]',
            session_id="",
            cost_usd=0.001,
            duration_secs=1.0,
        )

        note = Note(path=vault_for_tag.root / "test.md", body="ML training pipeline")
        tags = await vault_for_tag.auto_tag(note, runner)
        assert tags == ["machine-learning", "data-science"]
        runner.run.assert_called_once()

    @pytest.mark.asyncio()
    async def test_auto_tag_error_response(self, vault_for_tag: VaultManager) -> None:
        from unittest.mock import AsyncMock

        from second_brain_kit.claude_runner import ClaudeResponse

        runner = AsyncMock()
        runner.run.return_value = ClaudeResponse(
            text="error", session_id="", cost_usd=0.0, duration_secs=0.0, is_error=True
        )

        note = Note(path=vault_for_tag.root / "test.md", body="content")
        tags = await vault_for_tag.auto_tag(note, runner)
        assert tags == []

    @pytest.mark.asyncio()
    async def test_auto_tag_json_in_prose(self, vault_for_tag: VaultManager) -> None:
        from unittest.mock import AsyncMock

        from second_brain_kit.claude_runner import ClaudeResponse

        runner = AsyncMock()
        runner.run.return_value = ClaudeResponse(
            text='Here are tags: ["python", "api"]',
            session_id="",
            cost_usd=0.001,
            duration_secs=1.0,
        )

        note = Note(path=vault_for_tag.root / "test.md", body="API development")
        tags = await vault_for_tag.auto_tag(note, runner)
        assert tags == ["python", "api"]

    @pytest.mark.asyncio()
    async def test_auto_tag_unparseable(self, vault_for_tag: VaultManager) -> None:
        from unittest.mock import AsyncMock

        from second_brain_kit.claude_runner import ClaudeResponse

        runner = AsyncMock()
        runner.run.return_value = ClaudeResponse(
            text="I cannot parse this as JSON",
            session_id="",
            cost_usd=0.001,
            duration_secs=1.0,
        )

        note = Note(path=vault_for_tag.root / "test.md", body="content")
        tags = await vault_for_tag.auto_tag(note, runner)
        assert tags == []
