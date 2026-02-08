"""SecondBrainBot: commands.Bot subclass with shared state."""

import logging

import discord
from discord.ext import commands

from .claude_runner import ClaudeRunner
from .config import Config
from .session_store import SessionStore

log = logging.getLogger(__name__)


class SecondBrainBot(commands.Bot):
    """Discord bot that bridges messages to Claude Code CLI with vault integration."""

    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self.config = config
        self.store = SessionStore(default_model=config.claude_model)
        self.runner = ClaudeRunner(
            model=config.claude_model,
            max_budget_usd=config.max_budget_usd,
            allowed_tools=config.allowed_tools,
            cwd=config.vault_path,
        )

    async def setup_hook(self) -> None:
        await self.load_extension("second_brain_kit.cog_chat")
        await self.load_extension("second_brain_kit.cog_admin")
        await self.load_extension("second_brain_kit.cog_vault")
        await self.tree.sync()
        log.info("Slash commands synced.")

    async def on_ready(self) -> None:
        log.info("Bot ready as %s (ID: %s)", self.user, self.user.id if self.user else "?")
        log.info("Owner ID: %s", self.config.owner_id)
        log.info("Model: %s", self.config.claude_model)
        log.info("Vault: %s", self.config.vault_path)

        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Synced commands to guild %s", guild.id)
