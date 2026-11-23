# Member 4 Guide: Opinion Mining and Validation

## Project in one minute

The team is collecting game reviews and testing whether extracted review opinions improve recommendations. The opinion-mining workstream identifies aspects reviewers praise or criticize, validates extraction quality, and provides an opinion feature for LightGCN. The project uses link analysis and opinion mining; Information Retrieval is excluded.

The Steam API's `voted_up` value is the reviewer's overall recommendation, not an aspect sentiment label. A positive recommendation can contain a complaint about graphics; a negative recommendation can praise gameplay. Read and label the review text itself.

## Inputs and current pilot

- Initial Steam pilot: `../../steam_pilot.jsonl`
- Crawl settings/counts: `../../steam_pilot_manifest.json`
- Shared project plan: `../../README.md`
- Current train-only development text: `../../steam_history_v3/opinion_train_candidates.jsonl` (85 records in the current pilot).
- Current source/date/content spot-check template: `../../steam_history_v3/source_spotcheck_template.csv` (human labels are still blank).
- Shared temporal contract: `../../../docs/evaluation_contract.md`.

The original 200-review pilot can be used to draft a taxonomy. The v3 opinion file contains 85 detected-English texts judged available before the training cutoff; this is a development set, not a validated aspect-mining corpus. The source/date/content spot-check is incomplete. Use `opinion_train_candidates.jsonl` for training-only user/item opinion features and keep all validation/test text out of those profiles.

## What to extract

For each review, identify zero or more **aspects** (what the reviewer discusses), a **sentiment** for each aspect, and an exact supporting **text span**. Begin by reading reviews and propose about 6-10 aspect categories; possible candidates are gameplay, story, graphics, performance, multiplayer, and value. Keep, merge, or split categories based on actual game-review language.

Example: “Combat feels great, but the story drags.”

- Aspect `gameplay`, sentiment `positive`, evidence `Combat feels great`.
- Aspect `story`, sentiment `negative`, evidence `the story drags`.

Keep `voted_up` separate from these aspect labels. Summarize criticisms in negative-recommendation reviews as **what reviewers say**, not proof of what caused their overall recommendation.

## Tasks and deliverables

1. Read 50 pilot reviews and draft:
   - `outputs/aspect_guide_v0.md`: category names, definitions, inclusion/exclusion rules, and ambiguous examples.
   - `outputs/aspect_annotations_v0.csv`: manual labels with `review_id`, `annotator_id`, aspect, sentiment, evidence span, and notes.
2. Have another teammate independently label an overlapping 10-15 reviews. Resolve disagreements and update the guide.
3. Test one pretrained aspect-based sentiment extractor on the pilot. Benchmark a small batch before processing more data; use Kaggle GPU if local CPU inference is too slow. Do not start a full-corpus run.
4. Save extracted records to `outputs/opinion_extraction_v0.jsonl`. Each record must include `review_id`, `user_id`, `item_id`, `timestamp`, `aspect`, `sentiment`, `evidence`, model/version, and configuration.
5. Produce `outputs/opinion_validation_v0.md`: aspect precision/recall/F1, sentiment results on matched aspects, evidence-span quality, common errors, and counts of criticized aspects among `voted_up=false` reviews. Include denominators and sample spans.
6. Coordinate with Member 3 on an opinion compatibility feature for LightGCN. Build user and game opinion profiles from training-only reviews; send the feature definition and join keys before the model integration.

For the Nov 23 checkpoint, a 50-review annotation pilot and honest extractor status are enough. For the final project, plan roughly 200-300 manually labeled reviews with a held-out evaluation portion and documented annotator overlap.

## Current status (2026-11-23)

Tooling and drafts live on branch `member4/opinion-mining`. See the [validation status report](../../opinion_validation_v0.md) for what has been measured and what is still missing. In short: the [aspect guide](../../aspect_guide_v0.md), the [50-review blinded annotation batch](../../annotation_batch_v0.csv), the extractor/evaluator scripts and the draft [O(u,i) spec](../../opinion_feature_spec_v0.md) are ready. Human labels, the second-annotator overlap and the pretrained-model run are still pending, so no extraction accuracy has been reported yet.

## Completion checklist

- Labels distinguish aspect from sentiment and preserve exact evidence spans.
- `voted_up` is never used as a substitute for aspect sentiment.
- Manual labels include an overlap with disagreements resolved and recorded.
- Extraction results are evaluated against held-out human labels; examples and errors are reported.
- Opinion profiles use only reviews available before each recommendation cutoff.
- Claims about disliked aspects include counts and supporting text; they are descriptive, not causal.

## Start this role in Codex

Open this guide, the original pilot, and the v3 opinion-candidate file in the shared Codex workspace, then paste:

> I own opinion mining and validation. Read this guide and inspect the original pilot, v3 opinion candidates, and source/date/content spot-check status before editing. Draft a small aspect taxonomy based on actual game-review language and prepare the annotation CSV/template and extraction-output schema. I will manually label 50 reviews; do not invent or auto-fill human labels. Arrange an independent 10-15-review overlap with another teammate and record disagreements. In parallel, identify one feasible pretrained aspect-based sentiment model and benchmark a small batch before processing more data. Preserve exact evidence spans and keep Steam `voted_up` separate from aspect sentiment. Use only training-available text when building recommendation features. Produce validation notes and report what is complete, what needs a GPU or human annotation, and any blockers. Keep changes in opinion-mining-owned files and coordinate the feature definition with the graph-model owner.
