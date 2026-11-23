# Research and data artifacts

This directory contains versioned source data, derived evaluation views, and pilot results. The v3 history sample is the current recommendation-evaluation dataset. Other snapshots are retained for source assessment and opinion-method development; they must not be combined with v3.

## Steam datasets

| Dataset | Contents | Intended use |
|---|---|---|
| steam_pilot.jsonl | 200 recent reviews from five games | Early crawl and opinion-taxonomy development |
| steam_100games_v1/ | 10,000 recent reviews sampled by a per-game quota | Collection, metadata, and overlap assessment; not the ranking benchmark |
| steam_history_v3/ | 554 historical reviews from 54 selected users across 95 games | Current ranking and opinion-feature feasibility pilot |

The v3 split files are accompanied by a manifest, file hashes, target lists, and seen-game masks. Do not edit these files in place. A revised collection or split must use a new dataset version.

## Evaluation results

- steam_history_v3/popularity_baseline_pilot.json contains the Popularity baseline.
- graph_metrics.json contains the Popularity, Personalized PageRank, and LightGCN pilot results on the shared evaluator.
- graph_coverage.md documents graph and candidate coverage.
- steam_history_v3/evaluation_owner_review.md records the shared split contract and explains why these results are smoke evidence only.

The v3 pilot has 22 validation users and 23 test users. The planned sample-size requirement is at least 500 users overall and at least 100 eligible users in each evaluation window. The requirement has not been met; do not describe these metrics as final evidence of model quality.

## Opinion-mining artifacts

- aspect_guide_v0.md defines the current aspect categories and annotation rules.
- annotation_batch_v0.csv contains 50 development reviews; the separate gold-label file is still empty.
- aspect_annotations_v0_claude_draft.csv is machine-generated draft material and is not ground truth.
- opinion_validation_v0.md records the current extraction and human-validation status.
- opinion_feature_spec_v0.md defines a proposed LightGCN opinion feature. It has not been validated or evaluated as a final model.
- opinion_profiles_v0/ contains exploratory lexicon-based profiles and coverage counts.

## Reproduction commands

Run from the repository root:

    python scripts/audit_history_quality.py
    python scripts/run_popularity_baseline.py --pilot-smoke
    python scripts/run_graph_models.py --pilot-smoke
    python scripts/opinion_select_batch.py
    python scripts/opinion_extract.py --backend lexicon --input outputs/steam_history_v3/opinion_train_candidates.jsonl --output outputs/opinion_profiles_v0/cohort_extraction_lexicon.jsonl

The opinion extractor outputs are not accuracy measurements. Human labels and a separate evaluation set are required before reporting precision, recall, or F1.
