# Steam expanded pilot: crawl, quality and overlap

Generated at 2026-11-21T04:02:22.096691Z. Dataset: `steam_expanded_v0`. Crawl status: **completed**.

**RECOMMEND AMAZON FALLBACK FOR MAIN EVALUATION.** This bounded pilot has only 20 games, 24 users with at least two distinct positive games, and 2 with at least three. These are descriptive history counts, not eligibility measured by the shared evaluator. The small candidate catalog also makes Recall@20 trivial. The recommended fallback is a project planning judgment for this pilot, not an agreed numerical acceptance threshold; Members 2/3 should verify the global split before the lead finalizes the source decision.

This is a recommendation for the project lead, not an automatic dataset switch. No Amazon data was fetched or merged.

## Collection and provenance

- Source: https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/
- API documentation: https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english
- Start / finish UTC: 2026-11-21T03:58:27.529326Z / 2026-11-21T04:00:16.671220Z
- Configured games: 20; target per game: 100; page size: 50.
- Parameters: recent (filter=1), English, all recommendation labels (review_type=0), all purchase types (purchase_type=1), off-topic filtering enabled. Parameters are passed as input_json.
- Selection: Convenience sample: the five original pilot games plus fifteen manually selected PC games across genres. Not a random or representative Steam sample.
- Crawl attempts: 40; successful: 40; failed: 0; HTTP 429: 0.
- Access probe attempts are recorded separately in the same request log and excluded from these crawl counts.
- See steam_access_check.json for this machine's access test; a teammate on a different network must test there separately.
- Cursor and per-game progress are saved after each page. Data is saved atomically before the manifest; a replay after a crash deduplicates existing review IDs.
- Local synthetic tests cover crash/replay and HTTP 429. Live bounded pause/resume is recorded in the manifest run_history; these are distinct from simulated failures.

## Data quality

| Check | Value |
| --- | ---: |
| Saved reviews | 2000 |
| Unique review IDs | 2000 |
| Duplicate IDs in saved file | 0 |
| Repeated user-game records | 0 |
| Blank review bodies | 15 |
| Bodies with at most 3 whitespace tokens (descriptive only) | 762 |
| Schema-invalid saved records | 0 |
| Duplicate observations skipped during requests/replay | 0 |
| Invalid observations excluded before saving | 0 |
| Distinct reviewers | 1972 |
| Distinct games | 20 |
| Positive recommendations | 1887 |
| Negative recommendations | 113 |

Review creation-time range UTC: 2026-11-10T01:01:01+00:00 to 2026-11-21T03:56:58+00:00.
All saved reviewer IDs pass the 64-character lowercase SHA-256 format check. The saved schema excludes raw author objects and SteamIDs. Source language labels were checked; no independent language classifier was run.

## Per-game coverage

| App ID | Configured game label | Reviews | Positive | Negative | Pages | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 570 | Dota 2 | 100 | 75 | 25 | 2 | target_reached |
| 730 | Counter-Strike 2 | 100 | 80 | 20 | 2 | target_reached |
| 440 | Team Fortress 2 | 100 | 97 | 3 | 2 | target_reached |
| 620 | Portal 2 | 100 | 100 | 0 | 2 | target_reached |
| 550 | Left 4 Dead 2 | 100 | 98 | 2 | 2 | target_reached |
| 400 | Portal | 100 | 98 | 2 | 2 | target_reached |
| 220 | Half-Life 2 | 100 | 99 | 1 | 2 | target_reached |
| 4000 | Garry's Mod | 100 | 98 | 2 | 2 | target_reached |
| 105600 | Terraria | 100 | 98 | 2 | 2 | target_reached |
| 413150 | Stardew Valley | 100 | 97 | 3 | 2 | target_reached |
| 1091500 | Cyberpunk 2077 | 100 | 96 | 4 | 2 | target_reached |
| 1245620 | ELDEN RING | 100 | 94 | 6 | 2 | target_reached |
| 1086940 | Baldur's Gate 3 | 100 | 97 | 3 | 2 | target_reached |
| 292030 | The Witcher 3: Wild Hunt | 100 | 92 | 8 | 2 | target_reached |
| 1174180 | Red Dead Redemption 2 | 100 | 84 | 16 | 2 | target_reached |
| 367520 | Hollow Knight | 100 | 99 | 1 | 2 | target_reached |
| 1145360 | Hades | 100 | 99 | 1 | 2 | target_reached |
| 646570 | Slay the Spire | 100 | 94 | 6 | 2 | target_reached |
| 294100 | RimWorld | 100 | 99 | 1 | 2 | target_reached |
| 548430 | Deep Rock Galactic | 100 | 93 | 7 | 2 | target_reached |

## Metadata audit

- Public Steam store appdetails check: **completed**.
- Verified game app types: **20 / 20**.
- Official app IDs, titles, types, request times and source URLs are saved in steam_metadata_audit.json.
- The review file keeps the configured human-readable game labels; the audit retains official titles separately (including trademark punctuation).
- This verifies the selected IDs are games; it is not a full genre/category audit or historical metadata snapshot.

## Reviewer overlap and positive graph

Positive graph: undirected bipartite graph with one edge per distinct user-game pair whose positive_interaction is true. Negative reviews are retained in the data but create no positive edges. Only nodes incident to positive edges are counted.

- Reviewers of at least two games (either feedback label): **25 / 1972**.
- Positive users / items / unique edges: **1860 / 20 / 1887**.
- Users with at least two distinct positive games: **24 / 1860**.
- Users with at least three distinct positive games: **2 / 1860**.
- Positive connected components: **4**.
- Largest component (by total nodes): **1604 users, 17 games, 1631 edges**.
- Largest component shares: **86.22% of positive nodes**, **86.43% of positive edges**.

| Distinct positive games per user | Users |
| --- | ---: |
| 1 | 1836 |
| 2 | 22 |
| 3 | 1 |
| 4 | 1 |

## Comparison with original pilot

These are separate time-dependent convenience snapshots, not a random-sample comparison. The original files were not modified.

| Check | Original pilot | Expanded pilot |
| --- | ---: | ---: |
| Reviews | 200 | 2000 |
| Games | 5 | 20 |
| Reviewers | 199 | 1972 |
| Multi-game reviewers | 1 | 25 |
| Users with >=2 positive games | 1 | 24 |
| Users with >=3 positive games | 0 | 2 |

## Evaluation implications and handoff

- History counts are upper bounds only. Member 2 owns global chronological cutoffs, warm-user/item eligibility and the final evaluator; this report does not invent a competing split.
- Two positive games can potentially support a user's historical interaction plus one held-out target. Three can potentially support history plus separate validation and test targets for that same user; the global protocol does not require every evaluated user to occur in both windows.
- Having a large connected component does not imply that users have long histories: a few cross-game reviewers can connect many item-centered stars.
- With only 20 sampled games and seen games excluded, K=20 can cover every eligible candidate in this pilot. Recall@20 would then be trivial; do not use it as evidence of recommendation quality.
- Keep both feedback labels for opinion mining. A negative recommendation is not an aspect sentiment label. Unobserved items are not verified negative labels.
- Review creation timestamps do not certify historical text contents; collected reviews may have been edited later. Member 2/4 must establish an edit-time policy before historical text features are used.
- Share the versioned JSONL and manifest with Member 2, and these graph diagnostics with Member 3. Member 4 can use this pilot to develop annotation guidelines; ranking features must later respect the agreed historical split.
- The limited metadata check above establishes only the fields it records; do not claim a full metadata audit.
- Ask the lead to confirm the Steam/Amazon decision. Do not collect beyond this bound or silently mix sources.

## Limitations

- Bounded convenience sample, not representative of Steam or all game players.
- Recent English reviews only; manually selected games; off-topic filtering enabled.
- No complete purchase/exposure histories; unobserved games are not verified dislikes.
- Steam voted_up is overall binary recommendation feedback, not aspect sentiment.
- SHA-256 reviewer identifiers are pseudonymous, not anonymous.
- Review text can be edited after creation: timestamp is creation time, not proof that the collected text existed then. Strict historical text evaluation needs an edit-time policy or historical snapshots.
- API responses may be cached; collection settings do not reproduce an immutable server snapshot.
- App names are manually configured labels, not a complete metadata audit.
