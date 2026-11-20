# Member 1 Guide: Crawl and Data Provenance

## Project in one minute

The team is building a review-aware game recommendation system. We want to learn whether opinions extracted from game reviews improve recommendations based on links between users and games. The capstone combines a reproducible data-collection system with an evaluated method. Information Retrieval is out of scope; the course connections are link analysis and opinion mining, with LightGCN as the learned recommender.

Your role is to collect a bounded, auditable review sample from one platform across multiple games. Do not crawl multiple platforms or attempt to copy all of Steam.

## What already exists

- `../../steam_pilot.jsonl`: 200 recent English reviews from five Steam games.
- `../../steam_pilot_manifest.json`: request settings and crawl counts.
- `../../README.md`: full project plan and the pilot's limitations.

The pilot has 200 unique reviews and 199 unique hashed reviewers, but only one reviewer appears on more than one sampled game. This is too sparse to validate graph recommendation. The Steam API was reachable from the environment that made the pilot; check access from your own normal network before expanding.

## Source and crawl boundary

Use Steam's current documented `IUserReviewsService/GetAppReviews` endpoint: [Steamworks API documentation](https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english). The endpoint returns review text, reviewer ID, timestamp, and `voted_up`; it does not return a 1–5 star rating. The app ID is the game ID. The project uses one source, Steam, across multiple game app IDs so reviewers can connect games in the graph.

For the next feasibility sample, target **up to 100 recent English reviews for about 20 game IDs** (at most 2,000 records). Use `purchase_type=all`, preserve the returned cursor, and save progress incrementally. Steam documents a maximum of 100 reviews per page; anonymous requests have lower rate limits. On HTTP 429, wait and retry with backoff. Do not bypass access controls or keep retrying aggressively.

## Shared record format

Keep the current pilot's field names and types consistent:

| Field | Meaning |
| --- | --- |
| `review_id` | Steam recommendation ID; unique review key |
| `user_id` | Stable SHA-256 hash of SteamID, using the same transform for every game; this is pseudonymous, not anonymous |
| `item_id` | Steam app ID as a string |
| `item_title` | Game title for readability |
| `timestamp` | Review creation time as Unix seconds |
| `crawl_time_utc` | Time this record was collected |
| `source_feedback` | Original `voted_up` Boolean; overall recommendation, not aspect sentiment |
| `positive_interaction` | Same Boolean for Steam; downstream graph code uses `true` as a positive edge |
| `title` | Empty string when Steam provides no review title |
| `text` | Review body; retain negative as well as positive reviews |
| `language`, `helpful_votes` | API language and helpful-vote count |
| `source_url` | Current API endpoint; keep app ID in `item_id` |

Do not include raw SteamIDs in saved outputs. Do not map `voted_up` to aspect sentiment; the opinion-mining owner will infer aspect sentiment from the text separately.

## Your tasks and deliverables

1. Confirm the API works from your normal network and record the test result.
2. Expand the sample to up to 20 games and 100 recent English reviews per game. Keep a request log and make the crawl resumable.
3. Save:
   - `outputs/steam_expanded_pilot.jsonl`
   - `outputs/steam_expanded_manifest.json` with endpoint, filters, app IDs, page/cursor counts, times, and failures.
   - `outputs/steam_overlap_report.md` with records per game, duplicate and blank-text counts, unique reviewers, reviewers on multiple games, positive-edge counts, and the largest positive-graph connected component.
4. Recommend **continue with Steam** or **fall back to Amazon** based on access, review coverage, and graph overlap. Do not claim the 2,000-record pilot is representative.

## Completion checklist

- All sampled game IDs and request settings are recorded.
- Each saved record follows the shared schema, has a hashed user ID, and retains its `voted_up` value.
- Duplicate IDs, blank text, failed pages, and reviewer overlap are counted and reported.
- The manifest makes the crawl resumable and reproducible.
- If Steam access or graph overlap is inadequate, report the blocker and recommend the fallback; do not hide it by collecting from another platform.

## Start this role in Codex

Open this guide and the two pilot files above in the shared Codex workspace, then paste:

> I own the Steam crawler workstream for this project. Read this guide and inspect the existing pilot and code before editing. First verify that the documented Steam reviews endpoint works from this environment. Then implement a bounded, resumable crawl of up to 100 recent English reviews for about 20 game IDs, preserving the pilot schema and never overwriting the pilot. Save the expanded JSONL, a resumable manifest, and the overlap/data-quality report listed above. Include polite rate-limit handling and incremental saves. Do not bypass access controls, switch sources silently, or claim this convenience sample is representative. If the API is inaccessible or overlap remains too sparse, report evidence and recommend the Amazon fallback. Keep changes limited to crawler-owned files and summarize the artifacts and blockers when done.
