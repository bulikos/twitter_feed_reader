import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass
class Account:
    username: str
    bearer_token: str
    csrf_token: str
    auth_token: str
    guest_id: str

    @property
    def headers(self) -> dict[str, str]:
        # Using a fixed transaction ID for now, or could generate dynamic
        transaction_id = "vskJBlMoqtAmJzTKldvzYgeFc/pdO7uqPVydcXPSd9TfSn+idNvXx8ht8wgIF++4TW7Hn7v3nytlgjV8fyGLe14OMDWvvQ"

        return {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,cs;q=0.7",
            "authorization": f"Bearer {self.bearer_token}",
            "content-type": "application/json",
            "priority": "u=1, i",
            "referer": "https://x.com/home",
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "x-client-transaction-id": transaction_id,
            "x-csrf-token": self.csrf_token,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
        }

    @property
    def cookies(self) -> dict[str, str]:
        return {
            "dnt": "1",
            "twtr_pixel_opt_in": "Y",
            "lang": "en",
            "auth_token": self.auth_token,
            "ct0": self.csrf_token,
            "guest_id": self.guest_id,
        }

def load_account(username: str) -> Account:
    """Loads account credentials from environment variables for a specific user."""
    suffix = f"_{username.lower()}"
    return Account(
        username=username,
        bearer_token=os.getenv(f"BEARER_TOKEN{suffix}", ""),
        csrf_token=os.getenv(f"CSRF_TOKEN{suffix}", ""),
        auth_token=os.getenv(f"AUTH_TOKEN{suffix}", ""),
        guest_id=os.getenv(f"GUEST_ID{suffix}", "")
    )


