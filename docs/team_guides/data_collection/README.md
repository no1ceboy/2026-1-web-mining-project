# Member 1: Data collection and source checks

## Purpose

The collection workstream provides a reproducible, bounded Steam dataset and records what the crawl could and could not observe. The 10,000-review quota snapshot is retained for source assessment. The v3 user-history sample is the current recommendation pilot. These datasets have different sampling rules and must remain separate.

## Current status

The v3 run attempted 100 public profiles and selected 54 complete users who met the training-history rule. It contains 554 reviews across 95 games. The registered planning gate targets at least 500 users and 100 eligible users in each holdout; the pilot does not meet that gate.

The full-scale sampling configuration exists at configs/steam_history_sampling_full_v1.json but has not been run. A 20-review public-source, date, and content spot-check is also unfinished. See the [sampling design](../../sampling_design.md) and [current audit](../../../outputs/steam_history_v3/sampling_report.md).

## Responsibilities

1. Verify the public Steam endpoints from the normal collection network and record access failures.
2. Complete the source, date, and content spot-check using the template in outputs/steam_history_v3/source_spotcheck_template.csv.
3. Decide with the team whether to run a larger sample within the registered request budget or retain the pilot and narrow the report's claims.
4. If collection continues, write a new dataset version. Do not append new records to v3 or mix the quota snapshot into the history sample.
5. Preserve review IDs, hashed reviewer IDs, game IDs, source feedback, creation and update times, crawl times, and source provenance.
6. Report profile availability, collection failures, game coverage, review counts, and cross-game reviewer overlap.

## Source and data rules

Steam's official IUserReviewsService/GetAppReviews endpoint returns public reviews and uses cursor pagination. It includes an overall positive or negative recommendation vote, not a star rating. The current endpoint and parameters are documented in the [Steamworks Web API reference](https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english).

Keep negative, short, and non-English reviews in the interaction history. The opinion-mining view may apply separate text eligibility rules. Do not classify repeated phrases or simple text-pattern flags as spam without human review. Do not store raw SteamIDs, credentials, or API tokens in the repository.

## Deliverables

- A versioned data snapshot and manifest with collection settings, timestamps, app IDs, request status, and file hashes.
- A source/date/content spot-check with review IDs and clear outcomes.
- A concise coverage and collection-quality report.
