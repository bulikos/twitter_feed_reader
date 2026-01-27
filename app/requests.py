import json
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class BaseRequest:
    endpoint: str = ""
    query_id: str = ""
    
    def get_variables(self) -> Dict[str, Any]:
        return {}
        
    def get_features(self) -> Dict[str, Any]:
        # Common features found in latest captures
        return {
            "rweb_video_screen_enabled": False,
            "profile_label_improvements_pcf_label_in_post_enabled": True,
            "responsive_web_profile_redirect_enabled": False,
            "rweb_tipjar_consumption_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "premium_content_api_read_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
            "responsive_web_grok_analyze_post_followups_enabled": True,
            "responsive_web_jetfuel_frame": True,
            "responsive_web_grok_share_attachment_enabled": True,
            "responsive_web_grok_annotations_enabled": False,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "responsive_web_grok_show_grok_translated_post": False,
            "responsive_web_grok_analysis_button_from_backend": True,
            "post_ctas_fetch_enabled": True,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_grok_image_annotation_enabled": True,
            "responsive_web_grok_imagine_annotation_enabled": True,
            "responsive_web_grok_community_note_auto_translation_is_enabled": False,
            "responsive_web_enhance_cards_enabled": False
        }

@dataclass
class RequestTimeline(BaseRequest):
    feed_type: str = "for_you"
    cursor: Optional[str] = None
    ranking: bool = False
    
    def __post_init__(self):
        if self.feed_type == "for_you":
            self.query_id = "GP_SvUI4lAFrt6UyEnkAGA" 
            self.endpoint = "HomeTimeline"
        elif self.feed_type == "following":
            self.query_id = "HN6oP_7h7HayqyYimz97Iw"
            self.endpoint = "HomeLatestTimeline"
    
    def get_variables(self) -> Dict[str, Any]:
        variables = {
            "count": 20,
            "includePromotedContent": True,
            "requestContext": "launch" if not self.cursor else "ptr",
        }
        
        if self.feed_type == "for_you":
            variables["withCommunity"] = True
        elif self.feed_type == "following":
             variables["enableRanking"] = self.ranking
             
        if self.cursor:
            variables["cursor"] = self.cursor
            
        return variables

@dataclass
class RequestDetail(BaseRequest):
    focal_tweet_id: str = ""
    cursor: Optional[str] = None
    
    def __post_init__(self):
        self.query_id = "nK2WM0mHJKd2-jb6qhmfWA"
        self.endpoint = "TweetDetail"
        
    def get_variables(self) -> Dict[str, Any]:
        return {
            "focalTweetId": self.focal_tweet_id,
            "with_rux_injections": False,
            "rankingMode": "Relevance",
            "includePromotedContent": True,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
            # Cursor support for conversation threads if needed, 
            # though usually handled by separate 'cursor' instruction logic not variable?
            # Actually TweetDetail variables usually don't take a standard pagination cursor 
            # in the same way, but let's keep it extensible.
            # "cursor": self.cursor 
        }

    def get_field_toggles(self) -> Dict[str, Any]:
        return {
            "withArticleRichContentState": True,
            "withArticlePlainText": False,
            "withGrokAnalyze": False,
            "withDisallowedReplyControls": False
        }
