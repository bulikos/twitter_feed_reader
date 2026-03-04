# AGENTS.md

Project context for AI coding assistants working on this codebase.

## Project overview

Async Python 3.13 scraper that fetches tweets from X/Twitter's "Following" timeline via reverse-engineered GraphQL APIs. Tweets are stored in a shared PostgreSQL catalogue (JSONB schema) so multiple instances can run in parallel without redundant work.

## Architecture

```
main.py           Entry point. Inits PG pool, builds Catalogue, runs the loop.
  orchestrator.py  One cycle: fetch timeline -> parse -> store -> fetch details -> store.
    client.py      Async HTTP client (aiohttp). Handles retries, rate limits.
    parser/        Extracts Tweet objects from Twitter's nested JSON responses.
      timeline.py  Parses HomeLatestTimeline responses.
      detail.py    Parses TweetDetail responses.
      item.py      Shared tweet-level parser (handles retweets, quotes, articles, notes).
    catalogue.py   Stores List[Tweet] into PostgreSQL as JSONB via asyncpg.
  database.py      Connection pool management (init, get, close) and DDL.
models.py          Tweet dataclass (14 fields).
auth.py            Loads account credentials from env vars.
requests.py        Request dataclasses (RequestTimeline, RequestDetail) with GraphQL variables/features.
```

## Key conventions

### Logging
- Single `logging.basicConfig()` in `main.py`. No other file configures the root logger.
- All log calls use lazy `%`-formatting: `logger.info("Got %d tweets", count)`.
- Never use f-strings in log calls (`logger.info(f"...")` is wrong).
- All `logger.error()` calls that catch exceptions include `exc_info=True`.

### Data flow
- The main pipeline passes `List[Tweet]` objects directly. No pandas DataFrames in the orchestrator or catalogue.
- `Tweet.to_df()` exists in `models.py` but is not used in the main pipeline.
- Catalogue stores each tweet as three columns: `tweet_id` (TEXT), `tweet_data` (JSONB with all tweet fields), `machine_data` (JSONB with source_instance and ingested_at).

### Multi-instance
- N instances share one PostgreSQL database. No unique constraint on `tweet_id` -- duplicates are allowed and rare.
- Before fetching a tweet's detail, the orchestrator checks `catalogue.has_detail(tweet_id)` with a 72-hour lookback window to avoid redundant API calls across instances.
- Timeline tweets are stored immediately after parsing (before detail work) so other instances see them as soon as possible.
- A background task deletes catalogue entries older than 30 days (runs hourly).

### Environment variables
- Credentials follow a naming convention: `BEARER_TOKEN_{name}`, `CSRF_TOKEN_{name}`, `AUTH_TOKEN_{name}`, `GUEST_ID_{name}` where `{name}` matches `ACCOUNT_NAME`.
- `DATABASE_URL` does not include the `postgresql://` scheme prefix -- `database.py:_build_dsn()` adds it automatically.
- `MACHINE_ID` identifies the machine; `source_instance` is `{MACHINE_ID}-{ACCOUNT_NAME}`.
- See `.env.example` for all required variables.

## Known quirks

- **Pre-existing LSP errors** in `client.py` (duplicate `__init__`, `self.session` type) and `scripts/verify_*.py` (stale `XParser` import). These are not bugs and should be ignored.
- **`host.docker.internal`** in `DATABASE_URL` only resolves inside Docker containers. Use `localhost` for local development.
- **Parser internals** handle Twitter's deeply nested and inconsistent JSON. Don't simplify parser logic without testing against real API payloads.

## Reference

- `docs/KNOWLEDGE.md` -- detailed X API reverse-engineering notes (endpoints, auth, pagination, response structure).
- `.env.example` -- all required environment variables with descriptions.
