"""Tests for config module."""

import pytest

from second_brain_kit.config import Config


class TestConfig:
    def test_from_env_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        vault = tmp_path / "vault"  # type: ignore[operator]
        vault.mkdir()

        monkeypatch.setenv("DISCORD_TOKEN", "test-token")
        monkeypatch.setenv("OWNER_ID", "12345")
        monkeypatch.setenv("VAULT_PATH", str(vault))
        monkeypatch.setenv("CLAUDE_MODEL", "opus")
        monkeypatch.setenv("MAX_BUDGET_USD", "2.50")
        monkeypatch.setenv("ALLOWED_TOOLS", "Read,Write,Bash")
        monkeypatch.setenv("DOWNLOAD_DIR", str(tmp_path / "dl"))  # type: ignore[operator]

        cfg = Config.from_env()
        assert cfg.discord_token == "test-token"
        assert cfg.owner_id == 12345
        assert cfg.vault_path == vault
        assert cfg.claude_model == "opus"
        assert cfg.max_budget_usd == 2.50
        assert cfg.allowed_tools == ["Read", "Write", "Bash"]

    def test_missing_discord_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DISCORD_TOKEN", raising=False)
        monkeypatch.setenv("OWNER_ID", "12345")
        monkeypatch.setenv("VAULT_PATH", "/tmp")
        with pytest.raises(ValueError, match="DISCORD_TOKEN"):
            Config.from_env()

    def test_missing_owner_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.delenv("OWNER_ID", raising=False)
        monkeypatch.setenv("VAULT_PATH", "/tmp")
        with pytest.raises(ValueError, match="OWNER_ID"):
            Config.from_env()

    def test_missing_vault_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("OWNER_ID", "12345")
        monkeypatch.delenv("VAULT_PATH", raising=False)
        with pytest.raises(ValueError, match="VAULT_PATH"):
            Config.from_env()

    def test_invalid_vault_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("OWNER_ID", "12345")
        monkeypatch.setenv("VAULT_PATH", "/nonexistent/path/xyz")
        with pytest.raises(ValueError, match="does not exist"):
            Config.from_env()

    def test_defaults(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        vault = tmp_path / "vault"  # type: ignore[operator]
        vault.mkdir()

        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("OWNER_ID", "12345")
        monkeypatch.setenv("VAULT_PATH", str(vault))
        monkeypatch.delenv("CLAUDE_MODEL", raising=False)
        monkeypatch.delenv("MAX_BUDGET_USD", raising=False)
        monkeypatch.delenv("ALLOWED_TOOLS", raising=False)
        monkeypatch.delenv("DOWNLOAD_DIR", raising=False)

        cfg = Config.from_env()
        assert cfg.claude_model == "sonnet"
        assert cfg.max_budget_usd == 1.00
        assert cfg.allowed_tools == []

    def test_empty_allowed_tools(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        vault = tmp_path / "vault"  # type: ignore[operator]
        vault.mkdir()

        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("OWNER_ID", "12345")
        monkeypatch.setenv("VAULT_PATH", str(vault))
        monkeypatch.setenv("ALLOWED_TOOLS", "")

        cfg = Config.from_env()
        assert cfg.allowed_tools == []
