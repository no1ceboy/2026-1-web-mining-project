# Member 3: Link analysis and game ranking

## Purpose

This workstream compares a link-analysis method, Personalized PageRank, with LightGCN, a learned recommender that propagates user and game representations over an interaction graph. Both methods use the same split and evaluator as the Popularity baseline.

## Current status

The PPR and LightGCN implementations and pilot metrics are in `src/models/` and `outputs/graph_metrics.json`. They use the shared v3 evaluator. The run is marked pilot-only because there are 22 validation users and 23 test users, below the planned sample-size requirement. The inputs are the [v3 history sample](../../../outputs/steam_history_v3/) and [shared evaluation contract](../../evaluation_contract.md); the common loader is `src/webmining/evaluation.py`.

On the test split, PPR has Recall@10 0.217 and NDCG@10 0.088. LightGCN has Recall@10 0.174 and NDCG@10 0.058. At 20 results, LightGCN has Recall@20 0.348, while PPR and Popularity each have 0.304. With only 23 test users, these results check the implementation; they do not show that one method is generally better.

## Shared graph rules

- Use unique positive user-game pairs from the permitted history as graph edges.
- Keep negative reviews in the data and seen-game mask, but do not use them as positive edges.
- Remove every previously reviewed game from each user's candidate set.
- Treat a game without an observed review as unknown, not disliked.
- Do not use validation or test interactions, later reviews, or later edits to fit a model.
- Use src/webmining/evaluation.py for split loading and ranking metrics. Do not create a separate candidate set or evaluator.

## Reproduction

Install the CPU package listed in `requirements-graph.txt`, then run from the repository root:

    python scripts/run_graph_models.py --pilot-smoke

The current configuration uses PPR restart probability 0.15 and LightGCN with 32-dimensional embeddings, two propagation layers, 30 training epochs, and seed 2026. The saved metrics record CPU execution.

## Remaining work

1. Rerun both methods on the approved final dataset and report the number of eligible users with all metrics.
2. Record the exact software environment and repository command used for the final rerun.
3. Integrate opinion scores only after Member 4 has validated them and both owners agree on cutoff-specific fields and fallback rules.
