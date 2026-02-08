"""MCP server registry and manager for Claude Code integration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# ── MCP Server Definition ──────────────────────────────────────────


@dataclass(frozen=True)
class MCPServerDef:
    """Definition of a supported MCP server."""

    name: str
    display_name: str
    description: str
    server_type: str  # "stdio" | "http"
    # stdio fields
    command: str | None = None
    args: list[str] = field(default_factory=list)
    # http fields
    url: str | None = None
    # env vars: key → description/hint for the user
    env_vars: dict[str, str] = field(default_factory=dict)
    setup_guide: str = ""

    def to_claude_config(self, env_values: dict[str, str] | None = None) -> dict[str, Any]:
        """Convert to ~/.claude.json mcpServers entry format."""
        if self.server_type == "http":
            entry: dict[str, Any] = {"type": "http", "url": self.url}
        else:
            entry = {"type": "stdio", "command": self.command, "args": list(self.args)}
            if self.env_vars and env_values:
                entry["env"] = {k: env_values[k] for k in self.env_vars if k in env_values}
        return entry


# ── Built-in Registry ──────────────────────────────────────────────

REGISTRY: dict[str, MCPServerDef] = {
    "google-calendar": MCPServerDef(
        name="google-calendar",
        display_name="Google Calendar",
        description="Read and manage Google Calendar events",
        server_type="stdio",
        command="npx",
        args=["-y", "@cocal/google-calendar-mcp"],
        env_vars={
            "GOOGLE_OAUTH_CREDENTIALS": "Path to Google OAuth credentials JSON file",
        },
        setup_guide=(
            "**Google Calendar MCP Setup**\n\n"
            "1. Go to [Google Cloud Console](https://console.cloud.google.com/)\n"
            "2. Create a project and enable the Calendar API\n"
            "3. Create OAuth 2.0 credentials (Desktop app type)\n"
            "4. Download the credentials JSON file\n"
            "5. Install with:\n"
            "   `/mcp install name:google-calendar "
            "env:GOOGLE_OAUTH_CREDENTIALS=/path/to/credentials.json`"
        ),
    ),
    "todoist": MCPServerDef(
        name="todoist",
        display_name="Todoist",
        description="Manage Todoist tasks, projects, and labels",
        server_type="http",
        url="https://ai.todoist.net/mcp",
        setup_guide=(
            "**Todoist MCP Setup**\n\n"
            "No configuration needed! Todoist MCP uses the hosted endpoint.\n"
            "Just run `/mcp install name:todoist` to enable."
        ),
    ),
    "rss-reader": MCPServerDef(
        name="rss-reader",
        display_name="RSS Reader",
        description="Fetch and read RSS/Atom feed entries",
        server_type="stdio",
        command="npx",
        args=["-y", "rss-reader-mcp"],
        setup_guide=(
            "**RSS Reader MCP Setup**\n\n"
            "No configuration needed!\n"
            "Just run `/mcp install name:rss-reader` to enable."
        ),
    ),
}


# ── MCP Manager ────────────────────────────────────────────────────


class MCPManager:
    """Manages MCP server entries in ~/.claude.json."""

    def __init__(self, claude_config_path: Path | None = None) -> None:
        self.config_path = claude_config_path or Path.home() / ".claude.json"

    # ── Read operations ────────────────────────────────────────────

    def list_registered(self) -> list[MCPServerDef]:
        """Return all MCP servers in the built-in registry."""
        return list(REGISTRY.values())

    def _read_config(self) -> dict[str, Any]:
        """Read ~/.claude.json, returning empty dict if missing."""
        if not self.config_path.exists():
            return {}
        text = self.config_path.read_text(encoding="utf-8")
        return json.loads(text) if text.strip() else {}

    def _write_config(self, config: dict[str, Any]) -> None:
        """Write config back to ~/.claude.json, preserving all keys."""
        self.config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def list_installed(self) -> dict[str, Any]:
        """Return currently installed mcpServers from ~/.claude.json."""
        config = self._read_config()
        return dict(config.get("mcpServers", {}))

    def is_installed(self, name: str) -> bool:
        """Check if a specific MCP server is installed."""
        return name in self.list_installed()

    # ── Write operations ───────────────────────────────────────────

    def install(self, name: str, env_values: dict[str, str] | None = None) -> MCPServerDef:
        """Install an MCP server by adding it to ~/.claude.json.

        Args:
            name: Registry name of the MCP server.
            env_values: Actual env var values (e.g. {"API_KEY": "abc123"}).

        Returns:
            The MCPServerDef that was installed.

        Raises:
            KeyError: If name is not in the registry.
        """
        if name not in REGISTRY:
            raise KeyError(
                f"Unknown MCP server: {name}. "
                f"Available: {', '.join(REGISTRY.keys())}"
            )

        server_def = REGISTRY[name]

        # Validate required env vars
        missing = []
        if server_def.env_vars:
            provided = env_values or {}
            missing = [k for k in server_def.env_vars if k not in provided]

        if missing:
            raise ValueError(
                f"Missing required environment variables for {server_def.display_name}: "
                + ", ".join(missing)
                + f"\n\n{server_def.setup_guide}"
            )

        config = self._read_config()
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"][name] = server_def.to_claude_config(env_values)
        self._write_config(config)

        log.info("Installed MCP server: %s", name)
        return server_def

    def uninstall(self, name: str) -> bool:
        """Remove an MCP server from ~/.claude.json.

        Returns:
            True if the server was removed, False if it wasn't installed.
        """
        config = self._read_config()
        servers = config.get("mcpServers", {})

        if name not in servers:
            return False

        del servers[name]
        self._write_config(config)

        log.info("Uninstalled MCP server: %s", name)
        return True

    def status(self) -> list[dict[str, str | bool]]:
        """Return install status for each registered MCP server."""
        installed = self.list_installed()
        result: list[dict[str, str | bool]] = []
        for server_def in REGISTRY.values():
            result.append({
                "name": server_def.name,
                "display_name": server_def.display_name,
                "installed": server_def.name in installed,
                "needs_env": bool(server_def.env_vars),
            })
        return result
