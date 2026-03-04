import logging
import os

import asyncpg

logger = logging.getLogger(__name__)

# Module-level pool reference
_pool: asyncpg.Pool | None = None

CATALOGUE_DDL = """
CREATE TABLE IF NOT EXISTS tweet_catalogue (
    id SERIAL PRIMARY KEY,
    tweet_id TEXT NOT NULL,
    tweet_data JSONB NOT NULL,
    machine_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tweet_catalogue_tweet_id ON tweet_catalogue (tweet_id);
CREATE INDEX IF NOT EXISTS idx_tweet_catalogue_created_at ON tweet_catalogue (created_at);
"""


def _build_dsn() -> str:
    """
    Reads DATABASE_URL from environment and ensures it has the postgresql:// scheme prefix.
    Expects format: user:password@host:port/dbname
    """
    raw = os.environ.get("DATABASE_URL", "")
    if not raw:
        raise ValueError("DATABASE_URL environment variable is not set")

    raw = raw.strip().strip("'\"")

    if raw.startswith("postgresql://") or raw.startswith("postgres://"):
        return raw

    return f"postgresql://{raw}"


async def init_pool(min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    """
    Creates the asyncpg connection pool and runs the DDL to ensure the catalogue table exists.
    Returns the pool instance.
    """
    global _pool

    if _pool is not None:
        logger.warning("Pool already initialized, returning existing pool.")
        return _pool

    dsn = _build_dsn()
    logger.info("Connecting to PostgreSQL...")

    _pool = await asyncpg.create_pool(dsn=dsn, min_size=min_size, max_size=max_size)

    # Run DDL
    async with _pool.acquire() as conn:
        await conn.execute(CATALOGUE_DDL)

    logger.info("PostgreSQL pool initialized and catalogue table ensured.")
    return _pool


def get_pool() -> asyncpg.Pool:
    """Returns the current pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_pool() first.")
    return _pool


async def close_pool():
    """Closes the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed.")
