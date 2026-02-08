"""Owner-only security check."""

import discord


def is_owner(message: discord.Message, owner_id: int) -> bool:
    return message.author.id == owner_id


def is_owner_interaction(interaction: discord.Interaction, owner_id: int) -> bool:
    return interaction.user.id == owner_id
