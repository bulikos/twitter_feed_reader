import asyncio
import logging
import os

from .auth import load_account
from .catalogue import Catalogue
from .client import XClient
from .database import close_pool, init_pool
from .orchestrator import Orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def cleanup_old_data(pool):
    """
    Periodically deletes catalogue entries older than 30 days.
    Runs every hour.
    """
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            async with pool.acquire() as conn:
                result = await conn.execute("DELETE FROM tweet_catalogue WHERE created_at < NOW() - INTERVAL '30 days'")
                # result is a string like "DELETE 42"
                deleted_count = result.split(" ")[-1]
                logger.info("Cleanup: deleted %s entries older than 30 days", deleted_count)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Cleanup error: %s", e, exc_info=True)
            # Continue the loop even on error


async def run_orchestrator_loop():
    """
    Runs the orchestrator in a never-ending loop.
    """
    # 1. Initialize PostgreSQL pool
    pool = await init_pool()

    # 2. Build source_instance identifier: {MACHINE_ID}-{account_name}
    account_name = os.environ.get("ACCOUNT_NAME", "").strip().strip("'\"")
    if not account_name:
        raise ValueError("ACCOUNT_NAME environment variable is not set")
    machine_id = os.environ.get("MACHINE_ID", "unknown").strip().strip("'\"")
    source_instance = f"{machine_id}-{account_name}"
    logger.info("Starting orchestrator (instance: %s)", source_instance)

    # 3. Initialize services
    catalogue = Catalogue(pool=pool, source_instance=source_instance)

    # 4. Load account credentials
    account = load_account(account_name)

    # 5. Start cleanup background task
    cleanup_task = asyncio.create_task(cleanup_old_data(pool))

    try:
        async with XClient(account) as client:
            orchestrator = Orchestrator(client=client, catalogue=catalogue)

            while True:
                try:
                    await orchestrator.process_timeline()
                    await asyncio.sleep(30)

                except Exception as e:
                    logger.error("Error in orchestrator loop: %s", e, exc_info=True)
                    await asyncio.sleep(120)
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await close_pool()
        logger.info("Shutdown complete.")


def main():
    try:
        asyncio.run(run_orchestrator_loop())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")


if __name__ == "__main__":
    main()
