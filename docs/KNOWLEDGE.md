# Twitter/X HomeTimeline Reverse Engineering

## Endpoints & Query IDs
Twitter uses GraphQL endpoints with specific Query IDs. These IDs change over time as the client definition evolves.

| Feed Type | Endpoint | Query ID (as of Jan 2026) | Description |
| :--- | :--- | :--- | :--- |
| **For You** | `HomeTimeline` | `GP_SvUI4lAFrt6UyEnkAGA` | Algorithmic "For You" timeline. |
| **Following** | `HomeLatestTimeline` | `HN6oP_7h7HayqyYimz97Iw` | "Following" timeline (Latest or Popular). |

## Authentication
Two critical components are required for successful authentication:

1.  **Cookies**:
    - `auth_token`: The main session token.
    - `ct0`: The CSRF token.
2.  **Headers**:
    - `authorization`: A static Bearer token used by the official web client.
    - `x-csrf-token`: **MUST** match the value of the `ct0` cookie.
    - `x-client-transaction-id`: A tracing header. While often dynamic, reusing a recent capture often works for short-term scripts.

## Request Variables
The `variables` JSON parameter controls the feed behavior.

### High-Level variables
- `count`: **Note**: The API often treats this as a loose suggestion or ignores it, commonly returning batches of ~20-40 items regardless of the value set here.
- `includePromotedContent`: Boolean to include ads.
- `withCommunity`: (For You) Includes community tweets.

### Ranking & Sort Order
Controlled by the `enableRanking` variable in the `HomeLatestTimeline` endpoint:
- `true`: **Popular** tweets first (Top).
- `false`: **Latest** tweets (Chronological).

### Pagination
Pagination is handled via the `cursor` variable.
1.  **Initial Request**: `requestContext` should be set to `"launch"`.
2.  **Subsequent Request**:
    - Set `requestContext` to `"ptr"` (Pull-to-Refresh) or omit it.
    - Set `cursor` to the value extracted from the previous response.
    - **Extraction**: Look for an entry with `entryId: "cursor-bottom-..."` in the `TimelineAddEntries` instruction and get its `content.value`.

### Anti-Duplication
- `seenTweetIds`: A list of Tweet IDs sent in the request to prevent the server from resending tweets the client already has.

## Response Structure
The response is a deeply nested JSON structure:
`data` -> `home` -> `home_timeline_urt` (or `home_latest_timeline_urt`) -> `instructions`

- **Tweets**: Found in `TimelineAddEntries` -> `entries` -> `content.itemContent.tweet_results.result`.
- **Cursors**: Found in `TimelineAddEntries` -> `entries` (entryId starting with `cursor-bottom-`).

## Anti-Duplication via seenTweetIds

The `seenTweetIds` variable in the request body is a list of tweet IDs already seen by the client.
Sending it prevents X from returning those tweets again in the response.

**Benefits:**
- Smaller response payloads (fewer bytes to download)
- Faster download time (measurable ~0.1–0.2s reduction)
- Cleaner responses — no need to filter already-processed tweets on the client side

**Implementation:** Maintain a rolling set of recently seen tweet IDs. Append to the `variables` dict before each request:
```python
variables["seenTweetIds"] = list(seen_ids)  # list of id strings
```
Keep the set bounded (e.g. last 200 IDs) to avoid bloating request size.

## Geographic Proximity (Latency Reduction)

X's API servers are primarily located in **US East (Ashburn, VA)** and **US West (Oregon/California)**.

Running the scraper on a cloud instance in the same region reduces round-trip download time:

| Server location | Typical download time |
|---|---|
| Europe (current) | ~0.3–0.6s |
| US East (Ashburn) | ~0.05–0.15s |
| US West | ~0.08–0.20s |

Savings of ~0.2–0.4s per request — small in absolute terms but meaningful at sub-5s total latency targets.
Recommended: AWS `us-east-1` (N. Virginia) or `us-west-2` (Oregon).

## X Browser Real-Time Mechanism — SSE, not WebSocket

**Verified March 2026:** X.com does NOT use WebSockets (`wss://`) for real-time timeline updates.
Chrome DevTools → Network → WS filter shows zero connections.

X uses **Server-Sent Events (SSE)** — visible in DevTools as:
- A long-lived `(pending)` HTTP request under `Network → Other`
- `Content-Type: text/event-stream`

**How it works:**
1. Browser holds an open SSE connection to X
2. X pushes a lightweight "new tweets available" signal when they appear
3. Browser fires a normal `HomeLatestTimeline` GraphQL poll in response

**Implication for scraping:** The SSE is just a wake-up signal — it doesn't carry tweet content.
The actual data comes from the same `HomeLatestTimeline` endpoint we already use.

**Optimal scraping strategy (in order of ROI):**

| Approach | Complexity | Avg detection improvement |
|---|---|---|
| Reduce polling 30s → 5s | Trivial | −12.5s |
| Multiple accounts × N, time-offset | Low | scales linearly |
| Replicate SSE wake-up signal | High, brittle | −2s marginal |

Replicating SSE is high maintenance for marginal gain. Multiple accounts + tight polling is the pragmatic path.
