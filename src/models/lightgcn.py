"""CPU LightGCN with symmetric graph normalization and pairwise BPR training."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Set
from dataclasses import dataclass
import math
import random

import torch
from torch import nn
from torch.nn import functional as F

from .interaction_graph import InteractionGraph


@dataclass(frozen=True)
class LightGCNConfig:
    embedding_dim: int
    layers: int
    epochs: int
    batch_size: int
    learning_rate: float
    regularization: float
    seed: int

    def __post_init__(self) -> None:
        if min(self.embedding_dim, self.layers, self.epochs, self.batch_size) < 1:
            raise ValueError("LightGCN dimensions, layers, epochs and batch size must be positive")
        if not math.isfinite(self.learning_rate) or self.learning_rate <= 0:
            raise ValueError("LightGCN learning rate must be finite and positive")
        if not math.isfinite(self.regularization) or self.regularization < 0:
            raise ValueError("LightGCN regularization must be finite and nonnegative")


class LightGCN(nn.Module):
    def __init__(self, graph: InteractionGraph, config: LightGCNConfig) -> None:
        super().__init__()
        self.graph = graph
        self.config = config
        node_count = len(graph.neighbors)
        degree = [len(neighbors) for neighbors in graph.neighbors]
        source, destination, weights = [], [], []
        for node, neighbors in enumerate(graph.neighbors):
            for neighbor in neighbors:
                source.append(node)
                destination.append(neighbor)
                weights.append(1.0 / math.sqrt(degree[node] * degree[neighbor]))
        adjacency = torch.sparse_coo_tensor(
            torch.tensor([source, destination], dtype=torch.long),
            torch.tensor(weights, dtype=torch.float32),
            (node_count, node_count),
        ).coalesce()
        self.register_buffer("adjacency", adjacency)

        generator = torch.Generator().manual_seed(config.seed)
        self.initial_embeddings = nn.Parameter(torch.empty(node_count, config.embedding_dim, dtype=torch.float32))
        nn.init.normal_(self.initial_embeddings, std=0.1, generator=generator)

    def forward(self) -> torch.Tensor:
        layer = self.initial_embeddings
        embeddings = layer
        for _ in range(self.config.layers):
            layer = torch.sparse.mm(self.adjacency, layer)
            embeddings = embeddings + layer
        return embeddings / (self.config.layers + 1)

    def _negative_pools(self, seen_items_by_user: Mapping[str, Set[str]]) -> list[tuple[int, ...]]:
        pools = []
        for user, node in self.graph.user_nodes.items():
            seen = seen_items_by_user.get(user, frozenset())
            positives = set(self.graph.neighbors[node])
            pools.append(tuple(
                item_node for item_id, item_node in self.graph.item_nodes.items()
                if item_id not in seen and item_node not in positives
            ))
        return pools

    def fit(self, seen_items_by_user: Mapping[str, Set[str]]) -> dict[str, int | float]:
        """Sample one unobserved warm game per positive edge in each epoch."""
        config = self.config
        negative_pools = self._negative_pools(seen_items_by_user)
        training_pairs = [(user, item) for user, item in self.graph.edges if negative_pools[user]]
        if not training_pairs:
            raise ValueError("LightGCN requires a positive edge with an unobserved warm game")

        rng = random.Random(config.seed)
        optimizer = torch.optim.Adam(self.parameters(), lr=config.learning_rate)
        mean_losses = []
        for _ in range(config.epochs):
            rng.shuffle(training_pairs)
            epoch_loss = 0.0
            for start in range(0, len(training_pairs), config.batch_size):
                batch = training_pairs[start:start + config.batch_size]
                users, positives = zip(*batch)
                negatives = [rng.choice(negative_pools[user]) for user in users]
                user_nodes = torch.tensor(users)
                pos_nodes = torch.tensor(positives)
                neg_nodes = torch.tensor(negatives)

                optimizer.zero_grad()
                embeddings = self()
                margins = (embeddings[user_nodes] * (embeddings[pos_nodes] - embeddings[neg_nodes])).sum(dim=1)
                initial = self.initial_embeddings
                reg = sum(initial[nodes].square().sum() for nodes in (user_nodes, pos_nodes, neg_nodes))
                loss = F.softplus(-margins).mean() + config.regularization * reg / (2 * len(batch))
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * len(batch)
            mean_loss = epoch_loss / len(training_pairs)
            if not math.isfinite(mean_loss):
                raise RuntimeError("LightGCN training produced a non-finite loss")
            mean_losses.append(mean_loss)

        return {
            "positive_edges_per_epoch": len(training_pairs),
            "skipped_edges_without_unobserved_games": len(self.graph.edges) - len(training_pairs),
            "first_epoch_mean_loss": mean_losses[0],
            "last_epoch_mean_loss": mean_losses[-1],
        }

    def make_scorer(self) -> Callable[[str, str], float]:
        with torch.no_grad():
            embeddings = self()

        def score(user_id: str, item_id: str) -> float:
            user = self.graph.user_nodes.get(user_id)
            item = self.graph.item_nodes.get(item_id)
            if user is None or item is None:
                return 0.0
            return float(torch.dot(embeddings[user], embeddings[item]))

        return score
