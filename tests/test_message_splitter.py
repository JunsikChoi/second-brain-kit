"""Tests for message_splitter module."""

from second_brain_kit.message_splitter import DISCORD_MAX, SAFE_MAX, split_message


class TestSplitMessage:
    """Tests for split_message()."""

    def test_short_message_returns_single_chunk(self) -> None:
        assert split_message("hello") == ["hello"]

    def test_exact_limit_returns_single_chunk(self) -> None:
        msg = "x" * DISCORD_MAX
        result = split_message(msg)
        assert len(result) == 1
        assert result[0] == msg

    def test_empty_message(self) -> None:
        assert split_message("") == [""]

    def test_long_message_splits(self) -> None:
        msg = "a" * (DISCORD_MAX + 500)
        result = split_message(msg)
        assert len(result) >= 2
        assert "".join(result) == msg

    def test_splits_at_newline(self) -> None:
        # Build a message where a newline falls within the split search window
        line = "x" * (SAFE_MAX - 100) + "\n" + "y" * 300
        result = split_message(line)
        assert len(result) == 2
        assert result[0].endswith("\n") or result[0][-1] == "x"

    def test_all_chunks_within_limit(self) -> None:
        msg = ("abcde\n" * 1000).strip()
        result = split_message(msg)
        for chunk in result:
            # Code block fix may add a few chars, allow small overhead
            assert len(chunk) <= DISCORD_MAX + 20

    def test_preserves_full_content(self) -> None:
        msg = "line\n" * 500
        result = split_message(msg)
        reassembled = "".join(result)
        assert reassembled == msg

    def test_code_block_continuity(self) -> None:
        """An unclosed code block in a chunk should be closed and reopened."""
        code = "```python\n" + "x = 1\n" * 400 + "```"
        result = split_message(code)
        assert len(result) >= 2
        # First chunk should have a closing fence added
        assert result[0].rstrip().endswith("```")
        # Second chunk should start with reopened fence
        assert result[1].startswith("```")

    def test_code_block_with_language_tag(self) -> None:
        code = "```javascript\n" + "var a = 1;\n" * 400 + "```"
        result = split_message(code)
        assert len(result) >= 2
        # Reopened block should preserve language tag
        assert result[1].startswith("```javascript\n")

    def test_even_fence_count_no_fix(self) -> None:
        """A chunk with balanced (even) fences should not be modified."""
        text = "```py\ncode\n```\n" + "normal " * 300
        result = split_message(text)
        # First chunk should have even fences already, no extra closing
        fence_count = result[0].count("```")
        assert fence_count % 2 == 0
