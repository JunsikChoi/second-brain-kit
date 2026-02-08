"""MCP cog: Discord slash commands for MCP server management."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .config import Config
from .mcp_registry import REGISTRY, MCPManager
from .security import is_owner_interaction

log = logging.getLogger(__name__)


class MCPCog(commands.Cog):
    """Slash commands for managing MCP servers."""

    mcp_group = app_commands.Group(name="mcp", description="MCP server management")

    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.bot = bot
        self.config = config
        self.manager = MCPManager()

    # ── /mcp list ──────────────────────────────────────────────────

    @mcp_group.command(name="list", description="List available MCP servers")
    async def mcp_list(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        status = self.manager.status()
        lines: list[str] = ["**Available MCP Servers**\n"]
        for s in status:
            icon = "\u2705" if s["installed"] else "\u274c"
            env_note = " (requires config)" if s["needs_env"] else ""
            lines.append(f"{icon} **{s['display_name']}** (`{s['name']}`){env_note}")

        lines.append("\nUse `/mcp install name:<server>` to install.")
        await interaction.response.send_message("\n".join(lines))

    # ── /mcp install ───────────────────────────────────────────────

    @mcp_group.command(name="install", description="Install an MCP server")
    @app_commands.describe(
        name="MCP server name (e.g. google-calendar, todoist, rss-reader)",
        env="Environment variables as KEY=VALUE pairs, comma-separated",
    )
    async def mcp_install(
        self,
        interaction: discord.Interaction,
        name: str,
        env: str | None = None,
    ) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        # Parse env values
        env_values: dict[str, str] | None = None
        if env:
            env_values = {}
            for pair in env.split(","):
                pair = pair.strip()
                if "=" not in pair:
                    await interaction.response.send_message(
                        f"Invalid env format: `{pair}`. Use `KEY=VALUE`.",
                        ephemeral=True,
                    )
                    return
                key, value = pair.split("=", 1)
                env_values[key.strip()] = value.strip()

        try:
            server_def = self.manager.install(name, env_values)
            await interaction.response.send_message(
                f"\u2705 Installed **{server_def.display_name}** (`{name}`).\n"
                "Restart Claude Code to activate."
            )
        except KeyError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except ValueError as e:
            # Missing env vars — show setup guide
            await interaction.response.send_message(str(e), ephemeral=True)

    @mcp_install.autocomplete("name")
    async def _install_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        installed = self.manager.list_installed()
        return [
            app_commands.Choice(name=f"{d.display_name} ({d.name})", value=d.name)
            for d in REGISTRY.values()
            if d.name not in installed and current.lower() in d.name.lower()
        ][:25]

    # ── /mcp remove ────────────────────────────────────────────────

    @mcp_group.command(name="remove", description="Remove an installed MCP server")
    @app_commands.describe(name="MCP server name to remove")
    async def mcp_remove(self, interaction: discord.Interaction, name: str) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        removed = self.manager.uninstall(name)
        if removed:
            display = REGISTRY[name].display_name if name in REGISTRY else name
            await interaction.response.send_message(
                f"\u2705 Removed **{display}** (`{name}`).\n"
                "Restart Claude Code to apply."
            )
        else:
            await interaction.response.send_message(
                f"`{name}` is not installed.", ephemeral=True
            )

    @mcp_remove.autocomplete("name")
    async def _remove_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        installed = self.manager.list_installed()
        return [
            app_commands.Choice(
                name=f"{REGISTRY[n].display_name} ({n})" if n in REGISTRY else n,
                value=n,
            )
            for n in installed
            if current.lower() in n.lower()
        ][:25]

    # ── /mcp status ────────────────────────────────────────────────

    @mcp_group.command(name="status", description="Show installed MCP server status")
    async def mcp_status(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        installed = self.manager.list_installed()
        if not installed:
            await interaction.response.send_message(
                "No MCP servers installed.\nUse `/mcp list` to see available servers."
            )
            return

        lines: list[str] = [f"**Installed MCP Servers** ({len(installed)})\n"]
        for name, entry in installed.items():
            server_type = entry.get("type", "unknown")
            if name in REGISTRY:
                display = REGISTRY[name].display_name
            else:
                display = name
            lines.append(f"\u2022 **{display}** (`{name}`) — {server_type}")

        await interaction.response.send_message("\n".join(lines))


async def setup(bot: commands.Bot) -> None:
    config: Config = bot.config  # type: ignore[attr-defined]
    await bot.add_cog(MCPCog(bot, config))
