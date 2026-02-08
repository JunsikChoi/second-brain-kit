"""Vault manager: read, write, list, and search Obsidian-compatible markdown notes."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from .claude_runner import ClaudeRunner

log = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)", re.DOTALL)


@dataclass
class Note:
    """A single markdown note with YAML frontmatter."""

    path: Path
    """Absolute path to the .md file."""

    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def tags(self) -> list[str]:
        """Return tags from frontmatter (normalised to list[str])."""
        raw = self.frontmatter.get("tags", [])
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        if isinstance(raw, list):
            return [str(t) for t in raw]
        return []

    @property
    def title(self) -> str:
        """Note title: frontmatter 'title' or filename stem."""
        return str(self.frontmatter.get("title", self.path.stem))

    @property
    def rel_path(self) -> str:
        """Filename for display (stem.md)."""
        return self.path.name

    def to_markdown(self) -> str:
        """Serialise back to a markdown string with YAML frontmatter."""
        if self.frontmatter:
            fm = yaml.dump(
                self.frontmatter,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            ).rstrip("\n")
            return f"---\n{fm}\n---\n{self.body}"
        return self.body


def parse_note(path: Path) -> Note:
    """Parse a markdown file into a Note, separating frontmatter from body."""
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            fm = {}
        return Note(path=path, frontmatter=fm, body=m.group(2))
    return Note(path=path, frontmatter={}, body=text)


class VaultManager:
    """Manages an Obsidian-compatible vault (directory of markdown files)."""

    def __init__(self, vault_path: Path) -> None:
        self.root = vault_path.resolve()
        if not self.root.is_dir():
            raise ValueError(f"Vault path does not exist: {self.root}")

    # ── Read ────────────────────────────────────────────────────────

    def read_note(self, rel_path: str | Path) -> Note:
        """Read and parse a single note by its path relative to vault root."""
        full = self.root / rel_path
        if not full.is_file():
            raise FileNotFoundError(f"Note not found: {full}")
        if not full.suffix == ".md":
            raise ValueError(f"Not a markdown file: {full}")
        return parse_note(full)

    # ── Write ───────────────────────────────────────────────────────

    def write_note(self, note: Note) -> Path:
        """Write a Note to disk. Creates parent directories as needed."""
        note.path.parent.mkdir(parents=True, exist_ok=True)
        note.path.write_text(note.to_markdown(), encoding="utf-8")
        return note.path

    def create_note(
        self,
        rel_path: str | Path,
        body: str = "",
        frontmatter: dict[str, Any] | None = None,
        *,
        overwrite: bool = False,
    ) -> Note:
        """Create a new note under the vault root."""
        full = self.root / rel_path
        if full.exists() and not overwrite:
            raise FileExistsError(f"Note already exists: {full}")
        note = Note(path=full, frontmatter=frontmatter or {}, body=body)
        self.write_note(note)
        return note

    # ── List ────────────────────────────────────────────────────────

    def list_notes(self, folder: str | Path | None = None) -> list[Note]:
        """List all .md notes under *folder* (default: entire vault)."""
        base = self.root / folder if folder else self.root
        if not base.is_dir():
            return []
        return [parse_note(p) for p in sorted(base.rglob("*.md"))]

    # ── Search ──────────────────────────────────────────────────────

    def search(self, query: str, *, folder: str | Path | None = None) -> list[Note]:
        """Full-text search: matches against filename, tags, and body."""
        q = query.lower()
        results: list[Note] = []
        for note in self.list_notes(folder):
            if q in note.path.stem.lower():
                results.append(note)
            elif q in " ".join(note.tags).lower():
                results.append(note)
            elif q in note.body.lower():
                results.append(note)
        return results

    def find_by_tags(self, tags: list[str]) -> list[Note]:
        """Return notes whose frontmatter tags include ALL of the given tags."""
        target = {t.lower().lstrip("#") for t in tags}
        results: list[Note] = []
        for note in self.list_notes():
            note_tags = {t.lower().lstrip("#") for t in note.tags}
            if target <= note_tags:
                results.append(note)
        return results

    def all_tags(self) -> dict[str, int]:
        """Return a tag → count mapping across all notes."""
        counts: dict[str, int] = {}
        for note in self.list_notes():
            for tag in note.tags:
                t = tag.lower().lstrip("#")
                counts[t] = counts.get(t, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    # ── Auto-tagging ────────────────────────────────────────────────

    async def auto_tag(self, note: Note, runner: ClaudeRunner) -> list[str]:
        """Ask Claude to suggest tags for a note based on its content.

        Returns a list of suggested tag strings (lowercase, no '#').
        The note is NOT modified; caller decides whether to apply.
        """
        existing = self.all_tags()
        existing_sample = ", ".join(list(existing.keys())[:30])

        prompt = (
            "Read the following markdown note and suggest 2-5 tags for it. "
            "Tags should be lowercase, hyphenated (e.g. 'machine-learning'), "
            "and match the topic/domain of the note.\n\n"
            f"Existing tags in this vault: {existing_sample}\n"
            "Prefer reusing existing tags when appropriate.\n\n"
            "Return ONLY a JSON array of strings, e.g. [\"python\", \"web-scraping\"]. "
            "No explanation.\n\n"
            f"---\nTitle: {note.title}\n\n{note.body[:2000]}"
        )

        response = await runner.run(prompt, model="haiku")
        if response.is_error:
            log.warning("Auto-tag failed: %s", response.text[:200])
            return []

        try:
            tags = json.loads(response.text.strip())
            if isinstance(tags, list):
                return [str(t).lower().strip().lstrip("#") for t in tags if t]
        except (json.JSONDecodeError, TypeError):
            # Try to extract JSON array from response text
            m = re.search(r"\[.*?\]", response.text, re.DOTALL)
            if m:
                try:
                    tags = json.loads(m.group())
                    return [str(t).lower().strip().lstrip("#") for t in tags if t]
                except (json.JSONDecodeError, TypeError):
                    pass
            log.warning("Auto-tag: could not parse response: %s", response.text[:200])
        return []
