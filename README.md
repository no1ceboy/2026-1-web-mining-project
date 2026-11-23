# Game Recommendation from Steam Reviews

**Web Mining Capstone | Progress report, 23 November 2026**

## Project summary

This project studies whether public Steam reviews can support game recommendations and whether aspect-level opinions in review text add useful evidence beyond a review's overall recommendation vote. The study combines web data collection, link analysis, recommendation, and opinion mining. Information retrieval is outside the project scope.

For this progress checkpoint, the deliverables are a formal report, reproducible source code, and documented datasets. The report separates pilot evidence from results that still require validation.

## Current progress

- The Steam history pilot contains 54 selected users, 554 reviews, and 95 games. It is too small to meet the registered evaluation gate of 500 users and at least 100 eligible validation and test users.
- The shared chronological evaluator, data-quality audit, and Popularity baseline are implemented.
- Personalized PageRank and LightGCN have been run on the same pilot split. Results are exploratory because the test set has only 23 users.
- The aspect categories, rule-based text extractor, annotation tools, and proposed opinion feature are in the repository. Human annotation and extraction-quality evaluation are not complete, so no validated opinion result is available.

See the [progress report](reports/progress_report.tex) and its [PDF](output/pdf/progress_report.pdf) for the evidence, methods, and limitations.

## Research questions

1. How do Popularity, Personalized PageRank, and LightGCN rank held-out games under the same time-based evaluation?
2. Which aspects are discussed positively or negatively in reviews, and how accurately can those opinions be extracted?
3. After opinion extraction is validated, does adding aspect-level evidence improve LightGCN ranking?

## Repository map

| Path | Contents |
|---|---|
| reports/ | Editable progress report source |
| output/pdf/ | Rendered progress report |
| src/webmining/ | Shared data loader and ranking evaluation |
| src/models/ | Personalized PageRank and LightGCN implementations |
| scripts/ | Collection, audit, baseline, graph-model, and opinion-mining scripts |
| configs/ | Versioned collection and model settings |
| outputs/ | Versioned datasets, audit reports, pilot metrics, and opinion-mining artifacts |
| docs/ | Sampling design, evaluation protocol, project status, and role guides |

## Data versions

The repository preserves three distinct Steam datasets. Do not combine them to increase graph coverage.

- The 200-review pilot supports early collection and opinion-taxonomy development.
- The 10,000-review quota snapshot supports source and text-pipeline checks. Its reviewer overlap is too low for the current recommendation benchmark.
- The v3 history sample is the current ranking pilot. It preserves observed histories for selected users and uses time-based evaluation windows.

The v3 sample is not representative of all Steam users. The sample-size target and public-source spot-check remain incomplete. The full sampling rules are in [docs/sampling_design.md](docs/sampling_design.md), and the current counts are in [the sampling report](outputs/steam_history_v3/sampling_report.md).

## Reproduce the pilot analyses

From the repository root, install the Python packages needed for the selected analysis. The graph-model CPU environment is specified in requirements-graph.txt.

    python -m pip install -r requirements-graph.txt
    python scripts/audit_history_quality.py
    python scripts/run_popularity_baseline.py --pilot-smoke
    python scripts/run_graph_models.py --pilot-smoke

The rule-based opinion extractor and validation tools are described in the [Member 4 guide](docs/team_guides/member4_opinion_mining/README.md). Opinion outputs are exploratory until compared with human labels.

To rebuild the paper PDF with Tectonic:

    tectonic --outdir output/pdf reports/progress_report.tex

## Shared data rules

- Keep raw records separate from processed views and preserve the source fields.
- Hash reviewer identifiers consistently; do not store raw SteamIDs, credentials, or API tokens.
- Preserve negative reviews for text analysis. Only positive interactions form recommendation graph edges.
- A missing review is unknown feedback, not a verified dislike.
- Keep Steam's overall vote separate from sentiment inferred for individual review aspects.
- Build training histories and opinion profiles only from information available before each evaluation cutoff.

## Team workstreams

| Workstream | Main responsibility |
|---|---|
| [Member 1](docs/team_guides/data_collection/README.md) | Steam collection, source provenance, and coverage checks |
| [Member 2](docs/team_guides/member2_data_evaluation.md) | Data preparation, shared split, evaluator, and baseline |
| [Member 3](docs/team_guides/member3_graph_models/README.md) | Personalized PageRank and LightGCN |
| [Member 4](docs/team_guides/member4_opinion_mining/README.md) | Aspect taxonomy, opinion extraction, and human validation |
