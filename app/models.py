from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import time

@dataclass
class Tweet:
    id: str
    text: str
    author_id: str
    author_handle: str
    author_name: str
    publish_timestamp: float = 0.0
    received_timestamp: float = field(default_factory=time.time)
    media: List[str] = field(default_factory=list)
    reply_to_id: Optional[str] = None
    quote_tweet_id: Optional[str] = None
    retweet_tweet_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    tweet_source: str = "timeline" # timeline, quote, detail
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    
    def pretty_print(self) -> str:
        date_str = datetime.fromtimestamp(self.publish_timestamp).strftime('%Y-%m-%d %H:%M:%S') if self.publish_timestamp else "N/A"
        lines = [
            f"[{self.id}] @{self.author_handle} ({self.author_name}) | {date_str}",
            f"{len(self.text)} {self.text.replace('\n', ' ')[:100]}{'...' if len(self.text) > 100 else ''}",
            f"Media: {len(self.media)} | Tags: {', '.join(self.tags)} | Source: {self.tweet_source}",
            f"ReplyTo: {self.reply_to_id} | Quote: {self.quote_tweet_id} | Retweet: {self.retweet_tweet_id}"
        ]
        return "\n".join(lines)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, Tweet):
            return False
        return self.id == other.id

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Tweet object to a dictionary."""
        from dataclasses import asdict
        return asdict(self)

    @staticmethod
    def to_df(tweets: List['Tweet']) -> Any:
        """Converts a list of Tweet objects to a pandas DataFrame."""
        try:
            import pandas as pd
            from dataclasses import fields
            if not tweets:
                # Return empty DataFrame with correct column names
                columns = [f.name for f in fields(Tweet)]
                return pd.DataFrame(columns=columns)
            return pd.DataFrame([t.to_dict() for t in tweets])
        except ImportError:
            # Fallback or error logging
            print("Error: pandas module not found. Please install with `pip install pandas`.")
            return None
