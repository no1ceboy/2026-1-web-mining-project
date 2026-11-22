"""Shared loader and ranking metrics for the Steam user-history dataset.

The loader follows the history-sampling contract: graph edges come from unique
positive user-game interactions in the selected history file; all previously
reviewed games, including negative reviews, are removed from recommendation
candidates. Candidate items are the warm positive items for that split.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Callable, Iterable


class DataContractError(ValueError):
    """Raised when a dataset artifact violates the shared evaluation contract."""


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise DataContractError(f"Expected a JSON object in {path}")
    return value


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataContractError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise DataContractError(f"Expected an object at {path}:{line_number}")
            rows.append(row)
    return rows


def _check_hash(path: Path, expected: str | None) -> None:
    if expected is None:
        return
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise DataContractError(f"Hash mismatch for {path.name}; dataset artifacts changed")


def _validate_history(rows: list[dict], path: Path) -> None:
    required = {"review_id", "user_id", "item_id", "timestamp", "positive_interaction"}
    review_ids = set()
    for index, row in enumerate(rows, start=1):
        missing = required - row.keys()
        if missing:
            raise DataContractError(f"{path.name} row {index} is missing {sorted(missing)}")
        if not isinstance(row["review_id"], str) or not row["review_id"]:
            raise DataContractError(f"{path.name} row {index} has an invalid review_id")
        if not isinstance(row["user_id"], str) or not row["user_id"]:
            raise DataContractError(f"{path.name} row {index} has an invalid user_id")
        if not isinstance(row["item_id"], str) or not row["item_id"]:
            raise DataContractError(f"{path.name} row {index} has an invalid item_id")
        if type(row["positive_interaction"]) is not bool:
            raise DataContractError(f"{path.name} row {index} has a non-Boolean positive_interaction")
        if row["review_id"] in review_ids:
            raise DataContractError(f"{path.name} contains duplicate review_id {row['review_id']}")
        review_ids.add(row["review_id"])


@dataclass(frozen=True)
class RankingSplit:
    """Inputs shared by all recommenders for one chronological evaluation window."""

    name: str
    history_rows: tuple[dict, ...]
    targets: tuple[dict, ...]
    positive_edges: frozenset[tuple[str, str]]
    warm_users: frozenset[str]
    warm_items: frozenset[str]
    seen_items_by_user: dict[str, frozenset[str]]
    candidates_by_user: dict[str, tuple[str, ...]]
    dataset_version: str
    split_contract_status: str
    planning_gate_passed: bool

    @property
    def targets_by_user(self) -> dict[str, frozenset[str]]:
        grouped: dict[str, set[str]] = defaultdict(set)
        for row in self.targets:
            grouped[row["user_id"]].add(row["item_id"])
        return {user: frozenset(items) for user, items in grouped.items()}


def load_ranking_split(dataset_dir: str | Path, name: str) -> RankingSplit:
    """Load and validate a split named ``validation`` or ``test``.

    Validation uses ``train_reviews``. Test uses ``refit_reviews`` so that
    all observations permitted before the test cutoff are available.
    """
    dataset_dir = Path(dataset_dir)
    if name == "validation":
        history_name = "train_reviews.jsonl"
        target_name = "validation_targets.jsonl"
        seen_name = "seen_items_before_validation.jsonl"
    elif name == "test":
        history_name = "refit_reviews.jsonl"
        target_name = "test_targets.jsonl"
        seen_name = "seen_items_before_test.jsonl"
    else:
        raise ValueError("name must be 'validation' or 'test'")

    split_manifest_path = dataset_dir / "split_manifest.json"
    audit_path = dataset_dir / "sampling_audit.json"
    sampling_manifest_path = dataset_dir / "sampling_manifest.json"
    split_manifest = read_json(split_manifest_path)
    audit = read_json(audit_path)
    sampling_manifest = read_json(sampling_manifest_path)
    file_hashes = split_manifest.get("data_files_sha256", {})

    history_path = dataset_dir / history_name
    targets_path = dataset_dir / target_name
    seen_path = dataset_dir / seen_name
    _check_hash(history_path, file_hashes.get(history_name))
    _check_hash(targets_path, file_hashes.get(target_name))
    _check_hash(seen_path, file_hashes.get(seen_name))

    history = read_jsonl(history_path)
    targets = read_jsonl(targets_path)
    seen_rows = read_jsonl(seen_path)
    _validate_history(history, history_path)

    positive_edges = frozenset(
        (row["user_id"], row["item_id"])
        for row in history
        if row["positive_interaction"]
    )
    warm_users = frozenset(user for user, _ in positive_edges)
    warm_items = frozenset(item for _, item in positive_edges)

    seen_items: dict[str, frozenset[str]] = {}
    for index, row in enumerate(seen_rows, start=1):
        user = row.get("user_id")
        items = row.get("item_ids")
        if not isinstance(user, str) or not isinstance(items, list) or not all(
            isinstance(item, str) for item in items
        ):
            raise DataContractError(f"{seen_name} row {index} has an invalid shape")
        if user in seen_items:
            raise DataContractError(f"{seen_name} contains duplicate user masks for {user}")
        seen_items[user] = frozenset(items)

    missing_seen = [
        (row["user_id"], row["item_id"])
        for row in history
        if row["item_id"] not in seen_items.get(row["user_id"], frozenset())
    ]
    if missing_seen:
        raise DataContractError(
            f"Seen-item masks omit {len(missing_seen)} historical user-item interactions"
        )

    targets_by_user: dict[str, set[str]] = defaultdict(set)
    target_review_ids = set()
    for index, row in enumerate(targets, start=1):
        user, item, review_id = row.get("user_id"), row.get("item_id"), row.get("review_id")
        if not all(isinstance(value, str) and value for value in (user, item, review_id)):
            raise DataContractError(f"{target_name} row {index} has an invalid key")
        if review_id in target_review_ids:
            raise DataContractError(f"{target_name} contains duplicate target review_id {review_id}")
        target_review_ids.add(review_id)
        targets_by_user[user].add(item)
    history_review_ids = {row["review_id"] for row in history}
    leaked_target_ids = target_review_ids & history_review_ids
    if leaked_target_ids:
        raise DataContractError(
            f"{len(leaked_target_ids)} held-out review IDs also appear in the history file"
        )

    candidates_by_user: dict[str, tuple[str, ...]] = {}
    for user, relevant_items in targets_by_user.items():
        if user not in warm_users:
            raise DataContractError(f"Target user {user} has no positive training history")
        candidates = warm_items - seen_items.get(user, frozenset())
        if not relevant_items <= candidates:
            raise DataContractError(f"Target item for {user} is not an unseen warm candidate")
        declared_counts = {
            row["candidate_count"]
            for row in targets
            if row["user_id"] == user and "candidate_count" in row
        }
        if declared_counts and declared_counts != {len(candidates)}:
            raise DataContractError(
                f"Candidate count mismatch for {user}: manifest rows {declared_counts}, "
                f"loader {len(candidates)}"
            )
        candidates_by_user[user] = tuple(sorted(candidates))

    return RankingSplit(
        name=name,
        history_rows=tuple(history),
        targets=tuple(targets),
        positive_edges=positive_edges,
        warm_users=warm_users,
        warm_items=warm_items,
        seen_items_by_user=seen_items,
        candidates_by_user=candidates_by_user,
        dataset_version=audit.get("dataset_version", "unknown"),
        split_contract_status=split_manifest.get("status", "unknown"),
        planning_gate_passed=bool(audit.get("planning_gate_passed", False)),
    )


def popularity_scores(split: RankingSplit) -> Counter:
    """Count distinct positive user-game edges for each game in the history."""
    return Counter(item for _, item in split.positive_edges)


def evaluate_ranker(
    split: RankingSplit,
    score: Callable[[str, str], float],
    ks: Iterable[int] = (10, 20),
    include_per_user: bool = False,
) -> dict:
    """Evaluate a scorer over each target user's complete eligible candidate set.

    Ties are broken by ascending item ID. Metrics are macro-averaged over target
    users. Recall@K and NDCG@K are computed against all held-out relevant items
    for each user, even though the current pilot has one target per user.
    """
    ks = tuple(sorted(set(int(k) for k in ks)))
    if not ks or any(k < 1 for k in ks):
        raise ValueError("ks must contain positive integers")
    relevant_by_user = split.targets_by_user
    if not relevant_by_user:
        raise DataContractError(f"No eligible targets in {split.name} split")

    per_user = []
    metric_sums = {key: 0.0 for k in ks for key in (f"recall_at_{k}", f"ndcg_at_{k}")}
    for user, relevant in sorted(relevant_by_user.items()):
        candidates = split.candidates_by_user[user]
        scored = []
        for item in candidates:
            value = float(score(user, item))
            if not math.isfinite(value):
                raise DataContractError(f"Non-finite score for user={user}, item={item}")
            scored.append((item, value))
        ranked = [item for item, _ in sorted(scored, key=lambda pair: (-pair[1], pair[0]))]
        ranks = {item: position for position, item in enumerate(ranked, start=1)}
        user_result = {
            "user_id": user,
            "target_items": sorted(relevant),
            "candidate_count": len(candidates),
            "target_ranks": {item: ranks[item] for item in sorted(relevant)},
        }
        for k in ks:
            top = set(ranked[:k])
            hits = len(relevant & top)
            recall = hits / len(relevant)
            dcg = sum(1.0 / math.log2(ranks[item] + 1) for item in relevant if ranks[item] <= k)
            ideal_count = min(len(relevant), k)
            idcg = sum(1.0 / math.log2(position + 2) for position in range(ideal_count))
            ndcg = dcg / idcg if idcg else 0.0
            metric_sums[f"recall_at_{k}"] += recall
            metric_sums[f"ndcg_at_{k}"] += ndcg
            user_result[f"recall_at_{k}"] = recall
            user_result[f"ndcg_at_{k}"] = ndcg
        per_user.append(user_result)

    user_count = len(per_user)
    metrics = {key: value / user_count for key, value in metric_sums.items()}
    candidate_counts = [len(split.candidates_by_user[user]) for user in relevant_by_user]
    result = {
        "split": split.name,
        "target_users": user_count,
        "positive_history_edges": len(split.positive_edges),
        "warm_users": len(split.warm_users),
        "warm_items": len(split.warm_items),
        "candidate_count_min": min(candidate_counts),
        "candidate_count_max": max(candidate_counts),
        "candidate_count_mean": round(sum(candidate_counts) / len(candidate_counts), 4),
        "metrics": metrics,
        "tie_break": "score descending, then item_id ascending",
    }
    if include_per_user:
        result["per_user"] = per_user
    return result


def evaluate_popularity(split: RankingSplit, ks: Iterable[int] = (10, 20)) -> dict:
    scores = popularity_scores(split)
    result = evaluate_ranker(split, lambda _user, item: scores.get(item, 0), ks=ks)
    result["model"] = "Popularity (positive training-edge count)"
    result["score_source"] = "unique positive user-item pairs in the split history"
    return result
