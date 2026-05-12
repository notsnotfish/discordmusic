"""
extensions/owner.py — Owner-only admin commands for Discodrome.

Access gate: every command is protected by a single cog_check.
Non-owners are silently ignored — no error, no acknowledgement.
"""

import logging

import discord
from discord.ext import commands

import db
from util import env

logger = logging.getLogger(__name__)


class AdminCog(commands.Cog, name="Admin"):
    """Owner-only management commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Single access gate ────────────────────────────────────────────────

    async def cog_check(self, ctx: commands.Context) -> bool:  # type: ignore[override]
        return ctx.author.id == env.DISCORD_OWNER_ID

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Swallow CheckFailure — commands appear not to exist to non-owners."""
        if isinstance(error, commands.CheckFailure):
            return  # silent ignore
        logger.error("AdminCog error in %s: %s", ctx.command, error, exc_info=error)

    # ── Guild management ──────────────────────────────────────────────────

    @commands.command(name="addguild")
    async def add_guild(self, ctx: commands.Context, guild_id: int) -> None:
        """Register a guild. Usage: !addguild <guild_id>"""
        if db.add_guild(guild_id):
            await ctx.send(
                f"✅ Guild `{guild_id}` added. Run `!syncguilds` to push slash commands."
            )
            logger.info("Owner added guild %d.", guild_id)
        else:
            await ctx.send(f"ℹ️ Guild `{guild_id}` is already registered.")

    @commands.command(name="removeguild")
    async def remove_guild(self, ctx: commands.Context, guild_id: int) -> None:
        """Unregister a guild. Usage: !removeguild <guild_id>"""
        if db.remove_guild(guild_id):
            await ctx.send(f"✅ Guild `{guild_id}` removed.")
            logger.info("Owner removed guild %d.", guild_id)
        else:
            await ctx.send(f"⚠️ Guild `{guild_id}` was not in the database.")

    @commands.command(name="listguilds")
    async def list_guilds(self, ctx: commands.Context) -> None:
        """List all registered guilds. Usage: !listguilds"""
        guilds = db.list_guilds()
        if guilds:
            lines = "\n".join(f"• `{g}`" for g in guilds)
            await ctx.send(f"**Registered guilds ({len(guilds)}):**\n{lines}")
        else:
            await ctx.send("No guilds are currently registered.")

    @commands.command(name="syncguilds")
    async def sync_guilds(self, ctx: commands.Context) -> None:
        """Sync slash commands to all registered guilds. Usage: !syncguilds"""
        guilds = db.list_guilds()
        if not guilds:
            await ctx.send("⚠️ No guilds registered. Use `!addguild <id>` first.")
            return

        await ctx.send(f"⏳ Syncing to {len(guilds)} guild(s)…")
        synced, failed = [], []

        for gid in guilds:
            guild_obj = discord.Object(id=gid)
            try:
                self.bot.tree.copy_global_to(guild=guild_obj)
                await self.bot.tree.sync(guild=guild_obj)
                synced.append(gid)
                logger.info("Synced slash commands to guild %d.", gid)
            except discord.HTTPException as exc:
                failed.append(gid)
                logger.error("Failed to sync guild %d: %s", gid, exc)

        lines = [
            f"✅ Synced {len(synced)} guild(s): {', '.join(f'`{g}`' for g in synced)}"
        ]
        if failed:
            lines.append(
                f"❌ Failed for {len(failed)} guild(s): {', '.join(f'`{g}`' for g in failed)}"
            )
        await ctx.send("\n".join(lines))

    # ── Role-based access control ─────────────────────────────────────────

    @commands.command(name="allowrole")
    async def allow_role(self, ctx: commands.Context, role: discord.Role) -> None:
        """Whitelist a role for music commands. Usage: !allowrole @Role
        
        Falls back to allowing everyone when no roles are configured (safe default).
        """
        if db.allow_role(ctx.guild.id, role.id):
            await ctx.send(f"✅ **{role.name}** can now use music commands.")
            logger.info("Whitelisted role %d (%s) in guild %d.", role.id, role.name, ctx.guild.id)
        else:
            await ctx.send(f"ℹ️ **{role.name}** is already whitelisted.")

    @commands.command(name="denyrole")
    async def deny_role(self, ctx: commands.Context, role: discord.Role) -> None:
        """Remove a role from the music whitelist. Usage: !denyrole @Role"""
        if db.deny_role(ctx.guild.id, role.id):
            await ctx.send(f"✅ **{role.name}** can no longer use music commands.")
            logger.info("Removed role %d (%s) from guild %d.", role.id, role.name, ctx.guild.id)
        else:
            await ctx.send(f"⚠️ **{role.name}** was not in the whitelist.")

    @commands.command(name="listroles")
    async def list_roles(self, ctx: commands.Context) -> None:
        """List whitelisted roles for this guild. Usage: !listroles"""
        role_ids = db.get_allowed_roles(ctx.guild.id)
        if not role_ids:
            await ctx.send(
                "No role restrictions set — everyone can use music commands in this guild."
            )
            return
        lines = []
        for rid in role_ids:
            role = ctx.guild.get_role(rid)
            name = role.name if role else f"Unknown Role ({rid})"
            lines.append(f"• **{name}** (`{rid}`)")
        await ctx.send(
            f"**Whitelisted roles ({len(lines)}):**\n" + "\n".join(lines)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
    logger.info("AdminCog loaded.")