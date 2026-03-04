import asyncio
import logging
import pandas as pd
from typing import Tuple, List, Optional

from .client import XClient
from .requests import RequestTimeline, RequestDetail
from .parser.timeline import TimelineParser
from .parser.detail import DetailParser
from .models import Tweet
from .article_generator import ArticleGenerator
from .catalogue import Catalogue

logger = logging.getLogger(__name__)

class Orchestrator:

    def __init__(self, client: XClient, article_generator: ArticleGenerator, catalogue: Catalogue):
        self.client = client
        self.cursor = ""

        # Other services
        self.article_generator = article_generator
        self.catalogue = catalogue

    def _identify_detail_candidates(self, df_timeline: pd.DataFrame) -> pd.DataFrame:
        """
        Analyses the timeline to identify tweets that require detailed data fetching.

        This method checks for:
        1. Missing parent tweets for replies found in the timeline.
        2. Tweets tagged as articles which require full text extraction.

        Args:
            df_timeline (pd.DataFrame): DataFrame containing timeline tweets.

        Returns:
            pd.DataFrame: A DataFrame with columns ['id', 'reason'] containing candidates for detailed fetching.
        """
        # Check replies
        if 'reply_to_id' in df_timeline.columns:
            replies = df_timeline['reply_to_id'].dropna().values
            logger.info(f"Total replies found in batch: {len(replies)}")
            
            if len(replies) > 0:
                # Safe way using pandas directly:
                # missing_replies = replies[~pd.Series(replies).isin(df_timeline['id'])]
                # But 'replies' is numpy array.
                
                # Re-implementing user logic with pandas safer constructs because numpy might not be imported explicitly as np
                replies_series = pd.Series(replies)
                missing_replies = replies_series[~replies_series.isin(df_timeline['id'])].values
            else:
                missing_replies = []
        else:
            logger.info("No 'reply_to_id' column in dataframe")
            missing_replies = []
            
        logger.info(f"Missing replies count: {len(missing_replies)}")
        
        # Check articles
        if 'tags' in df_timeline.columns:
            # Handle list column for string search
            # tags is a list of strings, astype(str) converts it to string representation of list
            articles = df_timeline[df_timeline['tags'].astype(str).str.contains('article', na=False)]['id'].values
        else:
            articles = []
            
        logger.info(f"Total articles found: {len(articles)}")

        # Construct candidates DataFrame
        candidates_list = []
        
        # Reason - article_detail
        if len(articles) > 0:
            df_articles = pd.DataFrame({
                'id': articles,
                'reason': 'article_detail'
            })
            candidates_list.append(df_articles)
            
        # Reason - reply
        if len(missing_replies) > 0:
            df_replies = pd.DataFrame({
                'id': missing_replies,
                'reason': 'missing_reply'
            })
            candidates_list.append(df_replies)
            
        if candidates_list:
            candidates_for_additional_data = pd.concat(candidates_list, ignore_index=True)
        else:
            candidates_for_additional_data = pd.DataFrame(columns=['id', 'reason'])

        if candidates_for_additional_data.empty:
            return candidates_for_additional_data


        ## Remove duplicates

        # 1. Drop exact duplicates (same id, same reason)
        candidates_for_additional_data = candidates_for_additional_data.drop_duplicates()

        # 2. Merge reasons for same id
        #    If an ID has multiple reasons (e.g. 'article_detail' AND 'missing_reply'), 
        #    merge them into one string "article_detail, missing_reply"
        candidates_for_additional_data = candidates_for_additional_data.groupby('id', as_index=False).agg({
            'reason': lambda x: ', '.join(sorted(x.unique()))
        })

        return candidates_for_additional_data

    async def process_timeline(self) -> Tuple[pd.DataFrame, pd.DataFrame]:

        #
        # A. Request API for data
        # 

        # Prepare request
        req = RequestTimeline(feed_type="following", cursor=self.cursor)

        # Send request
        logger.info(f"Requesting timeline with cursor: {self.cursor}")
        data = await self.client.fetch_timeline(req)

        #
        # B. Parse data
        #

        # Initialize Parser
        tp = TimelineParser()
        tweets, cursor = tp.parse(data)

        # TODO Better stats
        logger.info(f"Parser stats: {tp.stats}")
        logger.info(f"Downloaded {len(tweets)} tweets")
        logger.info(f"New Cursor: {cursor}")

        # Prepare df_timeline
        df_timeline = Tweet.to_df(tweets)
             
        if df_timeline.shape[0] == 0:
             logger.warning("No tweets found in batch")

        #
        # C. Read tweets and prepare requests for additional reads
        # 

        candidates_for_additional_data = self._identify_detail_candidates(df_timeline)

        # 
        # D. Process additional request
        #

        all_add_tweets = []
        
        logger.info(f"Processing {len(candidates_for_additional_data)} additional requests")

        for i, row in candidates_for_additional_data.iterrows():

            # TODO Improvement access catalogue to check if we already have this tweet (at all) or article (in detail).

            logger.debug(f"Processing candidate {i}/{len(candidates_for_additional_data)}: {row['id']} ({row['reason']})")
        
            # Call for detail
            req_add = RequestDetail(focal_tweet_id=row['id'])
            add_data = await self.client.fetch_tweet_detail(req_add)
        
            # Parse detail
            dp = DetailParser()
            add_tweets = dp.parse(add_data, row['id'])
        
            # Store
            all_add_tweets.extend(add_tweets)
        
            await asyncio.sleep(3)
        
        # Convert additional tweets to dicts using to_d()
        df_all_add_tweets = Tweet.to_df(all_add_tweets)

        #
        # E. Finish
        #
        
        # Update cursor
        self.cursor = cursor

        # Send df_timeline and df_all_add_tweets to Catalogue, there will be merged with other articles and stored.
        self.catalogue.add_entries(df_timeline)
        self.catalogue.add_entries(df_all_add_tweets)

        # Remember which tweets we have seen directly on timeline (not quotes, or tweets loaded in detail)
        main_tweets_on_timeline = df_timeline[df_timeline['tweet_source'].isin(['timeline','timeline_conversation'])][['id']].copy()
        main_tweets_on_timeline['read_id'] = 'test'
        self.article_generator.add_entries(main_tweets_on_timeline)
    