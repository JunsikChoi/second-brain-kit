"""Chat cog: handles messages and slash commands."""

import io
import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from .claude_runner import ClaudeRunner
from .config import Config
from .file_handler import build_file_prompt, detect_output_files, download_attachments
from .message_splitter import split_message
from .security import is_owner, is_owner_interaction
from .session_store import SessionStore

log = logging.getLogger(__name__)


class ChatCog(commands.Cog):
    """Bridges Discord messages to Claude Code CLI."""

    def __init__(
        self,
        bot: commands.Bot,
        config: Config,
        store: SessionStore,
        runner: ClaudeRunner,
    ) -> None:
        self.bot = bot
        self.config = config
        self.store = store
        self.runner = runner

    @staticmethod
    def _get_session_key(channel: discord.abc.Messageable) -> int:
        if isinstance(channel, discord.Thread):
            return channel.parent_id or channel.id
        ch = getattr(channel, "id", 0)
        return int(ch)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if not is_owner(message, self.config.owner_id):
            return
        if message.content.startswith("/"):
            return

        try:
            await self._handle_message(message)
        except Exception as e:
            log.exception("Unexpected error handling message")
            await message.reply(
                f"오류가 발생했습니다.\n`{type(e).__name__}: {str(e)[:200]}`",
                mention_author=False,
            )

    async def _handle_message(self, message: discord.Message) -> None:
        prompt = message.content.strip()

        # Handle file attachments
        if message.attachments:
            try:
                file_paths: list[Path] = await download_attachments(
                    message.attachments, self.config.download_dir
                )
                prompt += build_file_prompt(file_paths)
            except Exception as e:
                log.error("File processing failed: %s", e)
                await message.reply("파일 처리에 실패했습니다.", mention_author=False)
                return

        if not prompt:
            return

        session_key = self._get_session_key(message.channel)
        session = self.store.get(session_key)

        async with message.channel.typing():
            response = await self.runner.run(
                prompt,
                channel_id=session_key,
                model=session.model,
                session_id=session.session_id,
                system_prompt=session.system_prompt,
                cwd=self.config.vault_path,
            )

            if response.is_error:
                error_preview = response.text[:300] if response.text else "unknown error"
                await message.reply(
                    f"Claude 실행에 실패했습니다.\n```\n{error_preview}\n```",
                    mention_author=False,
                )
                return

            self.store.update_after_response(
                session_key, response.session_id, response.cost_usd
            )
            session = self.store.get(session_key)

            chunks = split_message(response.text)
            for chunk in chunks:
                await message.channel.send(chunk)

            output_files = detect_output_files(response.text)
            for fpath in output_files:
                try:
                    await message.channel.send(file=discord.File(str(fpath)))
                except Exception as e:
                    log.warning("Failed to send file %s: %s", fpath, e)

            self.store.add_history(session_key, prompt, response.text)

            if response.cost_usd > 0:
                footer = (
                    f"-# {session.model} · Turn {session.turn_count} · "
                    f"${response.cost_usd:.4f} · {response.duration_secs:.1f}s"
                )
                await message.channel.send(footer)

    @app_commands.command(name="new", description="Start a new session")
    async def new_session(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        session_key = self._get_session_key(interaction.channel)  # type: ignore[arg-type]
        self.store.reset(session_key)
        await interaction.response.send_message("New session started.")

    @app_commands.command(name="model", description="Change Claude model")
    @app_commands.choices(
        name=[
            app_commands.Choice(name="sonnet", value="sonnet"),
            app_commands.Choice(name="opus", value="opus"),
            app_commands.Choice(name="haiku", value="haiku"),
        ]
    )
    async def change_model(
        self, interaction: discord.Interaction, name: app_commands.Choice[str]
    ) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        session_key = self._get_session_key(interaction.channel)  # type: ignore[arg-type]
        self.store.set_model(session_key, name.value)
        await interaction.response.send_message(f"Model changed to **{name.value}**.")

    @app_commands.command(name="status", description="Current session info")
    async def session_status(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        session_key = self._get_session_key(interaction.channel)  # type: ignore[arg-type]
        session = self.store.get(session_key)
        lines = [
            f"**Model**: {session.model}",
            f"**Session**: `{session.session_id or 'none'}`",
            f"**Turns**: {session.turn_count}",
            f"**Cost**: ${session.total_cost_usd:.4f}",
            f"**Vault**: {self.config.vault_path}",
        ]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="system", description="Set or view system prompt")
    @app_commands.describe(prompt="System prompt (omit to view)")
    async def system_prompt_cmd(
        self, interaction: discord.Interaction, prompt: str | None = None
    ) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        session_key = self._get_session_key(interaction.channel)  # type: ignore[arg-type]
        session = self.store.get(session_key)

        if prompt is None:
            if session.system_prompt:
                await interaction.response.send_message(
                    f"**System Prompt**:\n{session.system_prompt}"
                )
            else:
                await interaction.response.send_message("No system prompt set.")
            return

        self.store.set_system_prompt(session_key, prompt)
        preview = prompt[:100] + ("..." if len(prompt) > 100 else "")
        await interaction.response.send_message(f"System prompt set: {preview}")

    @app_commands.command(name="export", description="Export conversation history")
    async def export_conversation(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        session_key = self._get_session_key(interaction.channel)  # type: ignore[arg-type]
        session = self.store.get(session_key)
        if not session.history:
            await interaction.response.send_message("No conversation to export.")
            return

        lines = ["# Second Brain Conversation Export\n"]
        for i, (user_msg, bot_msg) in enumerate(session.history, 1):
            lines.append(f"## Turn {i}\n\n**User**: {user_msg}\n\n**Claude**: {bot_msg}\n")

        content = "\n".join(lines)
        file = discord.File(io.BytesIO(content.encode()), filename="conversation.md")
        await interaction.response.send_message("Conversation exported:", file=file)


async def setup(bot: commands.Bot) -> None:
    config = bot.config  # type: ignore[attr-defined]
    store = bot.store  # type: ignore[attr-defined]
    runner = bot.runner  # type: ignore[attr-defined]
    await bot.add_cog(ChatCog(bot, config, store, runner))
