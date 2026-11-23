# Member 3 graph-model pilot

The frozen Steam v3 dataset passed the shared loader's hash and candidate checks.
It has 22 eligible validation users and 23 test users, below the sampling gate.
The reported metrics verify the ranking pipeline.

On Kaggle, use the saved notebook to recreate this run on CPU with its supplied PyTorch.
In the repo, use python scripts/run_graph_models.py --pilot-smoke after applying
the source files to the Member 2 evaluator branch and installing requirements-graph.txt.
The script accepts --coverage-only for diagnostics and --models ppr for PPR alone.

PPR uses restart probability 0.15 and caches the converged scores for each user.
LightGCN uses symmetric degree normalization, averages layer 0 through layer 2,
and trains with BPR on one sampled unobserved warm game per positive edge per epoch.
The sampler excludes every game in the historical seen mask. Hyperparameters and
seed were set before running both holdouts. Test is fit anew using refit history.
The run uses only positive user–game edges and reports no opinion features.
An unobserved game may still become a future positive.

For the final comparison, run the same code on the approved benchmark.
LightGCN with opinions requires validated, cutoff-specific features from Member 4.

LightGCN reference: https://arxiv.org/abs/2002.02126
