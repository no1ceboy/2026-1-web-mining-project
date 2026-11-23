"""Run graph recommenders with the shared Steam history evaluator."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import platform
import sys
from time import perf_counter

from steam_crawler import atomic_text, write_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models.interaction_graph import InteractionGraph
from models.ppr import PersonalizedPageRank
from webmining.evaluation import (
    RankingSplit, evaluate_ranker, load_ranking_split, popularity_scores, read_json, read_jsonl,
)


def coverage_row(
    label: str, rows: list[dict] | tuple[dict, ...], graph: InteractionGraph, target_count: int | str
) -> dict:
    return {
        "history": label,
        "reviews": len(rows),
        "observed_users": len({row["user_id"] for row in rows}),
        "observed_items": len({row["item_id"] for row in rows}),
        **graph.coverage(),
        "target_users": target_count,
    }


def write_coverage(
    output: Path, version: str, gate_passed: bool, digest: str,
    splits: dict[str, RankingSplit], graphs: dict[str, InteractionGraph],
) -> None:
    pilot_rows = read_jsonl(ROOT / "outputs/steam_pilot.jsonl")
    pilot_graph = InteractionGraph(
        (row["user_id"], row["item_id"]) for row in pilot_rows if row["positive_interaction"]
    )
    rows = [coverage_row("Original Steam pilot (reference)", pilot_rows, pilot_graph, "—")]
    for name, split in splits.items():
        rows.append(coverage_row(name.title(), split.history_rows, graphs[name], len(split.candidates_by_user)))
    fields = {
        "history": "History",
        "reviews": "Reviews",
        "observed_users": "Observed users",
        "observed_items": "Observed games",
        "warm_users": "Positive users",
        "warm_items": "Positive games",
        "positive_edges": "Positive edges",
        "users_with_two_positive_games": "Users with ≥2 positive games",
        "components": "Components",
        "largest_component_users": "Largest component users",
        "largest_component_items": "Largest component games",
        "largest_component_edges": "Largest component edges",
        "target_users": "Eligible target users",
    }
    lines = [
        "# Graph coverage",
        "",
        f"Dataset version **{version}**. Split manifest SHA-256 \u0060{digest}\u0060.",
        f"Planning gate passed **{gate_passed}**.",
        "",
        "| " + " | ".join(fields.values()) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    lines.extend("| " + " | ".join(str(row[field]) for field in fields) + " |" for row in rows)
    lines.extend([
        "",
        "An edge is a distinct positive user–game pair. Components contain incident nodes only.",
        "Validation uses train history. Test refits on history available before the test cutoff.",
        "The original 200-review snapshot is included as a separate coverage reference.",
        "",
    ])
    atomic_text(output, "\n".join(lines))


def evaluate_models(
    split: RankingSplit, graph: InteractionGraph, selected: tuple[str, ...], config: dict,
) -> dict:
    results = {}
    for name in selected:
        started = perf_counter()
        details = {}
        if name == "popularity":
            counts = popularity_scores(split)
            score = lambda _user_id, item_id: counts.get(item_id, 0)
        elif name == "ppr":
            score = PersonalizedPageRank(graph, **config["ppr"]).score
        else:
            from models.lightgcn import LightGCN, LightGCNConfig

            model = LightGCN(graph, LightGCNConfig(**config["lightgcn"]))
            details["training"] = model.fit(split.seen_items_by_user)
            score = model.make_scorer()
        prepared = perf_counter()
        result = evaluate_ranker(split, score, ks=config["ks"])
        ranked = perf_counter()
        results[name] = {
            **result,
            **details,
            "runtime_seconds": {
                "prepare": round(prepared - started, 6),
                "rank_and_evaluate": round(ranked - prepared, 6),
                "total": round(ranked - started, 6),
            },
        }
    return results


def cpu_description() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "model name":
                return value.strip()
    return platform.processor() or platform.machine()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "outputs/steam_history_v3")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/graph_models_pilot.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--models", nargs="+", choices=("popularity", "ppr", "lightgcn"),
                        default=("popularity", "ppr", "lightgcn"))
    parser.add_argument("--coverage-only", action="store_true", help="Compute diagnostics without ranking.")
    parser.add_argument("--pilot-smoke", action="store_true", help="Allow smoke runs below the sampling gate.")
    args = parser.parse_args()

    splits = {name: load_ranking_split(args.dataset_dir, name) for name in ("validation", "test")}
    validation = splits["validation"]
    gate_passed = all(split.planning_gate_passed for split in splits.values())
    if not gate_passed and not (args.coverage_only or args.pilot_smoke):
        parser.error("The sampling gate has not passed. Use --pilot-smoke for pipeline verification.")

    manifest = args.dataset_dir / "split_manifest.json"
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    graphs = {name: InteractionGraph(split.positive_edges) for name, split in splits.items()}
    write_coverage(
        args.output_dir / "graph_coverage.md", validation.dataset_version, gate_passed, digest, splits, graphs
    )
    if args.coverage_only:
        return

    config = read_json(args.config)
    selected = tuple(dict.fromkeys(args.models))
    runtime = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "device": "cpu",
        "cpu": cpu_description(),
        "logical_cpus": os.cpu_count(),
    }
    if "lightgcn" in selected:
        try:
            import torch
        except ModuleNotFoundError as exc:
            if exc.name != "torch":
                raise
            parser.error("LightGCN requires PyTorch. Install requirements-graph.txt or choose --models ppr.")
        torch.set_num_threads(1)
        runtime.update(torch=str(torch.__version__), torch_threads=torch.get_num_threads())

    result = {
        "dataset_version": validation.dataset_version,
        "split_manifest_sha256": digest,
        "split_contract_status": validation.split_contract_status,
        "planning_gate_passed": gate_passed,
        "result_status": "preliminary" if gate_passed else "pilot_smoke_only",
        "runtime_environment": runtime,
        "config": {"ks": config["ks"], **{name: config[name] for name in selected if name in config}},
        "splits": {
            name: {
                "coverage": graphs[name].coverage(),
                "models": evaluate_models(split, graphs[name], selected, config),
            }
            for name, split in splits.items()
        },
    }
    path = args.output_dir / "graph_metrics.json"
    write_json(path, result)
    print(f"Wrote {path} ({result['result_status']}).")


if __name__ == "__main__":
    main()
