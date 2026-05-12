"""
db.py — SQLite-backed persistence for guild management and role-based access control.

Tables:
  guilds(id INTEGER PRIMARY KEY)
  allowed_roles(guild_id INTEGER, role_id INTEGER, PRIMARY KEY (guild_id, role_id))
"""

import sqlite3
import logging
import os
from typing import Optional
from util import env

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "guilds.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist and seed from DISCORD_TEST_GUILD env var."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS guilds (
                id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS allowed_roles (
                guild_id INTEGER NOT NULL,
                role_id  INTEGER NOT NULL,
                PRIMARY KEY (guild_id, role_id)
            );
        """)
        logger.info("Database initialised at %s", DB_PATH)

    # On-startup migration: seed from legacy env var so nothing breaks
    seed: Optional[str] = env.DISCORD_TEST_GUILD
    if seed:
        try:
            gid = int(seed)
            if add_guild(gid):
                logger.info("Seeded guild %d from DISCORD_TEST_GUILD env var.", gid)
        except (ValueError, TypeError):
            logger.warning("DISCORD_TEST_GUILD is not a valid integer; skipping seed.")


# ── Guild management ────────────────────────────────────────────────────────

def add_guild(guild_id: int) -> bool:
    """Insert a guild. Returns True if newly inserted."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO guilds (id) VALUES (?)", (guild_id,)
        )
        return cur.rowcount > 0


def remove_guild(guild_id: int) -> bool:
    """Remove a guild and all its role entries. Returns True if deleted."""
    with _connect() as conn:
        conn.execute("DELETE FROM allowed_roles WHERE guild_id = ?", (guild_id,))
        cur = conn.execute("DELETE FROM guilds WHERE id = ?", (guild_id,))
        return cur.rowcount > 0


def list_guilds() -> list[int]:
    """Return all registered guild IDs."""
    with _connect() as conn:
        rows = conn.execute("SELECT id FROM guilds ORDER BY id").fetchall()
    return [r["id"] for r in rows]


# ── Role-based access control ───────────────────────────────────────────────

def allow_role(guild_id: int, role_id: int) -> bool:
    """Whitelist a role for a guild. Returns True if newly inserted."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO allowed_roles (guild_id, role_id) VALUES (?, ?)",
            (guild_id, role_id),
        )
        return cur.rowcount > 0


def deny_role(guild_id: int, role_id: int) -> bool:
    """Remove a role from the whitelist. Returns True if deleted."""
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM allowed_roles WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id),
        )
        return cur.rowcount > 0


def get_allowed_roles(guild_id: int) -> list[int]:
    """Return all whitelisted role IDs for a guild (empty = everyone allowed)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role_id FROM allowed_roles WHERE guild_id = ?", (guild_id,)
        ).fetchall()
    return [r["role_id"] for r in rows]


def user_has_access(guild_id: int, member_role_ids: list[int]) -> bool:
    """
    Returns True if the member may use music commands.

    - No roles configured for this guild → allow everyone (safe default).
    - Otherwise → member must hold at least one whitelisted role.
    """
    allowed = get_allowed_roles(guild_id)
    if not allowed:
        return True
    return bool(set(member_role_ids) & set(allowed))