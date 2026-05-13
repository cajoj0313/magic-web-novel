"""SQLite database access for index.db — async via aiosqlite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite

from app.core.logger import get_logger

logger = get_logger(__name__)


class SQLiteAccess:
    """Async read access to the project's index.db SQLite database.

    The database is located at ``{project_root}/index.db`` and contains
    ``entities`` and ``relationships`` tables.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def _connect(self) -> aiosqlite.Connection:
        if self._conn is None or not self._conn._conn:
            assert self._db_path is not None, "db_path must be set before use"
            self._conn = await aiosqlite.connect(str(self._db_path))
            self._conn.row_factory = aiosqlite.Row
            logger.debug("SQLite connection opened: %s", self._db_path)
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.debug("SQLite connection closed")

    # ------------------------------------------------------------------
    # Core query
    # ------------------------------------------------------------------

    async def query(self, table: str, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute a raw SQL query and return rows as dicts.

        Args:
            table: Table name (used for logging / validation).
            sql: SQL statement with parameter placeholders.
            params: Optional dict of parameters.
        """
        conn = await self._connect()
        cursor = await conn.execute(sql, params or {})
        rows = await cursor.fetchall()
        result = [dict(row) for row in rows]
        logger.debug("SQLite query on '%s': %d rows returned", table, len(result))
        return result

    # ------------------------------------------------------------------
    # Entity operations
    # ------------------------------------------------------------------

    async def get_entities(
        self,
        project_root: Path,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query the entities table, optionally filtered by type.

        Sets db_path from project_root if not already configured.
        """
        await self._ensure_db(project_root)
        if entity_type:
            return await self.query(
                "entities",
                "SELECT * FROM entities WHERE type = :type ORDER BY name",
                {"type": entity_type},
            )
        return await self.query("entities", "SELECT * FROM entities ORDER BY name")

    async def get_entity_by_id(
        self,
        project_root: Path,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Get a single entity by ID."""
        await self._ensure_db(project_root)
        rows = await self.query(
            "entities",
            "SELECT * FROM entities WHERE id = :id",
            {"id": entity_id},
        )
        return rows[0] if rows else None

    async def search_entities(
        self,
        project_root: Path,
        keyword: str,
    ) -> list[dict[str, Any]]:
        """Full-text / LIKE search on entity names and descriptions."""
        await self._ensure_db(project_root)
        pattern = f"%{keyword}%"
        return await self.query(
            "entities",
            "SELECT * FROM entities WHERE name LIKE :name OR description LIKE :desc",
            {"name": pattern, "desc": pattern},
        )

    # ------------------------------------------------------------------
    # Relationship operations
    # ------------------------------------------------------------------

    async def get_relationships(
        self,
        project_root: Path,
        relationship_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query the relationships table, optionally filtered by type."""
        await self._ensure_db(project_root)
        if relationship_type:
            return await self.query(
                "relationships",
                "SELECT * FROM relationships WHERE type = :type",
                {"type": relationship_type},
            )
        return await self.query("relationships", "SELECT * FROM relationships")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_db(self, project_root: Path) -> None:
        """Derive db_path from project_root if not already set."""
        if self._db_path is None:
            self._db_path = project_root / "index.db"
            if not self._db_path.exists():
                raise FileNotFoundError(f"index.db not found at {self._db_path}")
