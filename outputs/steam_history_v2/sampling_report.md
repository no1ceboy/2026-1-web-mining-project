# User-history sampling audit

Version: `steam_history_v2`. Generated 2026-11-21T12:16:24.992860Z.

Collection status: **paused_profile_budget**. Planning gate passed: **False**.

This report evaluates a new acquisition strategy, not a claim that filtering single-review users fixes the original population. The target population is explicitly a train-defined active-reviewer cohort.

| Check | Value |
| --- | ---: |
| Seed users discovered using pre-cutoff API records | 4766 |
| Profiles attempted | 50 |
| Raw in-catalog reviews discovered | 122 |
| Users with discovered in-catalog reviews, before cohort filtering | 50 |
| Selected users (>=3 positive training games) | 10 |
| Selected review records | 60 |
| Observed games in selected cohort | 42 |
| Fixed catalogue games | 100 |
| Positive reviews | 55 |
| Negative reviews | 5 |
| Blank texts retained as interactions | 1 |
| Short texts flagged separately | 54 |
| English text candidates available before training cutoff | 5 |

## Distribution before filtering the cohort

Do not present the selected cohort's minimum degree as an improvement in the whole Steam population. The following includes every user with an observed in-catalog review, including incomplete profiles.

| Distinct positive games observed | Users |
| --- | ---: |
| 1 | 32 |
| 2 | 6 |
| 3 | 5 |
| 4 | 1 |
| 5 | 2 |
| 6 | 1 |
| 7 | 1 |
| 10 | 1 |
| 12 | 1 |

## Chronological coverage

| Check | Validation | Test |
| --- | ---: | ---: |
| Historical positive edges | 53 | 54 |
| Warm items | 37 | 38 |
| Eligible target users | 0 | 0 |
| Targets with >20 candidates | 0 | 0 |
| Candidate count, min..max | 0..0 | 0..0 |

The windows are proposed coverage diagnostics, not Recall/NDCG results. A user is never required to have a future target to enter the training cohort. Evaluation eligibility is subsequently reported per window.

## Acquisition versus filtering

- Profile statuses: `{'complete': 49, 'unavailable': 1}`.
- Cohort exclusions: `{'insufficient_training_positive_games': 39, 'profile_not_complete': 1}`.
- Matched positive users in the old snapshot and complete new profiles: 0. Observed positive edges for those matched users: old 0, new 0.
- This matched comparison has a different discovery window and source method. It measures additional observed history for shared users, not a causal or representative population comparison.

## Limits and next actions

- Do not report 10,000 new cohort reviews or 100 observed cohort games unless the table actually reaches those counts. The 100-game catalogue is a frame, not a quota that is forcibly filled.
- Exact 10,000-row truncation is incompatible with preserving complete user histories and train-only membership. The row count is a planning target; the cohort size and hard HTTP budget govern collection.
- Incomplete/private/parse-failed profiles are excluded from the cohort and counted; this introduces public-profile/nonresponse bias. Public pages can shift during collection and are not immutable snapshots.
- Public dates have day precision and an unknown timezone. The +38h bound is conservative for UTC offsets within +/-14h, conditional on the displayed date being correct. Missing edit dates are assumed unedited by the UI, not guaranteed by an API; manually validate a spot sample before final historical claims.
- Matching seed interactions are anchored to exact API times when review ID, app, label and displayed date bounds agree. This does not assign exact times to other records or relax the public text availability bound.
- Keep multilingual/short/blank review interactions; English detection and a minimum 20-token rule affect the opinion-training view only. Detector scores are not calibrated accuracy, and these flags do not validate aspect extraction or remove all memes.
- Popularity means positive count in this conditional cohort. Quota-free cohort acquisition does not estimate full-platform popularity, and no inverse-probability weighting is claimed.
- This config targets 500 cohort users and approximately 10000 reviews. The evaluation planning gate requires at least 500 cohort users and 100/100 eligible validation/test users with >20 candidates. If unmet, report the failure, resume within the registered budget or reconsider the source; never choose a different split based on ranking metrics.
- Coordinate split/loader contracts with the evaluation owner. These files are sampling/coverage evidence; no recommendation models or gold human annotations were fabricated.
