import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from ..models import Tweet
from .item import ItemParser

logger = logging.getLogger(__name__)

@dataclass
class DetailStats:
    total_entries: int = 0
    entries_tweet: int = 0
    entries_module: int = 0
    items_from_module: int = 0
    total_items_loaded: int = 0
    parse_duration_s: float = 0.0

class DetailParser:
    def __init__(self):
        self.item_parser = ItemParser()
        self.stats = DetailStats()

    def parse(self, data: Dict[str, Any], focal_id: str) -> List[Tweet]:
        start_time = time.time()
        tweets = []
        try:
            root = data.get('data', {}).get('threaded_conversation_with_injections_v2', {})
            instructions = root.get('instructions', [])
            logger.debug(f"Starting DetailParser.parse | Instructions found: {len(instructions)}")
            
            for instruction in instructions:
                inst_type = instruction.get('type')
                entries = []
                
                if inst_type == 'TimelineAddEntries':
                    entries = instruction['entries']
                    logger.debug(f"Processing TimelineAddEntries | Count: {len(entries)}")
                elif inst_type == 'TimelineAddToModule':
                    entries = instruction['moduleItems']
                    logger.debug(f"Processing TimelineAddToModule | Count: {len(entries)}")
                else:
                    logger.debug(f"Skipping instruction type: {inst_type}")
                
                for entry in entries:
                    self.stats.total_entries += 1
                    # entryId is often helpful for debugging specific items
                    eid = entry.get('entryId', 'unknown')
                    logger.debug(f"Processing entry: {eid}")
                    
                    new_tweets = self._parse_entry(entry, focal_id)
                    if new_tweets:
                        logger.debug(f"Extracted {len(new_tweets)} tweets from entry {eid}")
                    tweets.extend(new_tweets)
                        
        except Exception as e:
            logger.error(f"Error parsing detail: {e}", exc_info=True)
        
        duration = round(time.time() - start_time, 5)
        self.stats.parse_duration_s = duration
        logger.info(f"DetailParser finished | Tweets: {len(tweets)} | Duration: {duration}s | Stats: {self.stats}")
        return tweets

    def _parse_entry(self, entry: Dict[str, Any], focal_id: str) -> List[Tweet]:
        """
        Parses a single entry from the timeline instructions.
        Entries can be:
        1. 'item' -> usually inside a module (TimelineAddToModule)
        2. 'content' -> standard timeline entry (TimelineAddEntries)
           - Can be a single tweet result
           - Can be a TimelineTimelineModule containing multiple items
        """
        tweets = []
        content = None
        
        # Case 1: Module Item (likely from TimelineAddToModule)
        # Structure: entry -> item -> itemContent -> ...
        if 'item' in entry: 
             item_type = entry['item'].get('itemContent', {}).get('itemType')
             if item_type == 'TimelineTweet':
                 logger.debug("  -> Found TimelineTweet in module item")
                 content = entry['item']['itemContent']['tweet_results']['result']
             else:
                 logger.debug(f"  -> Skipping module item type: {item_type}")

        # Case 2: Standard Entry (likely from TimelineAddEntries)
        # Structure: entry -> content -> ...
        elif 'content' in entry: 
             entry_type = entry['content'].get('entryType')
             
             # Sub-case 2.1: TimelineModule (Thread/Conversation)
             if entry_type == 'TimelineTimelineModule':
                 self.stats.entries_module += 1
                 items = entry['content'].get('items', [])
                 logger.debug(f"  -> Found TimelineTimelineModule | Items: {len(items)}")
                 
                 for item in items:
                     if item.get('item', {}).get('itemContent', {}).get('itemType') == 'TimelineTweet':
                         c = item['item']['itemContent']['tweet_results']['result']
                         # We use regular parse_tweet_result from item parser here
                         t_list = self.item_parser.parse_tweet_result(c, source="detail")
                         self.stats.items_from_module += len(t_list)
                         tweets.extend(t_list)
                 
                 self.stats.total_items_loaded += len(tweets)
                 # Return immediately as we handled the module items loop
                 return tweets

             # Sub-case 2.2: Single Tweet item
             elif entry['content'].get('itemContent', {}).get('tweet_results'):
                 self.stats.entries_tweet += 1
                 logger.debug("  -> Found standard Single Tweet entry")
                 content = entry['content']['itemContent']['tweet_results']['result']
             
             else:
                 logger.debug(f"  -> Unhandled entry content type: {entry_type}")
        
        # If we extracted 'content' (the tweet result), parse it now
        if content:
            t_list = self.item_parser.parse_tweet_result(content, source="detail")
            self.stats.total_items_loaded += len(t_list)
            
            # If it came from 'item', it counts towards items_from_module for stats purposes
            if 'item' in entry:
                 self.stats.items_from_module += len(t_list)
            
            tweets.extend(t_list)
            
        return tweets
