from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import get_logger

logger = get_logger(__name__)


async def init_db(engine: AsyncEngine) -> bool:
    """Probe database connectivity on startup.

    Returns True when the database is reachable, False otherwise.
    Never raises — a missing database must not prevent the app from starting.
    """
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        return True
    except Exception as exc:
        logger.warning(
            "Database unavailable at startup — continuing without DB",
            error=str(exc),
            hint="Run 'docker compose up db' or set DATABASE_URL to a reachable instance.",
        )
        return False
