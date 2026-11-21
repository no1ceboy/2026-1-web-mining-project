# 2026-1 Web Mining Project

**Working title:** Review-Aware Game Recommendation with Web Mining

This capstone studies whether opinions mined from Steam game reviews add useful evidence to recommendations built from user-game links. It combines web data collection, link analysis, opinion mining, and a small recommendation demo. Information retrieval is out of scope.

## Start here

1. Read the [full project plan](outputs/README.md) for the research questions, shared schema, evaluation plan, and checkpoint schedule.
2. Open the README for the assigned workstream:
   - [Data collection and provenance](outputs/team_guides/data_collection/README.md)
   - [Member 3: Personalized PageRank and LightGCN](outputs/team_guides/member3_graph_models/README.md)
   - [Member 4: opinion mining and validation](outputs/team_guides/member4_opinion_mining/README.md)
3. For recommendation data, read the [user-history sampling design](docs/sampling_design.md) and [current sampling audit](outputs/steam_history_v3/sampling_report.md). The new sampler retains observed user histories and defines cohort membership using training data only. Its outputs are a feasibility pilot and proposed split contract; check the audit gate before treating them as final benchmark data.
4. Keep the [10,000-review quota snapshot](outputs/steam_100games_v1/steam_expanded_pilot.jsonl), [its manifest](outputs/steam_100games_v1/steam_expanded_manifest.json), and [quality report](outputs/steam_100games_v1/steam_overlap_report.md) as a separate reference. Do not combine it with the historical cohort to fill row counts or build pre-cutoff features. The original 200- and 2,000-review snapshots also remain unchanged.
5. Read the [technical project assessment](docs/project_assessment.md) for data limitations, scope, workload and priorities for the four-person team.

## Project in brief

The main comparison is Popularity vs. Personalized PageRank (PPR) vs. LightGCN. We then test whether validated aspect-level opinions from review text improve LightGCN. Steam's `voted_up` field is an overall recommendation label; it is not the sentiment of every aspect mentioned in a review.

The earlier quota snapshot contains 10,000 recent English reviews from 100 games and 9,718 reviewers, but only 169 reviewers with two positive games. The [revised acquisition method](docs/sampling_design.md) therefore discovers reviewers in a historical training window and collects their public histories within a frozen 100-game catalogue. It preserves short/negative interactions, separates usable English opinion text, records date uncertainty and measures actual chronological coverage. The target population is a train-defined active-reviewer cohort, not all Steam users. Never combine Steam and Amazon users or interactions in one graph.

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

The quota crawl remains available as a reference. The new history sampler and cohort/coverage builder are implemented; see the [latest audit](outputs/steam_history_v3/sampling_report.md) for counts, limitations and whether the declared planning gate passes. Raw discovery, cohort reviews, historical views, seen-item masks and opinion-training candidates are versioned separately. Public-history dates have day precision except matching API-anchored seeds; exact historical text cannot be reconstructed. Final shared evaluator integration, models, human opinion validation and the demo remain pending on main. Use the [sampling runbook](docs/sampling_design.md#chạy-và-chạy-tiếp) for the new pipeline and the [API crawl runbook](docs/steam_data_collection.md) for the earlier snapshot.

The v3 design pilot checked 100 profiles and produced 54 train-eligible cohort users with 554 reviews across 95 observed games. The proposed temporal contract yields 22 validation and 23 test users, with 69–86 candidates each. These are coverage counts, not ranking scores; the planning gate is not yet met. A separately versioned [full-scale resource configuration](configs/steam_history_sampling_full_v1.json) is prepared but has not been executed.
