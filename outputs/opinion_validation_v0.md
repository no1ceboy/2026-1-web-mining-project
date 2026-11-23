# Opinion Extraction Validation v0: Status

Date: 2026-11-23. Owner: Member 4. Branch: `member4/opinion-mining`.

**Summary: no extraction-quality metric exists yet.** Precision, recall and F1 need human labels, and the 50-review annotation batch is prepared but not yet labelled. Everything below is infrastructure, runtime and coverage. None of it is evidence of extraction accuracy.

## Status by deliverable

| Deliverable | Status | Evidence |
| --- | --- | --- |
| Aspect guide | Draft v0 done | [aspect_guide_v0.md](aspect_guide_v0.md): 10 aspects + `overall` / `none`, sentiment and span rules, 12 ambiguous pilot cases |
| Annotation batch | Ready | [annotation_batch_v0.csv](annotation_batch_v0.csv): 50 reviews, 10 per game, 16 not recommended, 15 overlap. `voted_up` is hidden. Selection in [manifest](annotation_batch_v0_manifest.json) |
| Human labels (50) | **Not started.** Needs Member 4 | [aspect_annotations_v0.csv](aspect_annotations_v0.csv) has a header only |
| LLM pre-annotation draft (50) | Done. **Not gold** | [aspect_annotations_v0_claude_draft.csv](aspect_annotations_v0_claude_draft.csv): 189 rows by `claude_draft`, all spans validated. A human must review and correct each row before it goes into the gold file under their own `annotator_id`. Do not use it as the second "independent" annotator, and do not report extractor scores against it as human-validated |
| Overlap (15) by second annotator | **Not started.** Needs a teammate | Same CSV, different `annotator_id` |
| Baseline extractor | Runs | `scripts/opinion_extract.py --backend lexicon` → [opinion_extraction_v0.jsonl](opinion_extraction_v0.jsonl) |
| Pretrained ABSA extractor | Implemented, **not run** | `--backend hf-absa` (default `yangheng/deberta-v3-base-absa-v1.1`); torch/transformers not installed here |
| Evaluator | Done, smoke-tested | `scripts/opinion_evaluate.py`: span validation, agreement (pair F1, kappa), P/R/F1, sentiment on matched pairs, span token-F1, criticized-aspect counts |
| O(u,i) definition | Draft for Member 3 | [opinion_feature_spec_v0.md](opinion_feature_spec_v0.md), `scripts/opinion_profiles.py` |
| Criticized aspects among `voted_up=false` | Pending gold labels | Will be computed from adjudicated labels with denominators |

## Extractor pipeline

1. Split each review into clauses: sentence punctuation, newlines, `;`, "but", "however". Each clause is an exact substring with stored offsets, so evidence can be shown verbatim in the demo.
2. Detect candidate aspects with the cue lexicon in [configs/aspect_lexicon_v0.json](../configs/aspect_lexicon_v0.json).
3. Assign sentiment toward each cue. The **lexicon** backend uses polarity words with negation in a 3-token window. The **hf-absa** backend uses a pretrained aspect-sentiment classifier on (clause, cue term).
4. Emit `review_id, user_id, item_id, timestamp, aspect, aspect_term, sentiment, evidence, evidence_start, evidence_end, confidence, model, model_version, config, run_id`.

The hf-absa backend is an aspect-*sentiment* model. Aspect *detection* still comes from the lexicon in both backends, so the aspect recall of both is limited by the lexicon. If recall is the weak point after labelling, the next candidate is an end-to-end extractor (for example `yangheng/deberta-v3-base-end2end-absa`) or a prompted instruction model scored on the same held-out labels.

## Runtime measured so far

| Run | Reviews | Records | Time | Hardware |
| --- | ---: | ---: | ---: | --- |
| Lexicon, annotation batch | 50 | 212 (48 reviews with ≥1 record) | 0.06 s | Intel CPU |
| Lexicon, v3 cohort opinion candidates | 85 | 538 | 0.21 s | Intel CPU |
| hf-absa | — | — | not run | A local RTX 5070 Ti is available; needs a CUDA build of torch |

## Baseline errors seen while drafting the guide

These come from reading the lexicon output on the batch. They are qualitative and **not a measured error rate**.

| Review | Extracted | Problem |
| --- | --- | --- |
| 238229946 "YOU ARE FREE" | `value_monetization` / neutral | The word "free" is not about price |
| 238423549 "a real system that looks at actual words" | `audiovisual` / negative | "looks" matched as a visual cue |
| 239662439 "close to the level of CS:GO" | `modes_content` / neutral | "level" means quality, not a game level |
| 238229946 "highly recommended game" | `overall` / neutral | Polarity lexicon misses "recommended" |
| 240343903 "Great game for anyone who wants to develop trust issues" | `overall` / mixed | Sarcasm; the real target is other players |
| 239628772 "very good game if you want russians to yell at you" | `overall` / positive | Sarcasm; should be `players_community` negative |

These match the risks in the project assessment: slang, sarcasm and short meme reviews. Sarcasm is common in the Dota 2 and CS2 reviews, so the guide tells annotators to tag it so the report can give extractor accuracy separately on sarcastic and non-sarcastic reviews.

## Coverage of O(u,i) on the v3 pilot

See [opinion_feature_spec_v0.md](opinion_feature_spec_v0.md#pilot-coverage-lexicon-baseline-unvalidated). In short, 14/22 validation and 10/23 test target users have a profile, and about 30% of validation (user, game) pairs and 20% of test pairs have a score. Most candidates would fall back to LightGCN.

## Next steps

1. **Member 4:** review and correct the 189-row LLM draft against the guide, then save the corrected rows to `aspect_annotations_v0.csv` under your own `annotator_id` (estimate 1–1.5 h).
2. **A teammate:** label the 15 `overlap=yes` reviews independently. Then run the evaluator, adjudicate, and update the guide.
3. Install a CUDA build of torch with transformers locally (or use Kaggle). Run `--backend hf-absa` on the batch, then score both backends with `opinion_evaluate.py`.
4. Label a further 150–250 reviews for a **held-out** evaluation split, drawn from the 100-game catalogue so the taxonomy is tested beyond five Valve games. Score extractors only on that split, using `--eval-ids`.
5. Agree on the O(u,i) contract with Member 3. Ask the data owner for opinion candidates available before the test cutoff.

## Reproduce

```bash
python scripts/opinion_select_batch.py
python scripts/opinion_extract.py --review-ids outputs/annotation_batch_v0.csv
python scripts/opinion_evaluate.py            # after labels are added
python scripts/opinion_extract.py --input outputs/steam_history_v3/opinion_train_candidates.jsonl \
       --output outputs/opinion_profiles_v0/cohort_extraction_lexicon.jsonl
python scripts/opinion_profiles.py --split validation --extraction outputs/opinion_profiles_v0/cohort_extraction_lexicon.jsonl
python scripts/opinion_profiles.py --split test --extraction outputs/opinion_profiles_v0/cohort_extraction_lexicon.jsonl
python -m unittest tests.test_opinion_mining
```
