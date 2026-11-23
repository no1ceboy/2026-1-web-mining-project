# Graph-model pilot notes

## Scope

The recorded Personalized PageRank and LightGCN runs use dataset version steam_history_v3 and the shared loader and evaluator. They are marked pilot-only because the registered sampling gate has not passed.

## Configuration

- Personalized PageRank restart probability: 0.15.
- LightGCN embedding size: 32.
- LightGCN propagation layers: 2.
- LightGCN training epochs: 30.
- Random seed: 2026.
- Training objective: Bayesian Personalized Ranking with sampled unobserved games used only as optimization negatives.
- Evaluation: the complete eligible candidate set from the shared split after excluding all previously reviewed games.

## Recorded environment

The metrics file records Linux, Python 3.13.18, PyTorch 2.11.0+cpu, and one CPU thread. requirements-graph.txt pins that PyTorch version. A GPU is not required to reproduce this small smoke run.

## Interpretation

There are 22 validation users and 23 test users. The metrics show that the ranking code runs through the shared evaluator; they do not establish which method is better for Steam users generally. The test Recall@10 difference between PPR and Popularity corresponds to two users. LightGCN has higher Recall@20 than the other methods on this test split, but the difference is one user.

The run uses only positive user-game edges and no opinion features. Opinion-augmented LightGCN requires validated, cutoff-specific opinion data and a final shared benchmark.

## Reproduction

From the repository root, install requirements-graph.txt and run:

    python scripts/run_graph_models.py --pilot-smoke

The script and saved metrics are the reproducibility record. No notebook is required.
