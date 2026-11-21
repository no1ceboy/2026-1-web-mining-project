# Data Collection and Provenance Guide

Implementation and run instructions: [Steam data collection runbook](../../../docs/steam_data_collection.md). Start with `python scripts/steam_crawler.py --check-access` from the repository root. The current 100-game snapshot and source assessment are documented in [the overlap report](../../steam_100games_v1/steam_overlap_report.md). The original 20-game snapshot is preserved separately.

## Project in one minute

The team is building a review-aware game recommendation system. We want to learn whether opinions extracted from game reviews improve recommendations based on links between users and games. The capstone combines a reproducible data-collection system with an evaluated method. Information Retrieval is out of scope; the course connections are link analysis and opinion mining, with LightGCN as the learned recommender.

The crawler workstream collects a bounded, auditable review sample from one platform across multiple games. The scope is limited to one source and does not attempt to copy all of Steam.

## What already exists

- `../../steam_pilot.jsonl`: 200 recent English reviews from five Steam games.
- `../../steam_pilot_manifest.json`: request settings and crawl counts.
- `../../README.md`: full project plan and the pilot's limitations.

The pilot has 200 unique reviews and 199 unique hashed reviewers, but only one reviewer appears on more than one sampled game. This is too sparse to validate graph recommendation. The Steam API was reachable from the environment that made the pilot; the crawler owner should verify access from the collection network before expanding.

## Source and crawl boundary

Use Steam's current documented `IUserReviewsService/GetAppReviews` endpoint: [Steamworks API documentation](https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english). The endpoint returns review text, reviewer ID, timestamp, and `voted_up`; it does not return a 1–5 star rating. The app ID is the game ID. The project uses one source, Steam, across multiple game app IDs so reviewers can connect games in the graph.

The updated collection target is **up to 100 recent English reviews for 100 game IDs** (at most 10,000 saved records), replacing the original 20-game feasibility target. Use `purchase_type=all`, preserve the returned cursor, and save progress incrementally. Steam documents a maximum of 100 reviews per page; anonymous requests have lower rate limits. On HTTP 429, wait and retry with backoff. Do not bypass access controls or keep retrying aggressively.

## Shared record format

Keep the current pilot's field names and types consistent:

| Field | Meaning |
| --- | --- |
| `review_id` | Steam recommendation ID; unique review key |
| `user_id` | Stable SHA-256 hash of SteamID, using the same transform for every game; this is pseudonymous, not anonymous |
| `item_id` | Steam app ID as a string |
| `item_title` | Game title for readability |
| `timestamp` | Review creation time as Unix seconds |
| `timestamp_updated` | Last edit time as Unix seconds when provided; preserved in the new snapshot, optional for older snapshots |
| `crawl_time_utc` | Time this record was collected |
| `source_feedback` | Original `voted_up` Boolean; overall recommendation, not aspect sentiment |
| `positive_interaction` | Same Boolean for Steam; downstream graph code uses `true` as a positive edge |
| `title` | Empty string when Steam provides no review title |
| `text` | Review body; retain negative as well as positive reviews |
| `language`, `helpful_votes` | API language and helpful-vote count |
| `source_url` | Current API endpoint; keep app ID in `item_id` |

Do not include raw SteamIDs in saved outputs. Do not map `voted_up` to aspect sentiment; the opinion-mining owner will infer aspect sentiment from the text separately.

## Tasks and deliverables

1. Confirm the API works from the crawler owner's normal network and record the test result.
2. Expand the sample to 100 games and up to 100 recent English reviews per game. Keep a request log and make the crawl resumable.
3. Save:
   - `outputs/steam_100games_v1/steam_expanded_pilot.jsonl`
   - `outputs/steam_100games_v1/steam_expanded_manifest.json` with endpoint, filters, app IDs, page/cursor counts, times, and failures.
   - `outputs/steam_100games_v1/steam_overlap_report.md` with records per game, duplicate and blank-text counts, unique reviewers, reviewers on multiple games, positive-edge counts, and the largest positive-graph connected component.
4. Assess whether to continue with Steam or use the Amazon fallback based on access, review coverage, overlap and the shared chronological evaluator. Do not claim the 10,000-record convenience sample is representative.

## Completion checklist

- All sampled game IDs and request settings are recorded.
- Each saved record follows the shared schema, has a hashed user ID, and retains its `voted_up` value.
- Duplicate IDs, blank text, failed pages, and reviewer overlap are counted and reported.
- The manifest makes the crawl resumable and reproducible.
- If Steam access or graph overlap is inadequate, report the blocker and recommend the fallback; do not hide it by collecting from another platform.

## Start this role in Codex

Open this guide and the two pilot files above in the shared Codex workspace, then paste:

> I own the Steam data collection workstream. Read this guide and inspect the current code and snapshots before editing. Verify the documented reviews endpoint, then run the bounded, resumable 100-game configuration with up to 100 recent English reviews per game. Preserve existing snapshots; save the new version under outputs/steam_100games_v1. Include hashes, timestamps, update times, source provenance, request logs, resumable progress and quality/overlap diagnostics. Do not bypass access controls, switch sources silently or claim representativeness. Coordinate the shared chronological feasibility check before making model-quality claims.
