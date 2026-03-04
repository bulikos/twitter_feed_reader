import aiohttp
import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple


from .auth import Account
from .requests import BaseRequest, RequestTimeline, RequestDetail
from .models import Tweet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    status_code: int
    duration_s: float
    size_bytes: int

class XClient:
    def __init__(self, account: Account):
        self.account = account
    def __init__(self, account: Account):
        self.account = account
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self.account.headers,
            cookies=self.account.cookies
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers=self.account.headers,
                cookies=self.account.cookies
            )

    async def _request(self, method: str, url: str, params: Dict[str, Any]) -> Tuple[Dict[str, Any], RequestMetrics]:
        await self._ensure_session()
        
        # Simple Retry Logic
        retries = 3
        for attempt in range(retries):
            try:
                start = time.monotonic()
                async with self.session.request(method, url, params=params) as response:
                    raw = await response.read()
                    duration_s = round(time.monotonic() - start, 3)
                    metrics = RequestMetrics(
                        status_code=response.status,
                        duration_s=duration_s,
                        size_bytes=len(raw),
                    )
                    logger.info(
                        f"Request {method} {url} | "
                        f"status={metrics.status_code} "
                        f"duration={metrics.duration_s}s "
                        f"size={metrics.size_bytes / 1024:.1f}kB"
                    )

                    if response.status == 429:
                        logger.warning("Rate limit exceeded. Waiting...")
                        await asyncio.sleep(5 * (attempt + 1))
                        continue

                    if response.status == 503:
                        logger.warning(f"Service unavailable (503). Waiting before retry (attempt {attempt + 1}/{retries})...")
                        await asyncio.sleep(10 * (attempt + 1))
                        continue
                        
                    response.raise_for_status()
                    return json.loads(raw), metrics
            except aiohttp.ClientError as e:
                logger.error(f"Request failed: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2)
        return {}, RequestMetrics(status_code=0, duration_s=0.0, size_bytes=0)

    async def fetch_timeline(self, request: RequestTimeline) -> Dict[str, Any]:
        url = f"https://x.com/i/api/graphql/{request.query_id}/{request.endpoint}"

        params = {
            "variables": json.dumps(request.get_variables()),
            "features": json.dumps(request.get_features())
        }

        data, _ = await self._request("GET", url, params)
        return data

    async def fetch_tweet_detail(self, request: RequestDetail) -> Dict[str, Any]:
        url = f"https://x.com/i/api/graphql/{request.query_id}/{request.endpoint}"

        params = {
            "variables": json.dumps(request.get_variables()),
            "features": json.dumps(request.get_features()),
            "fieldToggles": json.dumps(request.get_field_toggles())
        }

        data, _ = await self._request("GET", url, params)
        return data

