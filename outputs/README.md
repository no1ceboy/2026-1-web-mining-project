# Review-Aware Game Recommendation with Web Mining

A Method + System Hybrid capstone: build a bounded crawler and recommendation system, then evaluate how link analysis and opinion mining work together to recommend video games.

**Status:** A Steam API smoke crawl completed on 2026-11-20: 200 reviews from five games are saved under `outputs/steam_pilot.jsonl`, with crawl settings and counts in `outputs/steam_pilot_manifest.json`. No full cleaning, models, or evaluation have been completed. The small pilot has very little cross-game reviewer overlap, so graph suitability remains unproven.

## 1. Motivation and project objective

Game reviews contain searchable descriptions of product features, user opinions, and links between reviewers and products. A star rating compresses this evidence: two games can receive similar averages even when reviewers praise and criticize different aspects.

For example:

> "Excellent combat, disappointing story."
>
> "Wonderful story, frustrating combat."

We will collect a bounded set of public game reviews and build a system that ranks games from a user's past interactions, uses links in the user-item graph, and exposes aspect-level opinion evidence.

**Central question:** How does a classical link-analysis ranker compare with a learned graph recommender, and does adding validated review opinions improve the learned model?

The capstone has two deliverables. The **method** is a controlled ranking experiment with familiar methods and clear evaluation. The **system** includes a requirements/design specification, reproducible crawl-to-recommendation pipeline, source code, and a small demo that shows ranked games with review evidence. The project does not depend on inventing a new neural architecture.

### Course alignment

| Course topic | Project component | Evidence in the capstone |
| --- | --- | --- |
| Link analysis | Personalized PageRank over the user-game interaction graph | Ranking comparison and graph diagnostics |
| Opinion mining | Aspect and sentiment extraction from review text | Manual annotation evaluation and evidence-backed aspect summaries |
| Learned ML method | LightGCN graph recommender | Interaction-only vs. opinion-augmented ranking results |
| Capstone type | Method + System Hybrid | Evaluated ranking method, crawler/graph/opinion pipeline, source code, dataset, and demo |

**Scope choice:** Information retrieval is covered in the course but is excluded from this capstone. The method focuses on link analysis and opinion mining to keep the research question and system coherent.

## 2. Research questions and supporting experiments

| Research question | Experiment or analysis | Evidence to report |
| --- | --- | --- |
| RQ1. How does classical link analysis compare with a learned graph recommender? | Compare Popularity, Personalized PageRank, and LightGCN using the same time split and candidate set | Recall@K and NDCG@K |
| RQ2. Do mined opinions improve learned recommendations? | Compare LightGCN using interactions alone with LightGCN plus an aspect-opinion score | Validation-selected fusion weight and held-out metric change |
| RQ3. What aspects do negative recommendations criticize, and how reliably can we mine them? | Analyze reviews with `voted_up=false`; validate aspect/sentiment extraction against manual labels | Criticism counts with denominators, supporting review spans, precision/recall/F1, and error examples |
| RQ4. When does the hybrid system help or fail? | Analyze performance by user history, item popularity, graph connectivity, and review coverage | Group sizes, group metrics, uncertainty, and evidence-backed cases |

These are questions to test. We do not assume that LightGCN or opinion augmentation will improve results.

## 3. Dataset and feasibility pilot

**Original-crawl candidate:** Steam's official `IUserReviewsService/GetAppReviews` API, collected across multiple game app IDs on Steam. This is one source/platform and many games, not multiple review sites. A smoke request and five-game pilot succeeded from this workspace; other team networks may still differ. Steam's storefront has been reported blocked or restricted on Vietnamese ISPs since 2024, with uneven access reports in 2026, but those reports do not establish that the separate `api.steampowered.com` API is blocked. Steam's current documentation says the API supports cursor pagination and up to 100 reviews per page, does not require a key, and applies lower rate limits to anonymous requests; excessive requests can receive HTTP 429. The older `/appreviews` endpoint is deprecated, so use the current documented API.

Steam is crawlable, not a ready-made local corpus: the team must request pages, follow cursors, save records, and handle rate limits. The API supplies review text, a persistent reviewer ID, creation time, and a binary `voted_up` recommendation label; it does not supply a 1-5 star rating. The app ID is the game ID. Hash reviewer IDs consistently in the saved research data. The released Amazon Reviews 2023 Video Games dataset named in the proposal is the ready-made fallback if the Steam API is inaccessible or a larger Steam sample remains too sparse. Its official page lists 4.6 million Video Games reviews and paired item metadata. The existing 5,000-row Amazon pilot may be used to develop the pipeline, but it is not evidence about a future Steam crawl or the full target population.

### Steam smoke-crawl result (2026-11-20)

We fetched 40 recent English reviews each for Dota 2 (570), Counter-Strike 2 (730), Team Fortress 2 (440), Portal 2 (620), and Left 4 Dead 2 (550), using `purchase_type=all`. All five requests succeeded. The 200 records have 200 unique review IDs, no duplicate IDs, no blank review text, and 199 distinct hashed reviewers; only one reviewer appears on more than one sampled game. The sample contains 121 `voted_up` and 79 negative recommendations, dated 2026-10-21 to 2026-11-20. This is a tiny, recent convenience sample, so low overlap is a warning to test more data, not a final verdict on Steam. Before committing to LightGCN, expand the same-source sample and measure the graph's connected users/items. If overlap remains inadequate, use the Amazon fallback or revise the graph task.

**Next source gate:** test the designated crawler's normal network, then expand to at most 100 recent English reviews each across about 20 Steam game IDs (roughly 2,000 records). Record how many reviewers appear on multiple games and how much of the positive interaction graph is connected. If overlap is still too sparse for warm-start evaluation, switch to the released Amazon dataset; do not merge Steam and Amazon users or interactions.

The target crawl size will be set after the pilot measures collection rate, user-item coverage, and sparsity. Collect one bounded product domain from one source; do not aim to reproduce an entire commercial review corpus.

Required fields:

| Field | Use |
| --- | --- |
| `review_id` | Track each review through raw, cleaned, and mined outputs |
| `user_id` | Identify users |
| `item_id` | Identify games consistently and join product metadata |
| `source_feedback` | Preserve Steam's `voted_up` or Amazon's numeric `rating` without conflating it with text sentiment |
| `positive_interaction` | Normalize Steam `voted_up=true` or Amazon rating 4-5 for the recommendation task |
| `title`, `text` | Extract aspect-level opinions |
| `timestamp` | Establish chronological histories and prediction cutoffs |
| Product title and category | Inspect the domain and distinguish games from accessories or unrelated products |
| `source_url` and crawl time | Trace records to their source and reproduce the collection |

Review timestamps describe reviewed-interaction order, not verified purchase order. Findings must use that interpretation. The dataset also does not contain a complete record of every user's purchases or exposures.

The source feasibility pilot must establish:

- How many users have sufficient historical interactions for evaluation.
- How many items and interactions remain after filtering.
- Missing-text, duplicate, language, and review-length distributions.
- Whether different product types require separate treatment.
- Memory and runtime for one baseline run.
- Crawl success rate, pagination behavior, response rate, and whether collection can resume after interruption.
- Reviewer overlap across games, because the graph model needs connected user-game histories.
- Runtime and cost for extracting evidence from approximately 1,000 reviews.

We will choose the final subset size and filtering thresholds from these measurements. Do not randomly sample individual review rows in a way that fragments user histories. Dataset selection rules must not depend on test performance.

## 4. Web Mining pipeline

The pipeline should produce useful findings independently of the recommendation leaderboard.

### 4.1 Audit and prepare the data

Validate identifiers and timestamps, handle duplicate user-item records consistently, and document all exclusions. Inspect review availability and product types before defining the analysis population.

Deliverables: a reproducible processing script, a data-quality summary, and counts before and after every filtering step.

Prefer a bounded original crawl if a source passes the feasibility check below; this gives the project an end-to-end web data pipeline. Crawling is not valuable just because it is difficult: fetching a few static pages is easy and is not the research contribution. The useful engineering work is reliable pagination, retries/resumption, duplicate control, stable identifiers, timestamp/rating normalization, source provenance, and quality checks while respecting the source's access rules.

Before committing, verify that the source provides review text, stable user and item identifiers, timestamps, and a usable positive-interaction label. Steam's `voted_up` is binary recommendation feedback, not a star rating; for the Amazon fallback, ratings 4 or 5 define positive interactions. Use one platform across multiple game IDs so reviewer identifiers connect the graph. Check page/API access rules, begin with a 100-200-record sample across 3-5 games, and record success rate, duplicates, missing fields, reviewer overlap, and requests per second. If key identifiers are absent or the smoke test is blocked, switch to the released dataset listed in the proposal. Do not let a source problem block cleaning, recommendation, or review-mining work on the pilot/fallback data.

The central Web Mining contribution is the complete, validated path from web reviews to aspect-opinion evidence and tested recommendation insights. Keep raw responses or raw extracted records separate from cleaned data, record crawl time and source URLs, and make the crawler resumable. One member owns the crawl queue and source policy; do not have everyone scrape the same pages. Once the pilot is available, the other three streams proceed in parallel.

### 4.2 Define a small aspect vocabulary

Inspect a sample of training reviews to identify recurring concepts. Start with roughly 6-10 categories and revise them during development. Candidate categories include gameplay, story, graphics, performance, multiplayer, and value. Hardware, delivery, and service comments may need separate categories depending on the selected items.

The vocabulary must come from the actual training data. Do not assume these candidate categories cover the entire dataset.

Deliverables: category definitions, annotation guidelines, and examples of ambiguous cases.

### 4.3 Extract aspect-opinion evidence

Use an established pretrained aspect-based sentiment model or a prompted instruction model. Select the approach based on the pilot's quality, runtime, and available compute. Training a new language model is outside the core scope.

For each extracted opinion, retain:

- Review identifier, user, item, and timestamp.
- Aspect category and the aspect expression when present.
- Sentiment: positive, negative, neutral, or mixed.
- A supporting text span from the original review.
- Extraction model version and configuration.

An illustrative record is:

```json
{
  "aspect": "story",
  "sentiment": "negative",
  "evidence": "the story is repetitive"
}
```

Mentioning an aspect does not automatically establish its importance to a user. A negative opinion about an item's story also does not mean the user dislikes stories. Preserve expressed evidence and distinguish it from inferred preferences.

### 4.4 Validate extraction quality

Manually annotate approximately 200-300 reviews. Have two members independently label an overlapping portion, resolve disagreements, and document difficult cases. Separate development examples from a held-out extraction evaluation sample.

Report aspect detection precision/recall/F1, sentiment performance on matched aspects, evidence fidelity, and common errors. Do not use generated explanations or model confidence as substitutes for human validation.

### 4.5 Mine and interpret patterns

Prioritize these analyses:

1. **Criticized aspects:** Among reviews with `voted_up=false`, which aspects are most often criticized? Report review counts and denominators, and show supporting spans. This describes what reviewers say; it does not establish that an aspect caused the negative recommendation.
2. **Opinion disagreement:** Do games with similar overall recommendation rates have different aspect-level opinion distributions? Separate negative/positive disagreement from neutral opinions and missing evidence. Always show supporting review counts.
3. **Information availability:** Which users and games have little interaction evidence but useful review coverage?
4. **Ranking disagreement:** When Personalized PageRank and LightGCN disagree, how do their outcomes relate to connectivity, recent history, and review evidence?

Optional extension: changes in expressed opinions over time, if enough timestamped evidence remains after filtering.

Deliverables: validated opinion records, item/group profiles, a small set of explanatory figures, and cases linked to original review evidence. Report associations rather than claim causal explanations.

### 4.6 Pilot test and current findings

On 2026-11-16, we smoke-tested the data and aggregation path on 5,000 records from the beginning of the Video Games review file. This was a convenience sample, not a random or representative sample. We did not download or audit the complete category file.

| Check | Pilot result | What it tells us |
| --- | --- | --- |
| Read and inspect JSONL rows | 5,000 rows in 0.25 seconds | Local parsing is fast for a small sample; this does not include downloading the full data |
| Sample coverage | 1,610 users, 3,766 parent product IDs, no blank review bodies, and 32 repeated user-product pairs | Deduplication and interaction definitions need to be explicit |
| Candidate aspect matching | 5,000 rows in 2.66 seconds, about 1,877 rows/second | Rule-based matching is fast enough for a smoke test |
| Candidate matches | 2,724 reviews had at least one keyword match; hardware/accessory patterns were especially frequent | The candidate vocabulary may be mixing games with controllers and other products |
| Semantic model inference | Not completed | No model extraction rate or GPU runtime has been measured |

The prototype retained sentence evidence and counted category mentions, but it used curated keyword rules and did not predict aspect polarity. It produced false matches: for example, a graphics/audio pattern matched a sentence about a graphic designer, and a gameplay pattern matched a sentence about volume control. These results are not ABSA accuracy or final project findings. They show why the team must inspect examples and validate the extractor.

The review sample also contains products that appear to be accessories and unrelated merchandise. Before finalizing the aspect vocabulary or analyzing recommendations, join product IDs to the official metadata and define the target product population. Do not interpret the sample-level rates as category-wide rates.

We attempted to fetch the end-to-end ABSA candidate model `yangheng/deberta-v3-base-end2end-absa`, whose model card describes aspect-span and sentiment extraction. Its weight file is 735 MB. The fetch did not complete in this environment, which has no CUDA GPU. A separate 1 MiB range request took 11.3 seconds; a straight-line extrapolation would put this model file near 2.2 hours on this connection. That is only a local transfer estimate. It says nothing reliable about Kaggle bandwidth or inference speed. The selected model is also not yet validated on video-game reviews, so domain accuracy remains an open risk.

### 4.7 Revised Web Mining stage estimate

After the crawl pilot and metadata audit, choose a stratified, training-only sample for aspect-opinion mining. Preserve all interaction records needed for recommendation evaluation; mine text only for the selected sample and expand it only if the first GPU throughput and quality checks justify it. Prioritize connected user-item histories over a large raw review count.

| Work | Estimated team effort | Calendar allowance with parallel work |
| --- | ---: | ---: |
| Check source feasibility, publish a 100-200-record crawl pilot, and audit fields | 5-8 person-hours | 1-2 days |
| Expand a successful crawler to the bounded target and check coverage/recovery | 6-12 person-hours, source-dependent planning estimate | 1-3 days after the pilot |
| Join product metadata and filter product types | 3-6 person-hours | 0.5-1 day |
| Define the aspect vocabulary and annotation guide from training reviews | 4-6 person-hours | 0.5-1 day |
| Set up the extractor, time a 1,000-review GPU benchmark, then process the selected training-only sample | 5-10 person-hours, plus machine runtime | 1-2 days after GPU access |
| Manually label 250-300 reviews, include an overlap, and resolve disagreements | 4-6 person-hours | 0.5-1 day |
| Build opinion profiles, analyze disagreement/coverage, and make figures | 6-10 person-hours | 1-2 days |

**Planning estimate:** about 33-58 team person-hours, or 5-8 calendar days with parallel work, including an original bounded crawl that passes its pilot. The crawl allowance is source-dependent and has not been benchmarked; revise it after the smoke sample. Keep 1-2 extra calendar days for access delays, model/data transfer, an extractor revision, or a rerun. The inference estimate is not measured yet; on the first GPU session, benchmark 1,000 reviews and calculate `estimated runtime = target review count / measured reviews per second`. Do not plan to extract all 4.6 million reviews in the Amazon fallback until that benchmark demonstrates it is necessary and practical.

The main schedule risks are source access, stable user-item identifiers, and video-game domain accuracy, not JSONL parsing. If GPU access is delayed, continue the annotation guide and crawl/data-quality audit while the model benchmark is pending.

## 5. Core methods

| Method | Course area | Role in the project |
| --- | --- | --- |
| Popularity | Reference baseline | Rank games by positive historical interaction count. |
| Personalized PageRank | Link analysis | Run a random walk with restart from the target user on a bipartite user-game graph; rank unseen games by their resulting scores. |
| LightGCN | Learned graph recommendation | Learn user and game representations by propagating interaction signals over the training graph. This is the required ML recommender. |
| Aspect-opinion compatibility | Opinion mining | Compare a user's training-only aspect sentiment profile with each candidate game's mined opinion profile. |

Use these established methods faithfully. LightGCN is the only required learned recommender. Defer BPR-MF, SASRec, and additional neural architectures so the crawler, opinion validation, and fair evaluation remain achievable.

## 6. Hybrid ranking and experiment matrix

For a user `u` and candidate game `i`, let `L(u,i)` be LightGCN's normalized interaction-only score, and `O(u,i)` the normalized compatibility between the user's historical aspect preferences and the game's mined aspect opinions. The opinion-augmented score is:

```text
score(u, i) = (1 - alpha) * L(u, i) + alpha * O(u, i)
```

Choose `alpha` between 0 and 1 using validation data only. Fix the normalization procedure before test evaluation. If an aspect profile is unavailable, fall back to the LightGCN score for that candidate.

Run these configurations with the same users, time cutoffs, candidate games, and metrics:

| Configuration | What it tests |
| --- | --- |
| Popularity | Simple recommendation reference |
| Personalized PageRank | Link-analysis signal alone |
| LightGCN | Learned graph recommender using interactions alone |
| LightGCN + opinion score | Whether validated aspect opinions add useful evidence to a learned recommender |

The primary review data for ranking must come from before each prediction cutoff. Keep later reviews out of user profiles, item opinions, and the graph. Show the supporting review span for opinion-based results in the demo. Personalized PageRank is the course-aligned link-analysis method; LightGCN is the learned ML method.

## 7. Fair evaluation protocol

### 7.1 Task and chronological access

Recommended starting task: predict a user's next positively reviewed, previously unseen game. For Steam, define a positive interaction as `voted_up=true`; for the Amazon fallback, use a rating of 4 or 5. Preserve negative Steam reviews for opinion mining, but do not treat unobserved games as verified dislikes.

Prefer shared global time cutoffs to prevent another user's future review from entering an earlier prediction:

1. Train on interactions and reviews before the validation cutoff.
2. Evaluate the first eligible positive interaction per user in the validation window.
3. Select hyperparameters using validation results.
4. Refit the selected configurations on all eligible history before the test cutoff.
5. Evaluate the first eligible positive interaction per user in the test window.

At each cutoff, build the user-game graph from earlier interactions and compute user/item opinion profiles only from reviews already available. Freeze these inputs for the prediction window so every ranking method uses the same history.

Build graphs, review profiles, aspect vocabularies, and learned preprocessing from permitted historical data only. Never include the target interaction or its review in a prediction. Analyze held-out text only after predictions are fixed, if needed for clearly labeled retrospective error analysis.

Exclude all previously reviewed items from candidates, including items with low historical ratings. Compute average ratings, review counts, and aspect summaries from the relevant historical window; do not use collection-wide metadata aggregates as if they were available at an earlier prediction time.

Begin with warm-start evaluation: eligible users and items must be represented in training. Determine eligibility from training history, document exclusions, and report coverage. Do not present these results as evidence of zero-history cold-start performance.

### 7.2 Metrics and comparison controls

- Primary metrics: Recall@10/20 and NDCG@10/20.
- Use identical evaluation users, target interactions, candidate sets, and seen-item exclusions across methods.
- Prefer full eligible-catalog ranking. If candidate sampling is necessary, fix the same candidates for every method and disclose the protocol.
- Choose score weights and any thresholds on validation data only.
- Repeat stochastic components with three seeds where practical; fixed Personalized PageRank runs may be deterministic.
- Report paired per-user uncertainty for important differences where feasible.
- Record training time, inference time, peak memory, and hardware alongside ranking quality.

With one relevant target per user, Recall@K and HitRate@K coincide. Reporting both would not add evidence.

### 7.3 Subgroup analysis

Start with training-history groups of 5-10, 11-30, and more than 30 positive interactions, provided enough users remain in each group. If the pilot requires different thresholds, establish them before examining test outcomes.

Also examine training item popularity, graph connectivity, and review coverage. Compute group definitions from historical data. Show group sizes and account for overlapping factors: an apparent text benefit may also reflect history length or item popularity.

The main effect is the change from LightGCN using interactions alone to LightGCN with aspect-opinion evidence. Use Personalized PageRank to compare learned graph recommendation with classical link analysis. Explain gains and failures using review coverage, history length, popularity, and graph connectivity rather than reporting one aggregate score alone.

## 8. Team responsibilities

Use four parallel technical workstreams. If the group has four people total, the project lead also owns one workstream. If there are four teammates plus you, the lead coordinates the shared protocol and integration while helping with annotation and analysis; do not leave the lead with coordination only.

| Owner | Primary ownership | Shared obligations |
| --- | --- | --- |
| Member 1: crawler and provenance | Test source access; implement a bounded, resumable crawler; record source, collection counts, failures, and field coverage; audit product metadata. Use the released dataset as fallback if the pilot fails. | Publish a small raw pilot early and produce the crawl/data-quality summary |
| Member 2 (you): data pipeline and evaluation | Parse, deduplicate, join metadata, filter the target population, create the chronological split and shared data loader; implement the evaluator and Popularity baseline | Build the pipeline on the pilot while acquisition continues; report counts, exclusions, and baseline metrics |
| Member 3: graph recommenders | Implement Personalized PageRank and LightGCN using the shared data loader and evaluator | Start with the pilot, report metrics/runtime, and rerun both methods on the frozen clean snapshot |
| Member 4: opinion mining | Define aspect labels, pilot a pretrained aspect-opinion extractor, manually check examples, and implement the opinion compatibility score for LightGCN fusion | Work from the pilot while the full dataset is prepared; report extraction quality, errors, and opinion-augmented results |

Target roughly 6-8 focused hours per person before the progress report. The source owner should publish a pilot early; the other owners can build against that sample while the crawl continues. Everyone should contribute to the overlapping annotation check, interpretation, writing, demo integration, and presentation. These are ownership areas, not isolated projects.

Role-specific, self-contained work guides for teammates who are new to the project:

- [Member 1: crawler and data provenance](team_guides/member1_crawler/README.md)
- [Member 3: Personalized PageRank and LightGCN](team_guides/member3_graph_models/README.md)
- [Member 4: opinion mining and validation](team_guides/member4_opinion_mining/README.md)

## 9. Timeline and compute plan

**Planning assumption:** four core workstream owners, each contributing approximately 10 hours per week. A five-to-six-week project therefore has roughly 200-240 person-hours; if the group has a fifth member, that person can add integration and analysis capacity. Availability still needs confirmation.

| Week | Work and exit milestone |
| --- | --- |
| 1 | Check source, freeze schema and split, build the pilot, and run Popularity and Personalized PageRank; start LightGCN |
| 2 | Expand the bounded crawl, complete cleaning, and evaluate aspect-opinion extraction on manual labels |
| 3 | Complete LightGCN and integrate its opinion augmentation; build the demo and freeze the validation-selected weight |
| 4 | Run the full ablation matrix and repair reproducibility or evaluation issues |
| 5 | Complete subgroup comparisons, opinion-disagreement analysis, cost measurements, and report draft |
| 6 | Buffer for justified reruns, final report, presentation, and a small demo |

The Web Mining stage has a revised estimate of 5-8 calendar days with parallel team work, plus 1-2 days of compute and rerun contingency (Section 4.7). It can overlap recommendation implementation. Set the text-mining sample size after the crawl pilot and measured extraction throughput; do not target the entire 4.6-million-review Amazon fallback corpus.

### Immediate sprint for the Nov 23 progress report

The report is due Monday, Nov 23, 2026. Use Nov 20-22 to prepare a short, evidence-based progress update. The goal is to show a defensible scope, a working data/evaluation path, and at least one preliminary experiment. For this deadline, a successful crawler smoke sample plus a documented go/no-go decision is enough; do not claim the full target collection is complete unless it is. Treat unfinished models and the untested ABSA model as work in progress.

The four workstreams run in parallel, not as four sequential handoffs. Freeze a small shared schema on Nov 20 and exchange a pilot snapshot early. Use these fields: `review_id`, `user_id`, `item_id`, `timestamp`, `crawl_time_utc`, `source_feedback`, `positive_interaction`, `title`, `text`, and `source_url`. If crawling, publish a 100-200-record sample across 3-5 game IDs as soon as it works; later pages append records without changing the schema. If using the public dataset, publish the same kind of pilot after acquisition/filtering. The cleaner, graph/recommendation owner, and opinion-mining owner begin on that pilot or the existing sample, then rerun on the cleaned snapshot when it is ready. Set two fixed sync points per day; do not wait for the full data collection before starting other work. Aim for roughly 6-8 focused hours per person before the report, with tasks adjusted if one workstream hits a real blocker.

### 30-minute kickoff agenda

1. **Motivation and scope (5 min):** Reviews reveal aspect-level praise and criticism that an overall recommendation flag does not explain. The project combines link analysis, LightGCN, and validated opinion mining; Information Retrieval is excluded.
2. **Pilot and source gate (5 min):** Show the 200-review Steam pilot and its single cross-game reviewer. Expand the same-source sample once and review graph overlap by Nov 21; use Amazon if the graph remains too sparse.
3. **Assign owners (10 min):** Confirm one owner for crawling, one for cleaning/evaluation (Member 2, you), one for PPR/LightGCN, and one for opinion extraction/annotation.
4. **Shared contract (5 min):** Freeze the schema, positive-label mapping, output paths, and dataset version names.
5. **Check-in (5 min):** Each owner states their first artifact and when they will report it. Use two short sync points per day until the Nov 23 checkpoint.

| Workstream | Starts immediately on | Handoff for integration |
| --- | --- | --- |
| Crawl/acquire | Target source, agreed schema, and a 100-200-record smoke sample; stop for a go/no-go decision if required fields or access are missing | Append-only raw JSONL plus source notes, crawl counts, and failure/retry counts |
| Clean | Schema and smoke sample; write validation, deduplication, and parsing steps while collection continues | Versioned clean file plus exclusion counts and a split manifest |
| Data pipeline/evaluation | Schema and smoke sample; build cleaning, split, shared evaluator, and Popularity before waiting for the final clean file | Versioned clean data, split manifest, runnable evaluator, and baseline metrics |
| Graph recommenders | Existing/pilot data and the shared evaluator; implement Personalized PageRank and LightGCN | Runnable model configs, metrics/runtime, and later reruns on clean snapshot v1 |
| Review mining | Pilot reviews; draft aspect labels and manually inspect examples while extraction setup proceeds | Aspect/opinion records with review evidence, a small annotation check, and known errors |

The only hard integration dependency is the clean snapshot for final comparable metrics. Freeze `clean_v1` by Nov 22 noon; any later additions belong in a new version and should not silently change reported results. If collection is late, report the pilot sample and keep the population claim provisional rather than blocking the other workstreams.

| Date | Owner and work | Evidence ready by end of day |
| --- | --- | --- |
| Fri, Nov 20 | The lead runs the kickoff and owns one of the four streams. Member 1 tests Steam access from their normal network and starts expanding the pilot. Member 2 cleans the existing 200 reviews and builds the shared loader, evaluator, and Popularity baseline. Member 3 measures graph coverage, runs PPR, and starts LightGCN feasibility work. Member 4 drafts aspect labels and manually checks pilot reviews while testing extraction. | Frozen schema and owners, clean_v0 counts, graph coverage summary, source-access status, baseline status, and draft annotation guide |
| Sat, Nov 21 | Member 1 reports expanded-crawl counts and reviewer overlap for the Steam go/no-go decision. Member 2 publishes the latest versioned clean snapshot, exclusions, split, and Popularity metrics. Member 3 reports PPR and LightGCN implementation/runtime status. Member 4 reports extraction examples and manual-label agreement on an overlapping subset. The lead resolves blockers and checks cross-stream consistency. | Source decision, data-quality summary, split manifest, baseline results/status, opinion-mining examples, annotation disagreements, and known limitations |
| Sun, Nov 22 | The lead integrates the report. All members verify their section, consolidate evidence, and rehearse a 5-7 minute update. | Final progress report/slides with completed, in-progress, blocked, and next-step items clearly separated |
| Mon, Nov 23 | Submit/present the progress report. | Report delivered; assign follow-up tasks for the full project |

**Minimum credible report:** problem and research questions; course-to-project mapping; crawl pilot and go/no-go decision; selected data and split counts; one completed baseline run, with LightGCN implementation status; the review-mining prototype and its false-positive examples; current blockers; next milestone. If the crawler, LightGCN, or opinion extractor is not ready, report its measured status and do not invent a result. Do not describe the existing 5,000-row Amazon convenience sample as representative of a new crawl or the full category.

Do not start BPR-MF, SASRec, extra representations, a large model sweep, or full-corpus ABSA before Nov 23. LightGCN is in scope, but limit it to a pilot run for the progress report. Keep all ranking methods on the same data snapshot, candidate set, and metric code. If product metadata is not ready, present the dataset as an unfiltered pilot and keep the final domain claim provisional. Use Kaggle first; rent compute only if a measured workload cannot fit available GPU time.

Use free Kaggle GPU resources for pilots and development where available. Consider renting a Vast.ai instance for measured workloads that exceed available resources. Do not commit to a rental duration or API budget until the pilot establishes throughput, storage needs, and cost.

Cache preprocessing and text features, save checkpoints, and keep runs resumable. Avoid large sweeps before confirming that small end-to-end experiments are correct.

## 10. Deliverables and completion criteria

- A system requirements/design specification, documented resumable crawler, source-provenance log, data-processing pipeline, and chronological split specification.
- A user-game graph with Personalized PageRank, a LightGCN implementation, and shared evaluation code.
- Validated aspect-opinion extraction, annotation guidelines, and held-out extraction evaluation.
- Ablation results for Popularity, Personalized PageRank, LightGCN, and LightGCN with the opinion-aware score.
- Overall and subgroup ranking metrics, uncertainty, crawl/data-quality measures, and computational costs.
- Opinion-disagreement findings and evidence-backed success/failure cases.
- Source code, a bounded dataset or reproducible collection instructions, report, and presentation.
- A small demo that returns ranked games and supporting review evidence for an eligible user. Any displayed explanation must be supported by an actual review span.

The project succeeds if it answers the research questions with trustworthy evidence, even if text does not improve every model. Distinguish a failed hypothesis from an incomplete or unfair experiment.

## 11. Scope controls and decisions still open

| Issue | Response |
| --- | --- |
| Too few eligible histories | Inspect before committing to personalized graph ranking; revise the subset or domain using documented criteria |
| Extraction quality is weak | Refine aspect definitions or the extractor using development data, then evaluate on held-out annotations |
| Compute is limited | Reduce subset size and tuning breadth while preserving the shared protocol |
| Review augmentation gives little gain | Examine coverage, score scaling, and extraction/profile quality; report supported negative findings |
| The study becomes too broad | Keep the four core ranking configurations; defer BPR-MF, SASRec, temporal analysis, and extra representations |

Still to confirm: member names/availability, instructor rubric, selected crawl source and its access rules, final subset size, exact time cutoffs, filtering thresholds, extraction model, normalization rule, and rental/API budget. The progress report deadline is Nov 23, 2026.

The current preference is an original, bounded crawl, subject to the source feasibility check. The released web-derived dataset named in the proposal is the fallback, not a second full data source.

Suggested repository organization once implementation begins:

```text
README.md
configs/        # Data, model, and experiment settings
src/            # Processing, mining, models, and shared evaluation
scripts/        # Reproducible entry points
data/           # Ignored raw/processed data and cached features
results/        # Compact metrics and experiment summaries
reports/        # Figures, report, and presentation
```

Keep large datasets, embeddings, and checkpoints out of version control. Remove temporary debug scripts, redundant outputs, and abandoned experiment artifacts after reviewing them. Retain the configurations and compact logs needed to reproduce reported results.

## 12. References

- [Amazon Reviews 2023: dataset, schema, and category statistics](https://amazon-reviews-2023.github.io/)
- [Steamworks: IUserReviewsService/GetAppReviews API](https://partner.steamgames.com/doc/webapi/IUserReviewsService?l=english)
- [VnExpress: Steam services blocked or restricted in Vietnam, May 2024](https://e.vnexpress.net/news/business/companies/gaming-platform-steam-blocked-in-vietnam-for-refusal-to-cooperate-with-authorities-4752391.html)
- [Inven Global: reports of wider Steam access problems in Vietnam, October 2026](https://labs.invenglobal.com/articles/26798/steam-effectively-blocked-in-vietnam-issues-extend-to-downloads-and-updates)
- [Rendle et al. — BPR: Bayesian Personalized Ranking from Implicit Feedback](https://proceedings.mlr.press/r7/rendle09a.html)
- [He et al. — LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation](https://arxiv.org/abs/2002.02126)
- [Kang and McAuley — Self-Attentive Sequential Recommendation](https://arxiv.org/abs/1808.09781)
- [Reimers and Gurevych — Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks](https://arxiv.org/abs/1908.10084)
- [Pontiki et al. — SemEval-2014 Task 4: Aspect Based Sentiment Analysis](https://aclanthology.org/S14-2004/)
- [Yangheng — end-to-end ABSA model card considered for the extraction pilot](https://huggingface.co/yangheng/deberta-v3-base-end2end-absa)

The schedule, scope choices, and proposed analyses above are planning judgments. The references establish the dataset and methods; they do not establish outcomes for our experiments.
