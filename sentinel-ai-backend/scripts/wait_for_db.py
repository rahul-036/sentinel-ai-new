#!/usr/bin/env python3
"""Wait for the database to become available before starting the app."""

import asyncio
import sys

from tenacity import retry, stop_after_attempt, wait_fixed


@retry(stop=stop_after_attempt(30), wait=wait_fixed(2))
async def wait_for_db() -> None:
    import asyncpg

    from app.core.config import get_settings

    settings = get_settings()
    # asyncpg uses postgresql:// not postgresql+asyncpg://
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    await conn.close()
    print("Database is ready.")


if __name__ == "__main__":
    try:
        asyncio.run(wait_for_db())
    except Exception as exc:
        print(f"Database not available after retries: {exc}", file=sys.stderr)
        sys.exit(1)
