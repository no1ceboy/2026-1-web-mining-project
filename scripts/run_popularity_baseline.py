"""Run the shared Popularity baseline on the history-sampling dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from webmining.evaluation import evaluate_popularity, load_ranking_split  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=ROOT / "outputs/steam_history_v3",
        help="Directory containing the versioned history-sampling artifacts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: <dataset-dir>/popularity_baseline_pilot.json).",
    )
    parser.add_argument(
        "--pilot-smoke",
        action="store_true",
        help="Allow metrics when the registered sampling planning gate has not passed; label them smoke-only.",
    )
    parser.add_argument("--ks", nargs="+", type=int, default=[10, 20])
    args = parser.parse_args()

    validation = load_ranking_split(args.dataset_dir, "validation")
    test = load_ranking_split(args.dataset_dir, "test")
    gate_passed = validation.planning_gate_passed and test.planning_gate_passed
    if not gate_passed and not args.pilot_smoke:
        parser.error(
            "The registered sampling planning gate has not passed. "
            "Use --pilot-smoke only for evaluator verification, not model claims."
        )

    payload = {
        "dataset_version": validation.dataset_version,
        "split_contract_status": validation.split_contract_status,
        "planning_gate_passed": gate_passed,
        "result_status": "preliminary" if gate_passed else "pilot_smoke_only",
        "interpretation": (
            "This run verifies metric and ranking plumbing on the current small cohort. "
            "Do not interpret it as evidence that one recommender is better."
            if not gate_passed
            else "Report only alongside the complete evaluation protocol and coverage diagnostics."
        ),
        "validation": evaluate_popularity(validation, args.ks),
        "test": evaluate_popularity(test, args.ks),
    }
    output = args.output or (args.dataset_dir / "popularity_baseline_pilot.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "result_status": payload["result_status"],
        "validation": payload["validation"]["metrics"],
        "test": payload["test"]["metrics"],
        "validation_users": payload["validation"]["target_users"],
        "test_users": payload["test"]["target_users"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
