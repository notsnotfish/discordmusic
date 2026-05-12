import asyncio
import signal
import sys
import discord
import logging
import os

logger = logging.getLogger(__name__)

from discord.ext import commands

import data
import db
from util import env
from util import logs
from subsonic import close_session, ping_api


class DiscodromeClient(commands.Bot):
    """An instance of the Discodrome client."""

    def __init__(self) -> None:
        if env.BOT_PREFIX is not None:
            if len(env.BOT_PREFIX) > 0:
                logger.info("Command prefix is %s", env.BOT_PREFIX)
            else:
                logger.info(
                    "Command prefix is an empty string. "
                    "ALL MESSAGES WILL BE INTERPRETED AS COMMANDS."
                )
        else:
            logger.info("Command prefix not set.")

        prefix = (
            commands.when_mentioned
            if env.BOT_PREFIX is None
            else commands.when_mentioned_or(env.BOT_PREFIX)
        )
        super().__init__(command_prefix=prefix, intents=discord.Intents.all())

    async def load_extensions(self) -> None:
        """Auto-loads all extensions present within the `./extensions` directory."""
        for file in os.listdir("./extensions"):
            if file.endswith(".py"):
                ext_name = file[:-3]
                try:
                    await self.load_extension(f"extensions.{ext_name}")
                except commands.errors.ExtensionError as err:
                    if isinstance(err, commands.errors.ExtensionNotFound):
                        logger.warning("Failed to load '%s'. Not found.", ext_name)
                    elif isinstance(err, commands.errors.ExtensionAlreadyLoaded):
                        logger.warning("Failed to load '%s'. Already loaded.", ext_name)
                    elif isinstance(err, commands.errors.NoEntryPointError):
                        logger.error("Failed to load '%s'. No entry point.", ext_name, exc_info=err)
                    elif isinstance(err, commands.errors.ExtensionFailed):
                        logger.error("Failed to load '%s'. Setup failed.", ext_name, exc_info=err)
                else:
                    logger.info("Extension '%s' loaded successfully.", ext_name)

    async def sync_to_all_guilds(self) -> None:
        """Sync slash commands to every guild registered in the database."""
        guilds = db.list_guilds()
        if not guilds:
            logger.warning("No guilds in database — skipping startup sync.")
            return
        for gid in guilds:
            guild_obj = discord.Object(id=gid)
            try:
                self.tree.copy_global_to(guild=guild_obj)
                await self.tree.sync(guild=guild_obj)
                logger.info("Synced slash commands to guild %d.", gid)
            except discord.HTTPException as exc:
                logger.error("Failed to sync guild %d: %s", gid, exc)

    async def setup_hook(self) -> None:
        """Setup done after login, prior to events being dispatched."""
        await self.load_extensions()

        if await ping_api():
            logger.info("Subsonic API is online.")
        else:
            logger.error("Subsonic API is unreachable.")

        await self.sync_to_all_guilds()

        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(
                signal.SIGTERM,
                lambda: asyncio.ensure_future(self._on_sigterm()),
            )

    async def _on_sigterm(self) -> None:
        """Graceful shutdown on SIGTERM."""
        logger.debug("Beginning graceful shutdown...")
        data.save_guild_properties_to_disk()
        await close_session()
        logger.info("Discodrome shutdown complete.")
        await self.close()

    async def on_ready(self) -> None:
        """Event called when the client is done preparing."""
        activity = discord.Activity(
            type=discord.ActivityType.playing, name=env.BOT_STATUS
        )
        await self.change_presence(activity=activity)
        logger.info(
            "Logged as: %s | Connected Guilds: %s | Loaded Extensions: %s",
            self.user,
            len(self.guilds),
            list(self.extensions),
        )


if __name__ == "__main__":
    logs.setup_logging()
    logger = logging.getLogger(__name__)

    # 1. Initialise DB — creates tables + seeds from DISCORD_TEST_GUILD if present
    db.init_db()

    # 2. Load saved guild properties (queue, autoplay, etc.)
    data.load_guild_properties_from_disk()

    # 3. Run — no test_guild arg needed anymore
    client = DiscodromeClient()
    client.run(env.DISCORD_BOT_TOKEN, log_handler=None)