from collections.abc import AsyncGenerator

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row

from .config import get_settings


async def get_db() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """Open one short-lived connection per request for the small assessment app."""
    try:
        connection = await psycopg.AsyncConnection.connect(
            get_settings().database_url,
            row_factory=dict_row,
        )
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="The database is unavailable. Apply the migration and seed the database first.",
        ) from exc

    try:
        yield connection
    finally:
        await connection.close()