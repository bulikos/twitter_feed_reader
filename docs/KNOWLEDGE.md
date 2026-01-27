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
