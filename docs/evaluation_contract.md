# Shared Evaluation Contract

## Purpose

The project compares a simple reference ranker, graph link analysis, and a learned graph recommender. Every method must use the same target users, training history, eligible candidates, seen-game exclusions, and ranking metrics. This contract defines the shared interface for those experiments.

## Current data contract

The current source is the versioned Steam user-history pilot in `outputs/steam_history_v3/`. Its split manifest is marked `proposed_sampling_contract_requires_evaluation_owner_review`; the Project Lead / Member 2 has reviewed it for **pilot use only**. It is not approved as a final benchmark because its registered coverage gate has not passed and its public-source spot check is still blank.

| Split | History file | Target file | Seen-game file |
| --- | --- | --- | --- |
| Validation | `train_reviews.jsonl` | `validation_targets.jsonl` | `seen_items_before_validation.jsonl` |
| Test | `refit_reviews.jsonl` | `test_targets.jsonl` | `seen_items_before_test.jsonl` |

The sampler-produced files and their manifest hashes are authoritative. Do not silently re-clean, resort, truncate, or edit them. Build alternate processing outputs with a new version and preserve the source artifacts.

## Graph and candidate rules

- A graph edge is a unique `(user_id, item_id)` pair whose `positive_interaction` is `true` in that split's history. Negative reviews remain available in the history but do not become graph edges.
- `source_feedback` is Steam's overall recommendation vote. It is not an aspect-sentiment label.
- The warm candidate catalogue for a split is the set of games with at least one positive edge in that split's permitted history.
- For each target user, remove every previously reviewed game in the split's seen-game mask, including negative reviews and reviews before the study window.
- Every held-out target must be a warm, unseen candidate. Candidate counts in target files must match the shared loader's recomputation.
- Validation models use `train_reviews.jsonl`; the test evaluation refits on `refit_reviews.jsonl`. Do not use target review text or feedback to build histories, item profiles, or model scores.

## Metrics and baseline

The primary metrics are macro Recall@10/20 and NDCG@10/20 over eligible target users. The evaluator ranks each user's full eligible warm-catalogue candidate set. Ties are broken by ascending item ID for reproducibility. With one target per user, Recall@K is hit rate at K.

Popularity ranks games by the count of distinct positive user-game edges in the permitted history. PPR and LightGCN must implement the same `score(user_id, item_id)` interface and call the same evaluator. Report target-user count, warm users/items, candidate-count range, snapshot, split, and coverage beside every metric.

Run the current small cohort only as an evaluator smoke check:

```powershell
python scripts/audit_history_quality.py
python scripts/run_popularity_baseline.py --pilot-smoke
```

The audit writes `text_quality_audit.json` and `text_quality_audit.md` in the v3 folder without changing source rows. The baseline command writes `outputs/steam_history_v3/popularity_baseline_pilot.json`. Those metrics verify plumbing; they are not evidence of comparative model quality.

## Coverage and limitations

The v3 pilot contains 54 train-defined users and 554 in-window reviews. The proposed global windows currently have 22 validation target users and 23 test target users. Their candidate counts are above 20, but the registered planning gate asks for at least 500 cohort users and at least 100 eligible users in each holdout. The gate is therefore not met. These small holdouts can reveal implementation errors, not establish a reliable ranking conclusion.

The cohort is a sample of complete, accessible public profiles selected using training evidence, not a representative sample of Steam users. The 20-row source/date/content spot-check template has no human labels yet. Public dates have day-level uncertainty for most records, and the current split contract assumes profiles without a displayed edit date were unedited. Confirm this assumption before historical text claims. The opinion candidate file has 85 records; it is only a small development pool, not a validated aspect-mining dataset.

Keep the 10,000-review quota snapshot separate from this history-cohort dataset. It can support crawling and text-pipeline development, but it must not be merged into this split to inflate histories, candidate counts, or metrics.
