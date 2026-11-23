# Project scope and current status

**Project:** Review-Aware Recommendation from User-Generated Content
**Checkpoint:** Progress report, 23 November 2026
**Team:** Four members

## Motivation

Steam provides an overall recommendation vote for each review, while the review text can describe specific praise or criticism. The project asks whether user-game links support useful game rankings and whether aspect-level opinions in the text add evidence to those rankings.

The course topics addressed are link analysis and opinion mining. Information retrieval is outside the project scope. The current checkpoint package consists of the report, source code, and documented datasets.

## Method

The study compares three ranking methods on a common time-based evaluation: a Popularity baseline, Personalized PageRank, and LightGCN. It also proposes a fourth comparison, LightGCN combined with aspect-level opinion features. This fourth comparison is not ready for evaluation because the opinion labels have not been validated and the available text coverage is limited.

The recommendation graph uses unique positive user-game interactions available before a cutoff. Negative reviews remain available for opinion analysis and for excluding games already reviewed by a user. A game without an observed review is not treated as a confirmed dislike.

Two Steam snapshots serve different purposes:

1. The 10,000-review quota snapshot supports collection and overlap assessment. It has too few users with multiple positive game reviews for the current personalized-ranking evaluation.
2. The v3 history sample was designed for time-based ranking. It contains 54 selected users, 554 reviews, and 95 observed games. It is a pilot, not a representative sample of Steam users.

The two snapshots must not be combined. Sampling details, timestamp rules, and the coverage gate are documented in [sampling_design.md](sampling_design.md) and the [v3 sampling report](../outputs/steam_history_v3/sampling_report.md).

## Current evidence

- The shared loader, split checks, data-quality audit, and Popularity baseline are implemented.
- Personalized PageRank and LightGCN have run on the shared v3 split.
- The v3 evaluation contains 22 validation targets and 23 test targets. The registered planning gate requires at least 500 users and 100 eligible users in each holdout with more than 20 candidates; it is not met.
- An aspect guide, annotation workflow, lexicon extractor, and opinion-profile calculation are implemented.
- The 50-review human annotation batch has not yet been labeled. There is no human-validated extraction score and no final comparison of LightGCN with opinion features.
- A 20-review public-source, date, and content spot-check remains incomplete.

The current counts, model metrics, and next steps appear in the [progress report](../reports/Group9_ProgressReport.tex).

## Completion criteria for the final study

1. Resolve the data-size decision: collect a larger sample under a new version or explicitly narrow the claims to the available pilot.
2. Complete source and date checks and publish before/after counts for every data-processing rule.
3. Freeze one dataset and time split before model tuning.
4. Run Popularity, Personalized PageRank, and LightGCN on the same candidate sets; report coverage with every metric.
5. Complete independent human annotation and held-out evaluation of aspect and sentiment extraction.
6. Generate cutoff-specific opinion features and evaluate their contribution to LightGCN without using future review text.
7. Report uncertainty, failure cases, and limits on generalizing beyond the sampled Steam users.

## Team responsibilities

| Member | Responsibility |
|---|---|
| 1 | Data collection, source checks, and sampling coverage |
| 2 | Data preparation, shared split, evaluation, and baseline |
| 3 | Personalized PageRank and LightGCN |
| 4 | Aspect categories, opinion extraction, and human validation |
