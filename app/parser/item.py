from typing import Dict, Any, List, Optional, Tuple
from dataclasses import field
import logging
import time

from ..models import Tweet

logger = logging.getLogger(__name__)

class ItemParser:
    def __init__(self):
        pass

    def parse_timestamp(self, date_str: Optional[str]) -> int:
        """Parses Twitter's created_at format: 'Sun Jan 25 17:01:51 +0000 2026'"""
        if not date_str:
            logger.debug("parse_timestamp: Empty date string provided.")
            return 0
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return int(dt.timestamp())
        except Exception as e:
            logger.debug(f"Failed to parse timestamp '{date_str}': {e}")
            return 0

    def extract_media(self, legacy: Dict[str, Any]) -> List[str]:
        media_urls = []
        if 'entities' in legacy and 'media' in legacy['entities']:
            for m in legacy['entities']['media']:
                if 'media_url_https' in m:
                    media_urls.append(m['media_url_https'])
        
        # Also check extended_entities which usually has variants for videos
        if 'extended_entities' in legacy and 'media' in legacy['extended_entities']:
             for m in legacy['extended_entities']['media']:
                if 'media_url_https' in m and m['media_url_https'] not in media_urls:
                     media_urls.append(m['media_url_https'])
        
        if media_urls:
            logger.debug(f"Extracted {len(media_urls)} media URLs")
        return media_urls

    def extract_text(self, result: Dict[str, Any], legacy: Dict[str, Any]) -> Tuple[str, bool]:
        """Returns (full_text, is_article)"""
        is_article = False
        
        # 1. Check for Article
        # Articles often reside in 'article' key inside user_results->result->legacy or similar? 
        # But based on article.json it seems: 
        # tweet_results.result.article.article_results.result
        if 'article' in result:
             if 'article_results' in result['article']:
                try:
                    art_res = result['article']['article_results']['result']
                    title = art_res.get('title', '')
                    
                    # Try to get full text from blocks
                    # TODO - support text formating (list items, bold, italic, media, ...)
                    # TODO - support nested tweets, i.e. links to other tweets
                    full_text_parts = []
                    if 'content_state' in art_res and 'blocks' in art_res['content_state']:
                        for block in art_res['content_state']['blocks']:
                             full_text_parts.append(block.get('text', ''))
                        full_content = "\n".join(full_text_parts)
                        if full_content.strip():
                             logger.debug("Detected Article content (full text)")
                             return full_content, True

                    preview = art_res.get('preview_text', '')
                    is_article = True
                    logger.debug("Detected Article content (preview only)")
                    return f"{title}\n{preview}", is_article
                except Exception as e:
                    logger.debug(f"Failed to extract Article content: {e}")
             else:
                 logger.debug("Found 'article' key but no 'article_results'")

        # 2. Check for Note Tweet (Long text)
        if 'note_tweet' in result:
             try:
                 note_res = result['note_tweet']['note_tweet_results']['result']
                 text = note_res.get('text', legacy.get('full_text', ''))
                 logger.debug("Detected Note Tweet (long text)")
                 return text, is_article
             except Exception as e:
                 logger.debug(f"Failed to extract Note Tweet content: {e}")
        
        # 3. Standard
        return legacy.get('full_text', ''), is_article

    def parse_tweet_result(self, result: Dict[str, Any], source: str = "timeline") -> List[Tweet]:
        """
        Parses a tweet result and returns a list of Tweet objects.
        The list includes the main tweet and any recursively parsed tweets (retweets, quotes).
        """
        received_ts = time.time()
        collected_tweets: List[Tweet] = []
        
        if not result: 
            logger.debug("parse_tweet_result called with empty result")
            return collected_tweets
        
        # 1. unwrapping 'tweet' wrapper if present
        if 'tweet' in result:
             result = result['tweet']
             
        # 2. Extract legacy and core
        legacy = result.get('legacy')
        core = result.get('core')
        
        # Handle Tombstones/Unavailable
        if not legacy:
            typename = result.get('__typename')
            if typename == 'TweetUnavailable':
                logger.debug(f"Skipping TweetUnavailable (reason: {result.get('reason', 'unknown')})")
                return collected_tweets
            elif typename == 'TweetTombstone':
                logger.debug("Skipping TweetTombstone")
                return collected_tweets
                
            logger.debug(f"Skipping tweet with no legacy data (typename: {typename})")
            return collected_tweets

        tid = legacy.get('id_str')
        logger.debug(f"Parsing tweet {tid} from source {source}")

        # 3. Build User Info
        user_handle = "unknown"
        user_name = "unknown"
        user_id = str(legacy.get('user_id_str', 'unknown'))
        
        if core:
            user_res = core.get('user_results', {}).get('result', {})
            
            # Helper to extract from a dict if keys exist
            def extract_from(obj):
                h = obj.get('screen_name')
                n = obj.get('name')
                return h, n

            # 1. Try 'core' (modern)
            if 'core' in user_res:
                h, n = extract_from(user_res['core'])
                if h: user_handle = h
                if n: user_name = n
                
            # 2. Try 'legacy' (if not found yet)
            if user_handle == "unknown" and 'legacy' in user_res:
                h, n = extract_from(user_res['legacy'])
                if h: user_handle = h
                if n: user_name = n
            
            # 3. Try direct (if weird wrapper)
            if user_handle == "unknown":
                h, n = extract_from(user_res)
                if h: user_handle = h
                if n: user_name = n
        else:
            logger.debug(f"No 'core' data found for tweet {tid}")

        if user_handle == "unknown":
            logger.warning(f"Failed to extract user handle for tweet {tid} (user_id: {user_id})")
        
        # Metadata extraction
        created_at_str = legacy.get('created_at')
        publish_timestamp = self.parse_timestamp(created_at_str)
        media_links = self.extract_media(legacy)
        
        # Text extraction (initially from this tweet)
        full_text, is_article = self.extract_text(result, legacy)

        # Metadata
        views_count = result.get('views', {}).get('count')
        
        metadata = {
            "views": views_count,
            "favorite_count": legacy.get('favorite_count'),
            "retweet_count": legacy.get('retweet_count'),
            "reply_count": legacy.get('reply_count'),
            "quote_count": legacy.get('quote_count'),
            "bookmark_count": legacy.get('bookmark_count'),
            "lang": legacy.get('lang'),
            "retweeted_status_id": None
        }
        
        # Determine Tags
        tags = []
        if is_article:
            tags.append("article")
        
        # Handle Retweets
        if 'retweeted_status_result' in legacy:
            rt_res = legacy['retweeted_status_result'].get('result')
            # Check if rt_res is valid before recursion
            if rt_res and rt_res.get('__typename') == 'Tweet':
                tags.append("retweet")
                # Recursively parse the ORIGINAL tweet
                logger.debug(f"Recursing into retweet content for tweet {tid}")
                rt_tweets = self.parse_tweet_result(rt_res, source="retweet")
                collected_tweets.extend(rt_tweets)
                
                # Find the tweet object we just parsed
                if rt_tweets:
                    # We expect the 'main' tweet of that batch to match the ID in the legacy info of rt_res
                    rt_id = rt_res.get('legacy', {}).get('id_str')
                    rt_tweet = next((t for t in rt_tweets if t.id == rt_id), None)
                    
                    # TODO Handle media from retweet, Why metadata['retweeted_status_id'] exist?

                    if rt_tweet:
                        metadata['retweeted_status_id'] = rt_tweet.id
                        # OVERRIDE text with the original tweet's text 
                        full_text = rt_tweet.text 
                else:
                    logger.debug(f"Retweet recursion returned no tweets for {tid}")
            else:
                logger.debug(f"Retweet status result missing or not 'Tweet' for {tid}")
        
        # Handle Quoted Tweets
        elif legacy.get('is_quote_status'):
            tags.append("quote")
        #elif legacy.get('in_reply_to_status_id_str'):
        #    tags.append("reply")
        else:
             # Default to tweet if not a retweet, quote, or reply
             if "retweet" not in tags:
                 tags.append("tweet")

        tweet = Tweet(
            id=tid,
            text=full_text,
            author_id=user_id,
            author_handle=user_handle,
            author_name=user_name,
            publish_timestamp=publish_timestamp,
            received_timestamp=received_ts,
            media=media_links,
            reply_to_id=legacy.get('in_reply_to_status_id_str'),
            quote_tweet_id=legacy.get('quoted_status_id_str'),
            retweet_tweet_id=metadata.get('retweeted_status_id'),
            tags=tags,
            tweet_source=source,
            metadata=metadata
        )
        
        collected_tweets.append(tweet)
        
        # 4. Handle Quoted Tweet Recursion (Top Level)
        if 'quoted_status_result' in result:
            quoted_res = result['quoted_status_result'].get('result')
            if quoted_res and quoted_res.get('__typename') == 'Tweet':
                # Just trigger parsing to and add to collected
                logger.debug(f"Recursing into quoted tweet content for tweet {tid}")
                quoted_tweets = self.parse_tweet_result(quoted_res, source="quote")
                collected_tweets.extend(quoted_tweets)
            else:
                 logger.debug(f"Quoted status result missing or not 'Tweet' for {tid}")
                
        return collected_tweets
