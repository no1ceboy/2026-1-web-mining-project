# Member 2: Data preparation and evaluation

## Purpose

This workstream creates one auditable data view and one evaluation protocol that Popularity, Personalized PageRank, and LightGCN can share. The goal is a fair comparison, not to remove records until a model score improves.

## Current status

The shared loader checks required fields, file hashes, held-out targets, seen-game masks, candidate counts, and duplicate review IDs. The data-quality audit reports no blank text, duplicate review IDs, repeated user-game pairs, or feedback-mapping conflicts in the v3 sample. Short and repeated text is flagged rather than deleted automatically.

The Popularity baseline and shared metrics are implemented. The v3 split is accepted for pilot smoke evaluation only: 54 users, 22 validation targets, and 23 test targets. The registered coverage gate is unmet, and the source/date/content spot-check remains open. See the [evaluation contract](../evaluation_contract.md), [quality audit](../../outputs/steam_history_v3/text_quality_audit.md), and [evaluation review](../../outputs/steam_history_v3/evaluation_owner_review.md).

## Cleaning rules

1. Keep source data unchanged. Build versioned processed views and record exclusions with explicit reasons.
2. Validate review, user, and game identifiers; validate Boolean feedback and timestamps; preserve source and crawl provenance.
3. Deduplicate true copies by review ID. Do not remove records only because different people wrote the same short phrase.
4. Keep negative, short, and non-English records in the review history. Only positive user-game pairs form recommendation edges.
5. Keep every previously reviewed game in the user's seen-game mask, including negative reviews. Do not present unreviewed games as confirmed dislikes.
6. Apply the time-availability rules before constructing histories or opinion profiles. Keep later reviews and edits out of earlier split views.
7. Treat Steam's overall recommendation vote as separate from aspect sentiment inferred from text.
8. Apply language and minimum-text-length rules only to the opinion-training view; record the candidate count and excluded count.

## Evaluation rules

- Use the versioned files and hashes in `outputs/steam_history_v3/split_manifest.json`. Do not manually edit split files.
- Use the shared loader and evaluator in `src/webmining/evaluation.py`.
- Validation uses train_reviews.jsonl; test refits on refit_reviews.jsonl before its cutoff.
- Rank each user's full eligible warm-game catalogue after removing all seen games.
- Report Recall@10/20 and NDCG@10/20 with target-user counts, candidate ranges, dataset version, and limitations.

## Deliverables

- Reproducible data-quality audit and before/after counts for any new filter.
- Shared loader and evaluation contract.
- Popularity baseline on the approved final snapshot.
- A concise handoff stating the snapshot hash, split status, candidate rules, and known data limitations.
