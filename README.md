# 2026-1 Web Mining Project

**Working title:** Review-Aware Game Recommendation with Web Mining

This capstone studies whether opinions mined from Steam game reviews add useful evidence to recommendations built from user-game links. It combines web data collection, link analysis, opinion mining, and a small recommendation demo. Information retrieval is out of scope.

## Start here

1. Read the [full project plan](outputs/README.md) for the research questions, shared schema, evaluation plan, and checkpoint schedule.
2. Open the README for the assigned workstream:
   - [Member 1: crawler and data provenance](outputs/team_guides/member1_crawler/README.md)
   - [Member 3: Personalized PageRank and LightGCN](outputs/team_guides/member3_graph_models/README.md)
   - [Member 4: opinion mining and validation](outputs/team_guides/member4_opinion_mining/README.md)
3. Start from the [Steam pilot reviews](outputs/steam_pilot.jsonl) and [pilot manifest](outputs/steam_pilot_manifest.json). Keep this original pilot unchanged; write new, versioned outputs.

## Project in brief

The main comparison is Popularity vs. Personalized PageRank (PPR) vs. LightGCN. We then test whether validated aspect-level opinions from review text improve LightGCN. Steam's `voted_up` field is an overall recommendation label; it is not the sentiment of every aspect mentioned in a review.

The current pilot contains 200 recent English reviews from five games. It has very little cross-game reviewer overlap, so it is suitable for pipeline development but not for model-quality claims. The crawler owner will expand the same-source sample and report overlap before the team decides whether to continue with Steam or use the Amazon fallback. Never combine Steam and Amazon users or interactions in one graph.

## Workstream owners

| Owner | Workstream | First evidence to share |
| --- | --- | --- |
| Project Lead / Member 2 | Cleaning, shared loader, chronological split, evaluator, Popularity baseline | Clean-data counts, exclusions, split/evaluator contract, baseline status |
| Member 1 | Steam crawler and provenance | Expanded sample, manifest, access status, overlap/data-quality report |
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

Each contributor should create a branch for the assigned workstream, for example `member1/crawler`, `member3/graph-models`, or `member4/opinion-mining`. Commit focused changes and open a pull request or request review from the project lead before merging. Do not commit model weights, environment files, credentials, caches, or large unbounded crawls. Keep generated reports and bounded samples reproducible and small enough to review.

## Current status

The repository begins with the project plan, role guides, a 200-review Steam feasibility pilot, and its crawl manifest. The expanded crawl, cleaning pipeline, models, opinion validation, and demo are work in progress. See the [timeline and immediate checkpoint plan](outputs/README.md#9-timeline-and-compute-plan).
