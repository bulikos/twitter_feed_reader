import asyncio
import logging
import sys
import os

from .client import XClient
from .auth import load_account
from .orchestrator import Orchestrator
from .catalogue import Catalogue
from .article_generator import ArticleGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_orchestrator_loop():
    """
    Runs the orchestrator in a never-ending loop.
    """
    logger.info("Starting Orchestrator Loop...")
    
    # 1. Instantiate services
    # We use a context manager for the client if possible to ensure session cleanup, 
    # but since it's an infinite loop, we might want to manage the session manually 
    # or just keep the client open.
    # The XClient supports async context manager.
    
    # Initialize our simple components
    catalogue = Catalogue()
    article_generator = ArticleGenerator()

    # Determine user from env or default
    account = load_account("pussy")

    async with XClient(account) as client:
        # 2. Instantiate Orchestrator
        orchestrator = Orchestrator(
            client=client, 
            catalogue=catalogue, 
            article_generator=article_generator
        )

        logger.info("Orchestrator initialized. Entering loop.")
        
        while True:
            try:
                logger.info(">>> Starting new timeline processing cycle...")
                
                # Fetch and process timeline
                # process_timeline returns (df_timeline, df_additional)
                # but it also handles the staging internally now based on your recent changes.
                await orchestrator.process_timeline()
                
                logger.info("<<< cycle completed.")
                
                # Wait for some time before next iteration
                # Let's say 120 seconds or custom
                wait_seconds = 120
                logger.info(f"Sleeping for {wait_seconds} seconds...")
                await asyncio.sleep(wait_seconds)
                
            except Exception as e:
                logger.error(f"Error in orchestrator loop: {e}", exc_info=True)
                logger.info("Waiting 120 seconds before retrying...")
                await asyncio.sleep(120)

def main():
    try:
        asyncio.run(run_orchestrator_loop())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")

if __name__ == "__main__":
    main()
