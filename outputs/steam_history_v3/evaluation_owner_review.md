# Project Lead / Member 2: evaluation-owner review

## Decision

The v3 sampler output and proposed split are accepted for **shared-loader development and pilot smoke evaluation only**. The split manifest remains marked `proposed_sampling_contract_requires_evaluation_owner_review`; this note records the scope of review without editing the source manifest or its hashes.

The v3 output is not yet approved as the final recommendation benchmark. Its declared planning gate is unmet, and the human source/date/content spot-check has not been completed. The quota snapshot in `outputs/steam_100games_v1/` remains a separate dataset and must not be merged into v3.

## Data and coverage review

The current v3 cohort contains 54 train-defined users and 554 reviews across 95 observed games from the 100-game catalogue. It has 509 positive and 45 negative interactions. The quality audit flags 382 reviews as shorter than 20 whitespace-delimited tokens; the median text length is 9 tokens. Only 85 texts are available as English opinion candidates before the validation cutoff.

| Split | History rows | Positive user-game edges | Warm items | Target users | Candidate count |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation | 354 | 334 | 84 | 22 | 69–81 |
| Test | 494 | 458 | 90 | 23 | 69–86 |

The registered planning gate calls for at least 500 cohort users and at least 100 eligible users in each holdout with more than 20 candidates. Current coverage is 54 / 22 / 23, so it fails that gate. The split is adequate to check loader and metric plumbing, but not to make a reliable claim about recommendation quality.

The 20-row source/date/content spot-check template is still blank. One inspected opinion-candidate example contains unusually long, promotional, highly templated prose. This is a reason to complete the spot-check and inspect more examples; it is not enough evidence to classify the whole dataset as invalid. Do not treat detector labels or the current text-eligibility flags as human validation.

The reproducible text audit also found 10 exact normalized-text groups with repeated content (43 excess rows, largest group size 14), 10 reviews containing the “Originally posted by author” marker, 11 with Introduction/Conclusion headings, and 4 matching simple promotional-language signals. These flags overlap and are only screening cues. The audit found no repeated user-game pair, feedback-mapping mismatch, blank review body, or review-ID duplicate in the cohort. Keep all records unless a documented, human-reviewed rule justifies an exclusion; identical short text alone is not sufficient.

Run `python scripts/audit_history_quality.py` to reproduce the checks. It writes `text_quality_audit.json` and `text_quality_audit.md` without changing the source rows.

## Shared evaluation interface

`src/webmining/evaluation.py` is the common implementation for the current versioned history artifacts. It verifies the split-file hashes, checks the target and seen-item masks, and exposes `load_ranking_split`, `evaluate_ranker`, `popularity_scores`, and `evaluate_popularity`.

- Validation scores use only `train_reviews.jsonl`.
- Test scores use `refit_reviews.jsonl`, which contains permitted history before the test cutoff.
- Only unique positive user-game edges enter the graph or Popularity counts.
- Previously reviewed games—including negative reviews—are removed using the shared seen-item masks.
- Candidates are the split's warm positive-game catalogue minus each user's seen games.
- Recall@10/20 and NDCG@10/20 are macro-averaged over target users. Ties use ascending item ID.

Graph-model code can use the same loader and scorer interface:

```python
from webmining.evaluation import evaluate_ranker, load_ranking_split

validation = load_ranking_split("outputs/steam_history_v3", "validation")
metrics = evaluate_ranker(validation, lambda user_id, item_id: model.score(user_id, item_id))
```

## Popularity smoke result

`outputs/steam_history_v3/popularity_baseline_pilot.json` was produced with the shared loader and evaluator. It is marked `pilot_smoke_only`; the planning gate has not passed.

| Split | Target users | Recall@10 | NDCG@10 | Recall@20 | NDCG@20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation | 22 | 0.182 | 0.068 | 0.500 | 0.147 |
| Test | 23 | 0.130 | 0.043 | 0.304 | 0.088 |

There is one target per user in these files, so one user changes Recall by 4.55 percentage points on validation and 4.35 points on test. These figures verify the evaluation path; they are not final model results and do not support comparison until the registered coverage and data-quality requirements are resolved.

## Handoffs

1. Data Collection completes and records the 20-row source/date/content spot-check, especially the text examples flagged for human review.
2. The team either runs the separately configured full-scale cohort collection within its registered request budget or documents a source pivot. Rebuild the dataset into a new version; do not append into v3.
3. Data Collection and the Project Lead agree on the final snapshot and split contract before model tuning. The full-scale cohort must be re-audited for real eligible validation/test users; do not infer them from raw review count or component size.
4. Member 3 uses this shared evaluator for PPR and LightGCN. Member 4 keeps opinion profiles training-only and reports extraction quality against human labels before adding opinion scores to the recommendation comparison.
