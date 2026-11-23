"""Personalized PageRank with restart at the requesting user's node."""

from __future__ import annotations

import math

from .interaction_graph import InteractionGraph


class PersonalizedPageRank:
    def __init__(self, graph: InteractionGraph, restart: float, tolerance: float, max_iterations: int) -> None:
        if not 0 < restart <= 1 or not math.isfinite(tolerance) or tolerance <= 0 or max_iterations < 1:
            raise ValueError("PPR needs a restart probability in (0, 1], positive tolerance and at least one iteration")
        self.graph = graph
        self.restart = restart
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.rankings: dict[int, list[float]] = {}

    def _rank(self, user: int) -> list[float]:
        neighbors = self.graph.neighbors
        scores = [0.0] * len(neighbors)
        scores[user] = 1.0
        for _ in range(self.max_iterations):
            updated = [0.0] * len(neighbors)
            updated[user] = self.restart
            for mass, adjacent in zip(scores, neighbors):
                if mass:
                    share = (1.0 - self.restart) * mass / len(adjacent)
                    for neighbor in adjacent:
                        updated[neighbor] += share
            if sum(abs(new - old) for new, old in zip(updated, scores)) <= self.tolerance:
                return updated
            scores = updated
        raise RuntimeError(f"PPR did not converge within {self.max_iterations} iterations")

    def score(self, user_id: str, item_id: str) -> float:
        user = self.graph.user_nodes.get(user_id)
        item = self.graph.item_nodes.get(item_id)
        if user is None or item is None:
            return 0.0
        if user not in self.rankings:
            self.rankings[user] = self._rank(user)
        return self.rankings[user][item]
