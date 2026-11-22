# Member 3 Guide: Link Analysis and LightGCN

## Project in one minute

The team is collecting game reviews from one source and testing whether review opinions improve game recommendations. Information Retrieval is excluded. The graph-model workstream covers the syllabus's link-analysis method, Personalized PageRank (PPR), and one learned graph recommender, LightGCN.

The four core configurations are Popularity, PPR, LightGCN, and LightGCN with opinion evidence. The cleaning/evaluation owner (Member 2) supplies the common data loader, time split, evaluator, and Popularity baseline. Do not build a separate incompatible split or metric implementation.

## Inputs and current limitation

- Current history-based pilot: `../../steam_history_v3/`
- Proposed split and coverage report: `../../steam_history_v3/split_manifest.json` and `../../steam_history_v3/sampling_report.md`
- Shared loader/evaluator contract: `../../../docs/evaluation_contract.md`
- Project Lead / Member 2 implementation: `../../../src/webmining/evaluation.py`

The v3 pilot has 54 train-defined users, 554 reviews, 22 validation targets, and 23 test targets. It is below the registered planning gate and supports evaluator/model smoke runs only, not final ranking claims. Load the same shared split for PPR and LightGCN; do not recreate the cutoff or candidate logic. Keep the separate 10,000-review quota snapshot out of v3. If the source decision changes, use one dataset at a time; never mix Steam and Amazon IDs or interactions in one graph.

## Models

### Personalized PageRank

Build a bipartite graph with user nodes and game nodes. Add an edge for each training interaction where `positive_interaction=true`. Starting from a user's node, run Personalized PageRank with restart and rank unseen games by their resulting scores. Exclude already reviewed games from recommendation candidates.

### LightGCN

Train LightGCN on the same positive training edges. Use the same users, time cutoffs, candidate games, and seen-item exclusions as PPR. Do not train on validation/test edges. An unobserved game is not a verified dislike. If sampled unobserved games are used as training negatives, treat them only as an optimization device; at evaluation, rank the full shared eligible candidate set.

Negative Steam reviews (`voted_up=false`) stay available for the opinion-mining work, but do not become positive graph edges. `voted_up` is the reviewer's overall recommendation, not a label for each aspect.

### Opinion-augmented LightGCN

Member 4 supplies a training-only opinion compatibility score for each user/game pair. Coordinate the join keys and score range with Member 4. The shared plan defines the fusion as:

```text
score(u, i) = (1 - alpha) * L(u, i) + alpha * O(u, i)
```

Here `L(u,i)` is LightGCN's normalized interaction-only score, `O(u,i)` is the normalized opinion compatibility, and `alpha` is selected on validation data only. If the opinion score is unavailable, use the LightGCN score. Do not use test reviews or test labels to build either model or select `alpha`.

## Tasks and deliverables

1. Inspect the v3 pilot and report graph coverage: users, games, positive edges, users with positive interactions on two or more games, and largest connected component.
2. Implement PPR and LightGCN so both consume `load_ranking_split` and `evaluate_ranker` from Member 2's shared evaluator.
3. Start with a runnable smoke configuration. If the Steam graph is too sparse, use Amazon only for a clearly labeled development run; do not report it as a Steam result.
4. After the team freezes an approved dataset and split, run PPR and LightGCN on the same evaluation protocol. Add the opinion-augmented LightGCN configuration when Member 4's validated features are ready.
5. Save:
   - Model code under `src/models/` and configs under `configs/` (create these folders if needed).
   - `outputs/graph_coverage.md` with data and connectivity counts.
   - `outputs/graph_metrics.json` with model, split version, metrics, seed, runtime, and hardware.
   - A short `outputs/graph_models_notes.md` explaining failures, missing coverage, and limitations.

Primary ranking metrics are Recall@10/20 and NDCG@10/20. Record the exact snapshot and split used for every result. A result from the 200-review pilot is a pipeline smoke result only, not evidence that one model is better.

## Completion checklist

- PPR and LightGCN use the same clean snapshot and time split.
- No future review, target edge, or test-derived opinion is used in training or validation tuning.
- Previously reviewed games are removed from each user's recommendation candidates.
- Report connectivity and eligible-user coverage alongside ranking metrics.
- If the Steam graph is too sparse, report that and pause final model comparison until the source gate is resolved.

## Start this role in Codex

Open this guide and the v3 pilot files in the shared Codex workspace, then paste:

> I own link analysis and graph recommendation. Read this guide and inspect the repository, v3 data schema, and existing code before editing. First calculate graph coverage for the v3 history pilot and save the requested diagnostic. Use `load_ranking_split` and `evaluate_ranker` from `src/webmining/evaluation.py`; do not implement a separate split, candidate set, or metric. Implement small, reproducible Personalized PageRank and LightGCN smoke runs using the same positive training edges. Keep runs small enough for ordinary hardware, record runtime and environment, and do not tune on test data. The registered sampling gate has not passed, so label all current metrics as pilot smoke results. Keep changes in graph-owned files and report artifacts, results, and blockers when done.
