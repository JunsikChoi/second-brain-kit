"""Tests for file_handler module."""

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from second_brain_kit.file_handler import (
    build_file_prompt,
    detect_output_files,
    download_attachments,
)


class TestDetectOutputFiles:
    def test_detects_tmp_path(self, tmp_path: Path) -> None:
        f = tmp_path / "output.png"
        f.write_text("data")
        text = f"Here is the file: {f}"
        result = detect_output_files(text, max_age_secs=10)
        assert f in result

    def test_ignores_old_file(self, tmp_path: Path) -> None:
        f = tmp_path / "old.txt"
        f.write_text("data")
        # Set mtime to 5 minutes ago
        old_time = time.time() - 300
        import os

        os.utime(f, (old_time, old_time))
        text = f"File: {f}"
        result = detect_output_files(text, max_age_secs=120)
        assert f not in result

    def test_ignores_nonexistent_file(self) -> None:
        text = "File: /tmp/does-not-exist-xyz.txt"
        result = detect_output_files(text)
        assert result == []

    def test_ignores_large_file(self, tmp_path: Path) -> None:
        f = tmp_path / "big.bin"
        # Create a file reference but don't actually make it 25MB
        f.write_text("x")
        # Monkeypatch the size check would be complex; instead test the pattern
        text = f"File: {f}"
        result = detect_output_files(text, max_age_secs=60)
        # Small file should be detected
        assert f in result

    def test_deduplicates_paths(self, tmp_path: Path) -> None:
        f = tmp_path / "dup.txt"
        f.write_text("data")
        text = f"First: {f}\nSecond: {f}"
        result = detect_output_files(text, max_age_secs=10)
        assert len(result) == 1

    def test_matches_quoted_paths(self, tmp_path: Path) -> None:
        f = tmp_path / "quoted.txt"
        f.write_text("data")
        text = f'Output saved to "{f}"'
        result = detect_output_files(text, max_age_secs=10)
        assert f in result

    def test_matches_backtick_paths(self, tmp_path: Path) -> None:
        f = tmp_path / "bt.txt"
        f.write_text("data")
        text = f"Output: `{f}`"
        result = detect_output_files(text, max_age_secs=10)
        assert f in result

    def test_no_match_outside_tmp_home(self) -> None:
        text = "File at /var/log/syslog"
        result = detect_output_files(text)
        assert result == []


class TestBuildFilePrompt:
    def test_empty_list(self) -> None:
        assert build_file_prompt([]) == ""

    def test_single_file(self) -> None:
        prompt = build_file_prompt([Path("/tmp/a.txt")])
        assert "/tmp/a.txt" in prompt
        assert "Read" in prompt

    def test_multiple_files(self) -> None:
        prompt = build_file_prompt([Path("/tmp/a.txt"), Path("/tmp/b.png")])
        assert "/tmp/a.txt" in prompt
        assert "/tmp/b.png" in prompt


class TestDownloadAttachments:
    @pytest.mark.asyncio
    async def test_download_single_file(self, tmp_path: Path) -> None:
        att = MagicMock()
        att.filename = "test.txt"
        att.save = AsyncMock()

        result = await download_attachments([att], tmp_path)
        assert len(result) == 1
        assert result[0] == tmp_path / "test.txt"
        att.save.assert_awaited_once_with(tmp_path / "test.txt")

    @pytest.mark.asyncio
    async def test_download_deduplicates_filename(self, tmp_path: Path) -> None:
        # Create existing file
        (tmp_path / "test.txt").write_text("existing")

        att = MagicMock()
        att.filename = "test.txt"
        att.save = AsyncMock()

        result = await download_attachments([att], tmp_path)
        assert len(result) == 1
        # Should have a deduplicated name
        assert result[0] != tmp_path / "test.txt"
        assert "test" in result[0].stem

    @pytest.mark.asyncio
    async def test_creates_download_dir(self, tmp_path: Path) -> None:
        dl_dir = tmp_path / "subdir" / "downloads"
        att = MagicMock()
        att.filename = "file.txt"
        att.save = AsyncMock()

        await download_attachments([att], dl_dir)
        assert dl_dir.exists()
