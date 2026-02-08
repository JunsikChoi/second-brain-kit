"""Tests for MCP registry and manager."""

import json
from pathlib import Path

import pytest

from second_brain_kit.mcp_registry import REGISTRY, MCPManager, MCPServerDef

# ── Registry ───────────────────────────────────────────────────────


class TestRegistry:
    def test_has_three_servers(self) -> None:
        assert len(REGISTRY) == 3

    def test_google_calendar(self) -> None:
        gcal = REGISTRY["google-calendar"]
        assert gcal.display_name == "Google Calendar"
        assert gcal.server_type == "stdio"
        assert gcal.command == "npx"
        assert "GOOGLE_OAUTH_CREDENTIALS" in gcal.env_vars

    def test_todoist(self) -> None:
        todoist = REGISTRY["todoist"]
        assert todoist.server_type == "http"
        assert todoist.url == "https://ai.todoist.net/mcp"
        assert not todoist.env_vars

    def test_rss_reader(self) -> None:
        rss = REGISTRY["rss-reader"]
        assert rss.server_type == "stdio"
        assert rss.command == "npx"
        assert not rss.env_vars


# ── MCPServerDef ───────────────────────────────────────────────────


class TestMCPServerDef:
    def test_to_claude_config_stdio(self) -> None:
        server = MCPServerDef(
            name="test",
            display_name="Test",
            description="A test server",
            server_type="stdio",
            command="npx",
            args=["-y", "test-mcp"],
        )
        config = server.to_claude_config()
        assert config == {"type": "stdio", "command": "npx", "args": ["-y", "test-mcp"]}

    def test_to_claude_config_stdio_with_env(self) -> None:
        server = MCPServerDef(
            name="test",
            display_name="Test",
            description="A test server",
            server_type="stdio",
            command="npx",
            args=["-y", "test-mcp"],
            env_vars={"API_KEY": "hint"},
        )
        config = server.to_claude_config({"API_KEY": "abc123"})
        assert config["env"] == {"API_KEY": "abc123"}

    def test_to_claude_config_http(self) -> None:
        server = MCPServerDef(
            name="test",
            display_name="Test",
            description="A test server",
            server_type="http",
            url="https://example.com/mcp",
        )
        config = server.to_claude_config()
        assert config == {"type": "http", "url": "https://example.com/mcp"}

    def test_to_claude_config_args_not_shared(self) -> None:
        """Ensure args list is copied, not shared."""
        server = MCPServerDef(
            name="test",
            display_name="Test",
            description="desc",
            server_type="stdio",
            command="npx",
            args=["-y", "pkg"],
        )
        config = server.to_claude_config()
        config["args"].append("extra")
        assert server.args == ["-y", "pkg"]


# ── MCPManager ─────────────────────────────────────────────────────


class TestMCPManager:
    @pytest.fixture()
    def config_path(self, tmp_path: Path) -> Path:
        return tmp_path / ".claude.json"

    @pytest.fixture()
    def manager(self, config_path: Path) -> MCPManager:
        return MCPManager(claude_config_path=config_path)

    # ── list_registered ────────────────────────────────────────────

    def test_list_registered(self, manager: MCPManager) -> None:
        registered = manager.list_registered()
        assert len(registered) == 3
        names = {s.name for s in registered}
        assert names == {"google-calendar", "todoist", "rss-reader"}

    # ── list_installed ─────────────────────────────────────────────

    def test_list_installed_no_file(self, manager: MCPManager) -> None:
        assert manager.list_installed() == {}

    def test_list_installed_empty_file(self, config_path: Path, manager: MCPManager) -> None:
        config_path.write_text("{}", encoding="utf-8")
        assert manager.list_installed() == {}

    def test_list_installed_with_servers(
        self, config_path: Path, manager: MCPManager
    ) -> None:
        config_path.write_text(
            json.dumps(
                {"mcpServers": {"test": {"type": "stdio", "command": "echo", "args": []}}}
            ),
            encoding="utf-8",
        )
        installed = manager.list_installed()
        assert "test" in installed

    # ── is_installed ───────────────────────────────────────────────

    def test_is_installed_false(self, manager: MCPManager) -> None:
        assert not manager.is_installed("todoist")

    def test_is_installed_true(self, config_path: Path, manager: MCPManager) -> None:
        config_path.write_text(
            json.dumps({"mcpServers": {"todoist": {"type": "http", "url": "x"}}}),
            encoding="utf-8",
        )
        assert manager.is_installed("todoist")

    # ── install ────────────────────────────────────────────────────

    def test_install_creates_file(self, config_path: Path, manager: MCPManager) -> None:
        manager.install("todoist")
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["mcpServers"]["todoist"]["type"] == "http"

    def test_install_preserves_existing_data(
        self, config_path: Path, manager: MCPManager
    ) -> None:
        config_path.write_text(
            json.dumps({"someKey": "someValue", "mcpServers": {}}),
            encoding="utf-8",
        )
        manager.install("rss-reader")
        data = json.loads(config_path.read_text())
        assert data["someKey"] == "someValue"
        assert "rss-reader" in data["mcpServers"]

    def test_install_preserves_other_servers(
        self, config_path: Path, manager: MCPManager
    ) -> None:
        config_path.write_text(
            json.dumps(
                {"mcpServers": {"existing": {"type": "stdio", "command": "x", "args": []}}}
            ),
            encoding="utf-8",
        )
        manager.install("todoist")
        data = json.loads(config_path.read_text())
        assert "existing" in data["mcpServers"]
        assert "todoist" in data["mcpServers"]

    def test_install_with_env(self, config_path: Path, manager: MCPManager) -> None:
        manager.install(
            "google-calendar",
            env_values={"GOOGLE_OAUTH_CREDENTIALS": "/path/to/creds.json"},
        )
        data = json.loads(config_path.read_text())
        entry = data["mcpServers"]["google-calendar"]
        assert entry["env"]["GOOGLE_OAUTH_CREDENTIALS"] == "/path/to/creds.json"
        assert entry["command"] == "npx"

    def test_install_missing_env_raises(self, manager: MCPManager) -> None:
        with pytest.raises(ValueError, match="Missing required environment"):
            manager.install("google-calendar")

    def test_install_unknown_name_raises(self, manager: MCPManager) -> None:
        with pytest.raises(KeyError, match="Unknown MCP server"):
            manager.install("nonexistent")

    def test_install_overwrite(self, config_path: Path, manager: MCPManager) -> None:
        """Re-installing should overwrite the existing entry."""
        manager.install("todoist")
        # Install again — should not raise
        manager.install("todoist")
        data = json.loads(config_path.read_text())
        assert data["mcpServers"]["todoist"]["type"] == "http"

    def test_install_returns_server_def(self, manager: MCPManager) -> None:
        result = manager.install("todoist")
        assert isinstance(result, MCPServerDef)
        assert result.name == "todoist"

    # ── uninstall ──────────────────────────────────────────────────

    def test_uninstall_removes_server(
        self, config_path: Path, manager: MCPManager
    ) -> None:
        manager.install("todoist")
        assert manager.uninstall("todoist")
        data = json.loads(config_path.read_text())
        assert "todoist" not in data["mcpServers"]

    def test_uninstall_preserves_others(
        self, config_path: Path, manager: MCPManager
    ) -> None:
        manager.install("todoist")
        manager.install("rss-reader")
        manager.uninstall("todoist")
        data = json.loads(config_path.read_text())
        assert "rss-reader" in data["mcpServers"]
        assert "todoist" not in data["mcpServers"]

    def test_uninstall_nonexistent_returns_false(self, manager: MCPManager) -> None:
        assert not manager.uninstall("nonexistent")

    def test_uninstall_no_file_returns_false(self, manager: MCPManager) -> None:
        assert not manager.uninstall("todoist")

    # ── status ─────────────────────────────────────────────────────

    def test_status_none_installed(self, manager: MCPManager) -> None:
        status = manager.status()
        assert len(status) == 3
        assert all(not s["installed"] for s in status)

    def test_status_some_installed(
        self, config_path: Path, manager: MCPManager
    ) -> None:
        manager.install("todoist")
        status = manager.status()
        todoist_status = next(s for s in status if s["name"] == "todoist")
        assert todoist_status["installed"] is True
        gcal_status = next(s for s in status if s["name"] == "google-calendar")
        assert gcal_status["installed"] is False
        assert gcal_status["needs_env"] is True
