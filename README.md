# 2026-1 Web Mining Project

**Working title:** Review-Aware Game Recommendation with Web Mining

This capstone studies whether opinions mined from Steam game reviews add useful evidence to recommendations built from user-game links. It combines web data collection, link analysis, opinion mining, and a small recommendation demo. Information retrieval is out of scope.

## Start here

1. Read the [full project plan](outputs/README.md) for the research questions, shared schema, evaluation plan, and checkpoint schedule.
2. Open the README for the assigned workstream:
   - [Data collection and provenance](outputs/team_guides/data_collection/README.md)
   - [Member 3: Personalized PageRank and LightGCN](outputs/team_guides/member3_graph_models/README.md)
   - [Member 4: opinion mining and validation](outputs/team_guides/member4_opinion_mining/README.md)
3. Use the [10,000-review, 100-game snapshot](outputs/steam_100games_v1/steam_expanded_pilot.jsonl), [crawl manifest](outputs/steam_100games_v1/steam_expanded_manifest.json), and [data-quality/overlap report](outputs/steam_100games_v1/steam_overlap_report.md) for the next development steps. This snapshot still needs cleaning and a shared chronological split. Keep the original 200-review pilot and the [2,000-review snapshot](outputs/steam_expanded_pilot.jsonl) unchanged; write new, versioned outputs.
4. Read the [technical project assessment](docs/project_assessment.md) for data limitations, scope, workload and priorities for the four-person team.

## Project in brief

The main comparison is Popularity vs. Personalized PageRank (PPR) vs. LightGCN. We then test whether validated aspect-level opinions from review text improve LightGCN. Steam's `voted_up` field is an overall recommendation label; it is not the sentiment of every aspect mentioned in a review.

The current snapshot contains 10,000 recent English reviews from 100 games and 9,718 reviewers. Only 169 reviewers have positive interactions with at least two sampled games, 37 with at least three, and five with at least five. The larger catalog removes the old 20-item Recall@20 limitation, but graph training/evaluation suitability remains conditional on the shared chronological split. See the [source assessment](outputs/steam_100games_v1/steam_overlap_report.md). Never combine Steam and Amazon users or interactions in one graph.

## Workstream owners

| Owner | Workstream | First evidence to share |
| --- | --- | --- |
| Project Lead / Member 2 | Cleaning, shared loader, chronological split, evaluator, Popularity baseline | Clean-data counts, exclusions, split/evaluator contract, baseline status |
| Data Collection | Steam crawler and provenance | Expanded sample, manifest, access status, overlap/data-quality report |
| Member 3 | PPR and LightGCN | Graph coverage, runnable pilot methods, runtime and limitations |
| Member 4 | Opinion mining | Aspect guide, human annotation pilot, extractor benchmark and validation status |

All four streams can start from the pilot in parallel. Coordinate shared field names and model interfaces early; rerun results on the same frozen clean snapshot when it is ready.

## Shared-data rules

- Preserve `review_id`, hashed `user_id`, `item_id`, `timestamp`, `crawl_time_utc`, `source_feedback`, `positive_interaction`, `title`, `text`, and `source_url` when the source provides them.
- Do not store raw SteamIDs, credentials, or API tokens in the repository.
- Keep negative reviews for opinion mining, but create recommendation edges only from the agreed positive-interaction rule.
- Do not use validation/test interactions or future review text in training, user profiles, opinion features, or tuning.
- Record dataset version, filters, split, random seed, runtime, and hardware for reported results.

## Git collaboration

Each contributor should create a branch for the assigned workstream, for example `feat/steam-data-collection`, `member3/graph-models`, or `member4/opinion-mining`. Commit focused changes and open a pull request or request review from the project lead before merging. Do not commit model weights, environment files, credentials, caches, or large unbounded crawls. Keep generated reports and bounded samples reproducible and small enough to review.

## Current status

The expanded bounded crawl is complete: 10,000 saved reviews across 100 apps, with request logs, resumable manifests, SHA-256 user IDs, creation/update timestamps, and an [overlap/data-quality report](outputs/steam_100games_v1/steam_overlap_report.md). The limited store metadata audit verified 98 app types as games; two appdetails responses remain unavailable and are recorded as unresolved. The 200- and 2,000-review snapshots are preserved. See the [runbook](docs/steam_data_collection.md) for commands and handoff instructions. Cleaning, shared evaluation, models, opinion validation, and the demo are not yet present on main. The team still needs to verify chronological coverage before finalizing the main recommendation dataset.
