"""Vault cog: Discord slash commands for vault operations."""

import logging
from datetime import date

import discord
from discord import app_commands
from discord.ext import commands

from .claude_runner import ClaudeRunner
from .config import Config
from .security import is_owner_interaction
from .vault import VaultManager

log = logging.getLogger(__name__)


class VaultCog(commands.Cog):
    """Slash commands for managing the Obsidian vault."""

    def __init__(
        self,
        bot: commands.Bot,
        config: Config,
        runner: ClaudeRunner,
    ) -> None:
        self.bot = bot
        self.config = config
        self.runner = runner
        self.vault = VaultManager(config.vault_path)

    # ── /search ─────────────────────────────────────────────────────

    @app_commands.command(name="search", description="Search vault notes")
    @app_commands.describe(query="Search term (matches filename, tags, body)")
    async def search_notes(self, interaction: discord.Interaction, query: str) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        results = self.vault.search(query)
        if not results:
            await interaction.response.send_message(f"No notes matching **{query}**.")
            return

        lines: list[str] = [f"**Search**: {query} ({len(results)} results)\n"]
        for note in results[:10]:
            tags_str = " ".join(f"`{t}`" for t in note.tags[:5])
            preview = note.body.strip()[:80].replace("\n", " ")
            lines.append(f"• **{note.title}** ({note.rel_path}) {tags_str}\n  {preview}")

        await interaction.response.send_message("\n".join(lines))

    # ── /notes ──────────────────────────────────────────────────────

    @app_commands.command(name="notes", description="List recent notes")
    @app_commands.describe(folder="Subfolder to list (optional)")
    async def list_notes(
        self, interaction: discord.Interaction, folder: str | None = None
    ) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        notes = self.vault.list_notes(folder)
        if not notes:
            msg = f"No notes in **{folder}**." if folder else "Vault is empty."
            await interaction.response.send_message(msg)
            return

        # Sort by mtime descending, show latest 15
        notes.sort(key=lambda n: n.path.stat().st_mtime, reverse=True)
        lines: list[str] = [f"**Notes** ({len(notes)} total)\n"]
        for note in notes[:15]:
            tags_str = " ".join(f"`{t}`" for t in note.tags[:3])
            lines.append(f"• **{note.title}** ({note.rel_path}) {tags_str}")

        if len(notes) > 15:
            lines.append(f"\n... and {len(notes) - 15} more")

        await interaction.response.send_message("\n".join(lines))

    # ── /tags ───────────────────────────────────────────────────────

    @app_commands.command(name="tags", description="Show all tags in vault")
    async def show_tags(self, interaction: discord.Interaction) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        tag_counts = self.vault.all_tags()
        if not tag_counts:
            await interaction.response.send_message("No tags found in vault.")
            return

        lines: list[str] = [f"**Tags** ({len(tag_counts)} unique)\n"]
        for tag, count in list(tag_counts.items())[:30]:
            lines.append(f"`{tag}` ({count})")

        if len(tag_counts) > 30:
            lines.append(f"\n... and {len(tag_counts) - 30} more")

        await interaction.response.send_message(" · ".join(lines))

    # ── /save ───────────────────────────────────────────────────────

    @app_commands.command(name="save", description="Save a note to vault")
    @app_commands.describe(
        title="Note title",
        content="Note body (markdown)",
        tags="Comma-separated tags (e.g. python, ai)",
        folder="Subfolder (default: root)",
    )
    async def save_note(
        self,
        interaction: discord.Interaction,
        title: str,
        content: str,
        tags: str | None = None,
        folder: str | None = None,
    ) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        # Build filename
        safe_title = title.replace(" ", "-").replace("/", "-")
        rel = f"{folder}/{safe_title}.md" if folder else f"{safe_title}.md"

        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []
        frontmatter = {
            "title": title,
            "tags": tag_list,
            "created": str(date.today()),
        }

        try:
            note = self.vault.create_note(rel, body=f"\n{content}\n", frontmatter=frontmatter)
            tags_display = " ".join(f"`{t}`" for t in tag_list) if tag_list else "(none)"
            await interaction.response.send_message(
                f"Saved **{title}** → `{note.rel_path}` {tags_display}"
            )
        except FileExistsError:
            await interaction.response.send_message(
                f"Note `{rel}` already exists. Use a different title.", ephemeral=True
            )

    # ── /autotag ────────────────────────────────────────────────────

    @app_commands.command(name="autotag", description="Auto-tag a note with AI")
    @app_commands.describe(path="Relative path to the note (e.g. 'my-note.md')")
    async def auto_tag_note(self, interaction: discord.Interaction, path: str) -> None:
        if not is_owner_interaction(interaction, self.config.owner_id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            note = self.vault.read_note(path)
        except (FileNotFoundError, ValueError) as e:
            await interaction.followup.send(str(e))
            return

        suggested = await self.vault.auto_tag(note, self.runner)
        if not suggested:
            await interaction.followup.send("Could not generate tags for this note.")
            return

        # Merge with existing tags (no duplicates)
        existing = {t.lower() for t in note.tags}
        new_tags = [t for t in suggested if t not in existing]

        if not new_tags:
            await interaction.followup.send(
                f"**{note.title}** already has all suggested tags: "
                + " ".join(f"`{t}`" for t in suggested)
            )
            return

        note.frontmatter["tags"] = note.tags + new_tags
        self.vault.write_note(note)

        await interaction.followup.send(
            f"Tagged **{note.title}** with: "
            + " ".join(f"`{t}`" for t in new_tags)
            + f"\nAll tags: {' '.join(f'`{t}`' for t in note.frontmatter['tags'])}"
        )


async def setup(bot: commands.Bot) -> None:
    config: Config = bot.config  # type: ignore[attr-defined]
    runner: ClaudeRunner = bot.runner  # type: ignore[attr-defined]
    await bot.add_cog(VaultCog(bot, config, runner))
