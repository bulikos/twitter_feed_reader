# x_sourcer

Async Python scraper that fetches tweets from X/Twitter's "Following" timeline via reverse-engineered GraphQL APIs. Tweets are stored in a shared PostgreSQL catalogue so multiple instances can run in parallel -- each with a different X account -- to maximise timeline coverage without redundant API calls.

## How it works

```
                   X/Twitter GraphQL API
                          |
                    HomeLatestTimeline
                          |
              +-----------+-----------+
              |                       |
         parse tweets            paginate (cursor)
              |
      store in PostgreSQL
              |
     identify detail candidates
     (skip if another instance
      already fetched within 72h)
              |
        TweetDetail API
              |
      store detail tweets
              |
         sleep & repeat
```

Each cycle the orchestrator:

1. Fetches the latest timeline page (with cursor-based pagination).
2. Parses tweets from Twitter's nested JSON response.
3. Stores timeline tweets immediately so other instances see them.
4. Identifies tweets that need full detail (quotes, articles, notes) -- skipping any already fetched within 72 hours by any instance.
5. Fetches and stores each detail individually.
6. Sleeps and repeats.

A background task deletes catalogue entries older than 30 days (runs hourly).

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)
- PostgreSQL (external, already running)
- X/Twitter account credentials (bearer token, CSRF token, auth token, guest ID)

## Setup

```bash
git clone <repo-url>
cd x_sourcer
uv sync
```

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

### Credentials

Credential env vars follow a naming convention -- the suffix must match `ACCOUNT_NAME`:

```
ACCOUNT_NAME="myaccount"

BEARER_TOKEN_myaccount="..."
CSRF_TOKEN_myaccount="..."
AUTH_TOKEN_myaccount="..."
GUEST_ID_myaccount="v1:..."
```

See `docs/KNOWLEDGE.md` for how to obtain these values from browser dev tools.

### Database

`DATABASE_URL` should contain the connection string **without** the `postgresql://` scheme prefix (it is added automatically):

```
DATABASE_URL="user:password@localhost:5432/dbname"
```

### Machine identity

`MACHINE_ID` identifies the host. Combined with `ACCOUNT_NAME` it forms the `source_instance` value stored with each tweet (`machine1-myaccount`).

## Running

### Local

```bash
python -m app.main
```

### Docker

```bash
docker compose up --build
```

Note: if your PostgreSQL is on the host machine, use `host.docker.internal` in `DATABASE_URL` instead of `localhost`.

### Multiple instances

Run separate containers (or processes) with different `MACHINE_ID` and `ACCOUNT_NAME` values, each pointing to the same PostgreSQL database. Instances coordinate through the shared catalogue -- detail fetches are deduplicated across all instances via a 72-hour lookback window.

## Project structure

```
app/
  main.py            Entry point. Inits PG pool, builds Catalogue, runs the loop.
  orchestrator.py    One cycle: fetch timeline -> parse -> store -> fetch details -> store.
  client.py          Async HTTP client (aiohttp). Handles retries, rate limits.
  catalogue.py       Stores List[Tweet] into PostgreSQL as JSONB via asyncpg.
  database.py        Connection pool management (init, get, close) and DDL.
  models.py          Tweet dataclass (14 fields).
  auth.py            Loads account credentials from env vars.
  requests.py        Request dataclasses (RequestTimeline, RequestDetail).
  parser/
    __init__.py      Package init, exposes parser functions.
    timeline.py      Parses HomeLatestTimeline responses.
    detail.py        Parses TweetDetail responses.
    item.py          Shared tweet-level parser (retweets, quotes, articles, notes).
docs/
  KNOWLEDGE.md       X API reverse-engineering notes (endpoints, auth, pagination).
```

## Configuration

| Variable | Description |
|---|---|
| `ACCOUNT_NAME` | X account name (must match credential suffixes) |
| `BEARER_TOKEN_{name}` | Bearer token for X API authentication |
| `CSRF_TOKEN_{name}` | CSRF token (x-csrf-token header) |
| `AUTH_TOKEN_{name}` | Auth token (auth_token cookie) |
| `GUEST_ID_{name}` | Guest ID (guest_id cookie) |
| `DATABASE_URL` | PostgreSQL connection string without scheme prefix |
| `MACHINE_ID` | Machine identifier for source_instance tracking |

See `.env.example` for a complete example.
