from discord import app_commands
import discord
import json
import os

def get_config():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
    with open(path, "r") as f:
        return json.load(f)

config = get_config()

OWNER_ID = config.get("owner_id")
STAFF_ROLES = config.get("staff_roles", [])
ALLOWED_GUILDS = config.get("allowed_guilds", [])


# --- BASIC CHECK HELPERS --- #

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def is_staff(member: discord.Member) -> bool:
    return any(role.id in STAFF_ROLES for role in member.roles)


def is_allowed_guild(guild_id: int) -> bool:
    return guild_id in ALLOWED_GUILDS


# --- DECORATORS FOR COMMANDS --- #

def owner_only():
    """Allows ONLY the bot owner."""
    def predicate(interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            raise app_commands.CheckFailure("Only the bot owner may use this command.")
        return True
    return app_commands.check(predicate)


def staff_only():
    """Allows staff OR owner."""
    def predicate(interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        # Allow owner ALWAYS
        if is_owner(user.id):
            return True

        # Validate guild
        if not is_allowed_guild(guild.id):
            raise app_commands.CheckFailure("This command cannot be used in this server.")

        # Validate staff role
        if isinstance(user, discord.Member) and is_staff(user):
            return True

        raise app_commands.CheckFailure("You do not have permission to use this command.")
    return app_commands.check(predicate)


def guild_only():
    """Block commands outside allowed guilds."""
    def predicate(interaction: discord.Interaction):
        if not is_allowed_guild(interaction.guild.id):
            raise app_commands.CheckFailure("This command cannot be used in this server.")
        return True
    return app_commands.check(predicate)
