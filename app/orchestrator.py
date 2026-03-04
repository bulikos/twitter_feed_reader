import asyncio
import logging

from .catalogue import Catalogue
from .client import XClient
from .models import Tweet
from .parser.detail import DetailParser
from .parser.timeline import TimelineParser
from .requests import RequestDetail, RequestTimeline

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, client: XClient, catalogue: Catalogue):
        self.client = client
        self.cursor = ""
        self.catalogue = catalogue

    def _identify_detail_candidates(self, tweets: list[Tweet]) -> set[str]:
        """
        Find tweets that need a detail API call:
        - Reply parents not present in the current batch (we need the original tweet for context)
        - Tweets tagged 'article' (detail endpoint returns full article text)
        """
        tweet_ids = {t.id for t in tweets}
        candidates: set[str] = set()

        for t in tweets:
            # If this tweet is a reply and the parent wasn't in the batch,
            # we need to fetch the parent separately
            if t.reply_to_id and t.reply_to_id not in tweet_ids:
                candidates.add(t.reply_to_id)

            # Articles are truncated on timeline; detail endpoint has full text
            if "article" in t.tags:
                candidates.add(t.id)

        reply_count = sum(1 for t in tweets if t.reply_to_id)
        article_count = sum(1 for t in tweets if "article" in t.tags)
        logger.info(
            "Detail candidates: %d (%d replies in batch, %d articles)",
            len(candidates),
            reply_count,
            article_count,
        )
        return candidates

    async def _fetch_details(self, candidates: set[str]) -> None:
        """
        For each candidate, check the shared catalogue (72h lookback) to avoid
        redundant fetches across instances, then fetch and store immediately.
        """
        skipped = 0
        fetched = 0

        for tweet_id in candidates:
            # Another instance (or earlier cycle) may have already fetched this
            if await self.catalogue.has_detail(tweet_id):
                skipped += 1
                continue

            logger.info("Fetching detail for %s", tweet_id)
            req = RequestDetail(focal_tweet_id=tweet_id)
            data = await self.client.fetch_tweet_detail(req)

            # Parse and store immediately so other instances see it
            dp = DetailParser()
            detail_tweets = dp.parse(data, tweet_id)
            if detail_tweets:
                await self.catalogue.add_entries(detail_tweets)

            fetched += 1

            # Rate-limit: space out detail requests
            await asyncio.sleep(3)

        logger.info("Details done: %d fetched, %d skipped", fetched, skipped)

    async def process_timeline(self) -> None:
        """
        One cycle: fetch timeline -> parse -> store -> fetch missing details.
        Called repeatedly by the main loop.
        """
        req = RequestTimeline(feed_type="following", cursor=self.cursor)
        logger.info("Fetching timeline (cursor: %s)", self.cursor or "initial")
        data = await self.client.fetch_timeline(req)

        # Parser is created fresh each call (it accumulates stats per parse)
        tp = TimelineParser()
        tweets, cursor = tp.parse(data)

        # Always advance cursor, even if no tweets were parsed --
        # otherwise we'd re-fetch the same empty page forever
        self.cursor = cursor

        logger.info("Parsed %d tweets | stats: %s", len(tweets), tp.stats)

        if not tweets:
            return

        # Store timeline tweets immediately so other instances can skip duplicates
        await self.catalogue.add_entries(tweets)

        # Fetch detail for tweets that need it (reply parents, articles)
        candidates = self._identify_detail_candidates(tweets)
        if candidates:
            await self._fetch_details(candidates)
