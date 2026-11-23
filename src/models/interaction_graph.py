"""Undirected bipartite graph shared by PPR, LightGCN, and coverage diagnostics."""

from __future__ import annotations

from collections.abc import Iterable


class InteractionGraph:
    """Index users first and games second, with disjoint node IDs."""

    def __init__(self, positive_edges: Iterable[tuple[str, str]]) -> None:
        edges = sorted(set(positive_edges))
        self.users = tuple(sorted({user for user, _ in edges}))
        self.items = tuple(sorted({item for _, item in edges}))
        self.user_nodes = {user: index for index, user in enumerate(self.users)}
        self.item_nodes = {item: index for index, item in enumerate(self.items, len(self.users))}
        self.edges = tuple((self.user_nodes[user], self.item_nodes[item]) for user, item in edges)

        neighbors: list[list[int]] = [[] for _ in range(len(self.users) + len(self.items))]
        for user, item in self.edges:
            neighbors[user].append(item)
            neighbors[item].append(user)
        self.neighbors = tuple(tuple(nodes) for nodes in neighbors)

    def coverage(self) -> dict[str, int]:
        """Count positive components and size the largest by total nodes."""
        remaining = set(range(len(self.neighbors)))
        components = 0
        largest_users = largest_items = largest_edges = 0
        for start in range(len(self.neighbors)):
            if start not in remaining:
                continue
            remaining.remove(start)
            pending = [start]
            components += 1
            users = items = edges = 0
            while pending:
                node = pending.pop()
                if node < len(self.users):
                    users += 1
                    edges += len(self.neighbors[node])
                else:
                    items += 1
                for neighbor in self.neighbors[node]:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        pending.append(neighbor)
            if users + items > largest_users + largest_items:
                largest_users, largest_items, largest_edges = users, items, edges

        return {
            "warm_users": len(self.users),
            "warm_items": len(self.items),
            "positive_edges": len(self.edges),
            "users_with_two_positive_games": sum(len(self.neighbors[node]) >= 2 for node in self.user_nodes.values()),
            "components": components,
            "largest_component_users": largest_users,
            "largest_component_items": largest_items,
            "largest_component_edges": largest_edges,
        }
