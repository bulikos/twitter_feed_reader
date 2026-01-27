import logging
import time

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from ..models import Tweet
from .item import ItemParser

logger = logging.getLogger(__name__)

@dataclass
class TimelineStats:
    total_entries: int = 0
    entries_tweet: int = 0
    entries_module: int = 0
    entries_cursor: int = 0
    items_from_module: int = 0
    total_items_loaded: int = 0
    parse_duration_s: float = 0.0

class TimelineParser:
    def __init__(self):
        self.item_parser = ItemParser()
        self.stats = TimelineStats()

    def parse(self, data: Dict[str, Any]) -> Tuple[List[Tweet], Optional[str]]:
        start_time = time.time()
        tweets: List[Tweet] = []
        next_cursor: Optional[str] = None
        
        try:
            instructions = self._extract_instructions(data)
            if not instructions:
                logger.warning("No instructions found in timeline response")
                return [], None
            
            for instruction in instructions:
                type_ = instruction.get('type')
                if type_ == 'TimelineAddEntries':
                    for entry in instruction['entries']:
                        new_tweets, cursor = self._parse_entry(entry)
                        tweets.extend(new_tweets)
                        if cursor:
                            next_cursor = cursor
                            
        except Exception as e:
            logger.error(f"Error parsing timeline: {e}")
            
        self.stats.parse_duration_s = round(time.time() - start_time, 5)
        return tweets, next_cursor

    def _extract_instructions(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        home = data.get('data', {}).get('home', {})
        # Dynamic key lookup for "timeline_urt"
        timeline_key = next((k for k in home.keys() if k.endswith('timeline_urt')), None)
        if timeline_key:
            return home[timeline_key].get('instructions', [])
        return []

    def _parse_entry(self, entry: Dict[str, Any]) -> Tuple[List[Tweet], Optional[str]]:
        """Parses a single entry (Tweet, Module, or Cursor) and returns tweets and/or cursor."""
        entry_id = entry.get('entryId', '')
        tweets = []
        cursor = None
        
        self.stats.total_entries += 1

        try:
            # 1. Standard Tweet
            if entry_id.startswith('tweet-'):
                self.stats.entries_tweet += 1
                content = entry['content']['itemContent']['tweet_results']['result']
                tweets = self.item_parser.parse_tweet_result(content, source="timeline")
                self.stats.total_items_loaded += len(tweets)
            
            # 2. Thread / Conversation Module
            elif entry.get('content', {}).get('entryType') == 'TimelineTimelineModule':
                self.stats.entries_module += 1
                
                items = entry['content']['items']
                for item in items:
                    if item['item']['itemContent']['itemType'] == 'TimelineTweet':
                        content = item['item']['itemContent']['tweet_results']['result']
                        # We parse strictly for extraction
                        mod_tweets = self.item_parser.parse_tweet_result(content, source="timeline_conversation")
                        tweets.extend(mod_tweets)
                        self.stats.items_from_module += len(mod_tweets)
                        self.stats.total_items_loaded += len(mod_tweets)
            
            # 3. Cursor
            elif entry_id.startswith('cursor-bottom-'):
                self.stats.entries_cursor += 1
                # Ignore bottom cursor, we don't need it
                #cursor = entry['content']['value']

            # 4. Cursor
            elif entry_id.startswith('cursor-top-'):
                self.stats.entries_cursor += 1
                cursor = entry['content']['value']
            
            # 5. Else
            else:
                logger.debug(f"Unhandled entry: {entry_id} Type: {entry.get('content', {}).get('entryType')}")

        except Exception as e:
            logger.debug(f"Failed to parse entry {entry_id}: {e}")
            pass
            
        return tweets, cursor