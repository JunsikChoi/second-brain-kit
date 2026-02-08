"""Admin cog: /cost, /sessions, /kill, /budget."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .claude_runner import ClaudeRunner
from .config import Config
from .security import is_owner_interaction
from .session_store import SessionStore

log = logging.getLogger(__name__)


class AdminCog(commands.Cog):
    def __init__(
        self, bot: commands.Bot, config: Config, store: SessionStore, runner: ClaudeRunner
    ) -> None:
        self.bot = bot
        self.config = config
        self.store = store
        self.runner = runner

    @app_commands.command(name="cost", description="Show total cost")
    async def total_cost(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        total = self.store.total_cost()
        budget = self.runner.max_budget_usd
        await interaction.response.send_message(
            f"**Total cost**: ${total:.4f}\n**Budget per turn**: ${budget:.2f}"
        )

    @app_commands.command(name="sessions", description="List active sessions")
    async def list_sessions(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        sessions = self.store.all_sessions()
        if not sessions:
            await interaction.response.send_message("No active sessions.")
            return
        lines: list[str] = []
        for ch_id, session in sessions.items():
            sid = session.session_id or "none"
            lines.append(
                f"• <#{ch_id}> — {session.model} | "
                f"{session.turn_count} turns | "
                f"${session.total_cost_usd:.4f} | "
                f"`{sid[:8]}...`"
            )
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="kill", description="Kill running Claude processes")
    async def kill_process(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        count = self.runner.running_count
        if count == 0:
            await interaction.response.send_message("No running processes.")
            return
        killed = self.runner.kill()
        await interaction.response.send_message(f"Killed {killed} process(es).")

    @app_commands.command(name="budget", description="Set per-turn budget")
    @app_commands.describe(usd="Max USD per turn")
    async def set_budget(self, interaction: discord.Interaction, usd: float) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        if usd <= 0 or usd > 10:
            await interaction.response.send_message("Budget must be between 0 and 10 USD.")
            return
        self.runner.max_budget_usd = usd
        await interaction.response.send_message(f"Per-turn budget set to **${usd:.2f}**.")


async def setup(bot: commands.Bot) -> None:
    config = bot.config  # type: ignore[attr-defined]
    store = bot.store  # type: ignore[attr-defined]
    runner = bot.runner  # type: ignore[attr-defined]
    await bot.add_cog(AdminCog(bot, config, store, runner))
