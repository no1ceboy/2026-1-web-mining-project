# Member 3 Guide: Link Analysis and LightGCN

## Project in one minute

The team is collecting game reviews from one source and testing whether review opinions improve game recommendations. Information Retrieval is excluded. The graph-model workstream covers the syllabus's link-analysis method, Personalized PageRank (PPR), and one learned graph recommender, LightGCN.

The four core configurations are Popularity, PPR, LightGCN, and LightGCN with opinion evidence. The cleaning/evaluation owner (Member 2) supplies the common data loader, time split, evaluator, and Popularity baseline. Do not build a separate incompatible split or metric implementation.

## Inputs and current limitation

- Initial pilot: `../../steam_pilot.jsonl`
- Pilot counts and source notes: `../../steam_pilot_manifest.json`
- Shared project plan: `../../README.md`
- Expected handoff from Member 2 after cleaning: `outputs/steam_clean_v0.jsonl` and a split manifest. Confirm the final paths with Member 2 before coding against them.

The current 200-review Steam sample has only one reviewer appearing on multiple games. Use it to inspect the schema and compute graph-coverage statistics, **not** to claim meaningful ranking performance. The crawler owner is testing a larger same-source sample. If Steam remains too sparse, the team may use Amazon as a separate fallback dataset; never mix Steam and Amazon IDs or interactions in one graph.

## Models

### Personalized PageRank

Build a bipartite graph with user nodes and game nodes. Add an edge for each training interaction where `positive_interaction=true`. Starting from a user's node, run Personalized PageRank with restart and rank unseen games by their resulting scores. Exclude already reviewed games from recommendation candidates.

### LightGCN

Train LightGCN on the same positive training edges. Use the same users, time cutoffs, candidate games, and seen-item exclusions as PPR. Do not train on validation/test edges. An unobserved game is not a verified dislike; use the shared negative-sampling protocol from the evaluator.

Negative Steam reviews (`voted_up=false`) stay available for the opinion-mining work, but do not become positive graph edges. `voted_up` is the reviewer's overall recommendation, not a label for each aspect.

### Opinion-augmented LightGCN

Member 4 supplies a training-only opinion compatibility score for each user/game pair. Coordinate the join keys and score range with Member 4. The shared plan defines the fusion as:

```text
score(u, i) = (1 - alpha) * L(u, i) + alpha * O(u, i)
```

Here `L(u,i)` is LightGCN's normalized interaction-only score, `O(u,i)` is the normalized opinion compatibility, and `alpha` is selected on validation data only. If the opinion score is unavailable, use the LightGCN score. Do not use test reviews or test labels to build either model or select `alpha`.

## Tasks and deliverables

1. Inspect the current pilot schema and report graph coverage: users, games, positive edges, users with positive interactions on two or more games, and largest connected component.
2. Implement PPR and LightGCN so both consume Member 2's shared loader and split.
3. Start with a runnable smoke configuration. If the Steam graph is too sparse, use Amazon only for a clearly labeled development run; do not report it as a Steam result.
4. After Member 2 freezes a clean snapshot, run PPR and LightGCN on the same evaluation protocol. Add the opinion-augmented LightGCN configuration when Member 4's validated features are ready.
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

Open this guide and the pilot files in the shared Codex workspace, then paste:

> I own link analysis and graph recommendation. Read this guide and inspect the repository, data schema, and existing code before editing. First calculate graph coverage for the 200-review Steam pilot and save the requested diagnostic. Then check what split and evaluator Member 2 is building and agree on their interface before adding model code. Implement a small, reproducible Personalized PageRank baseline and LightGCN feasibility run using the same positive training edges and evaluation protocol. Keep runs small enough for ordinary hardware, record runtime and environment, and do not tune on test data. The current pilot is too sparse for model-quality claims; if it cannot support evaluation, document that and use Amazon only for a clearly labeled development run. Keep changes in graph-owned files and report artifacts, results, and blockers when done.
