"""Tests for security module."""

from unittest.mock import MagicMock

from second_brain_kit.security import is_owner, is_owner_interaction


class TestIsOwner:
    def test_owner_returns_true(self) -> None:
        msg = MagicMock()
        msg.author.id = 12345
        assert is_owner(msg, 12345) is True

    def test_non_owner_returns_false(self) -> None:
        msg = MagicMock()
        msg.author.id = 99999
        assert is_owner(msg, 12345) is False


class TestIsOwnerInteraction:
    def test_owner_returns_true(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        assert is_owner_interaction(interaction, 12345) is True

    def test_non_owner_returns_false(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 99999
        assert is_owner_interaction(interaction, 12345) is False
