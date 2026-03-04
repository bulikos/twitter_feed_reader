import json
import logging
import time

import asyncpg

from .models import Tweet

logger = logging.getLogger(__name__)

INSERT_SQL = """
    INSERT INTO tweet_catalogue (tweet_id, tweet_data, machine_data)
    VALUES ($1, $2::jsonb, $3::jsonb)
"""


class Catalogue:
    """
    Catalogue backed by PostgreSQL (asyncpg).
    Stores tweets as JSONB blobs in a flexible schema:
      - id: auto-increment PK
      - tweet_id: the tweet's actual ID
      - tweet_data: all tweet fields as JSONB
      - machine_data: machine identifier and ingestion metadata as JSONB
    """

    def __init__(self, pool: asyncpg.Pool, source_instance: str):
        self.pool = pool
        self.source_instance = source_instance

    def _tweet_to_params(self, tweet: Tweet) -> tuple:
        tweet_data_json = json.dumps(tweet.to_dict())
        machine_data_json = json.dumps(
            {
                "source_instance": self.source_instance,
                "ingested_at": time.time(),
            }
        )
        return (tweet.id, tweet_data_json, machine_data_json)

    async def add_entries(self, tweets: list[Tweet]):
        if not tweets:
            logger.info("No entries to add")
            return

        rows = [self._tweet_to_params(t) for t in tweets]

        try:
            async with self.pool.acquire() as conn:
                await conn.executemany(INSERT_SQL, rows)
            logger.info("Inserted %d entries", len(rows))
        except Exception as e:
            logger.error("Error adding entries: %s", e, exc_info=True)

    async def has_detail(self, tweet_id: str) -> bool:
        """
        Check if a tweet already exists in the catalogue with tweet_source='detail',
        looking back only 72 hours. Used to skip redundant detail fetches across
        runs and instances.
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchval(
                    """
                    SELECT 1 FROM tweet_catalogue
                    WHERE tweet_id = $1
                      AND tweet_data->>'tweet_source' = 'detail'
                      AND created_at > NOW() - INTERVAL '72 hours'
                    LIMIT 1
                    """,
                    tweet_id,
                )
            return row is not None
        except Exception as e:
            logger.error("Error checking detail for %s: %s", tweet_id, e, exc_info=True)
            return False
